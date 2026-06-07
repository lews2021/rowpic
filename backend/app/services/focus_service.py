"""Focus / blur / face analysis.

- overall sharpness: Laplacian variance
- face detection: OpenCV Haar cascade (no external model)
- per-face sharpness: Laplacian variance of face ROI
- blur heatmap: low-resolution Laplacian map (optional, base64 PNG)
"""
from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from app.models.schemas import FaceBox, FocusQuality, FocusReport

logger = logging.getLogger(__name__)


# Load Haar cascade (bundled with opencv)
_FRONTAL_FACE_XML = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_PROFILE_FACE_XML = cv2.data.haarcascades + "haarcascade_profileface.xml"
_frontal_cascade = cv2.CascadeClassifier(_FRONTAL_FACE_XML)
_profile_cascade = cv2.CascadeClassifier(_PROFILE_FACE_XML)


def laplacian_variance(gray: np.ndarray) -> float:
    if gray.dtype != np.uint8:
        gray = np.clip(gray, 0, 255).astype(np.uint8)
    lap = cv2.Laplacian(gray, cv2.CV_32F)
    return float(lap.var())


def classify_sharpness(score: float, blurry_thr: float, soft_thr: float) -> FocusQuality:
    if score < blurry_thr:
        return FocusQuality.BLURRY
    if score < soft_thr:
        return FocusQuality.SOFT
    return FocusQuality.SHARP


def detect_faces(rgb: np.ndarray, min_size: int = 40) -> List[Tuple[int, int, int, int]]:
    """Return list of (x, y, w, h) face boxes."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray_eq = cv2.equalizeHist(gray)
    boxes: List[Tuple[int, int, int, int]] = []

    if not _frontal_cascade.empty():
        f = _frontal_cascade.detectMultiScale(
            gray_eq, scaleFactor=1.1, minNeighbors=4, minSize=(min_size, min_size)
        )
        if len(f):
            boxes.extend([tuple(int(v) for v in b) for b in f])

    if not _profile_cascade.empty():
        p = _profile_cascade.detectMultiScale(
            gray_eq, scaleFactor=1.1, minNeighbors=4, minSize=(min_size, min_size)
        )
        if len(p):
            for b in p:
                bb = tuple(int(v) for v in b)
                if not _overlaps(bb, boxes, iou=0.3):
                    boxes.append(bb)

    return boxes


def _overlaps(box, others, iou: float) -> bool:
    x, y, w, h = box
    for (ox, oy, ow, oh) in others:
        # intersection
        ix0, iy0 = max(x, ox), max(y, oy)
        ix1, iy1 = min(x + w, ox + ow), min(y + h, oy + oh)
        iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
        inter = iw * ih
        union = w * h + ow * oh - inter
        if union and inter / union > iou:
            return True
    return False


def make_focus_heatmap(rgb: np.ndarray, size: int = 96) -> Optional[str]:
    """Return base64 PNG of a downsampled Laplacian heatmap (red = sharp)."""
    try:
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape
        scale = size / float(max(h, w))
        if scale < 1.0:
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        lap = cv2.Laplacian(gray, cv2.CV_32F)
        lap = np.abs(lap)
        if lap.max() > 0:
            lap = (lap / lap.max() * 255.0).astype(np.uint8)
        heat = cv2.applyColorMap(lap, cv2.COLORMAP_INFERNO)
        ok, buf = cv2.imencode(".png", heat)
        if not ok:
            return None
        return base64.b64encode(buf.tobytes()).decode("ascii")
    except Exception as exc:
        logger.debug("heatmap failed: %s", exc)
        return None


def analyze(
    rgb: np.ndarray,
    blur_threshold: float = 60.0,
    face_blur_threshold: float = 35.0,
    face_min_size: int = 40,
    include_heatmap: bool = True,
) -> FocusReport:
    """Full focus analysis."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    overall = laplacian_variance(gray)
    soft_thr = max(blur_threshold, 25.0) * 1.5
    quality = classify_sharpness(overall, blur_threshold, soft_thr)

    faces: List[FaceBox] = []
    raw_boxes = detect_faces(rgb, min_size=face_min_size)
    for (x, y, w, h) in raw_boxes:
        # Pad slightly
        px0 = max(0, x - int(w * 0.1))
        py0 = max(0, y - int(h * 0.1))
        px1 = min(rgb.shape[1], x + w + int(w * 0.1))
        py1 = min(rgb.shape[0], y + h + int(h * 0.1))
        roi = gray[py0:py1, px0:px1]
        if roi.size == 0:
            continue
        s = laplacian_variance(roi)
        faces.append(FaceBox(
            x=px0, y=py0, w=px1 - px0, h=py1 - py0,
            sharpness=s,
            quality=classify_sharpness(s, face_blur_threshold, face_blur_threshold * 1.6),
        ))

    heatmap_b64 = make_focus_heatmap(rgb) if include_heatmap else None

    from app.services.histogram_service import is_backlit, mean_luminance
    return FocusReport(
        overall_sharpness=overall,
        overall_quality=quality,
        exposure=mean_luminance(rgb),
        is_backlit=is_backlit(rgb),
        faces=faces,
        blur_map_thumb=heatmap_b64,
    )
