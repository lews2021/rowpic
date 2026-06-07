"""Histogram & luminance analysis."""
from __future__ import annotations

import numpy as np

from app.models.schemas import HistogramData


def compute_histogram(rgb: np.ndarray, bins: int = 256) -> HistogramData:
    """Compute per-channel + luminance histogram."""
    if rgb.dtype != np.uint8:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    r, _ = np.histogram(rgb[..., 0], bins=bins, range=(0, 256))
    g, _ = np.histogram(rgb[..., 1], bins=bins, range=(0, 256))
    b, _ = np.histogram(rgb[..., 2], bins=bins, range=(0, 256))
    # Rec. 709 luminance
    lum_f = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]) / 255.0
    lum, _ = np.histogram(np.clip(lum_f * 255.0, 0, 255).astype(np.uint8), bins=bins, range=(0, 256))

    total = float(r.sum()) or 1.0
    return HistogramData(
        luminance=lum.tolist(),
        red=r.tolist(),
        green=g.tolist(),
        blue=b.tolist(),
        clip_high=float((rgb >= 250).sum()) / (rgb.size / 3) / 1.0,
        clip_low=float((rgb <= 5).sum()) / (rgb.size / 3) / 1.0,
    )


def mean_luminance(rgb: np.ndarray) -> float:
    f = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]) / 255.0
    return float(f.mean())


def is_backlit(rgb: np.ndarray, threshold: float = 0.85) -> bool:
    """Heuristic: very bright background + dark foreground subject region."""
    h, w = rgb.shape[:2]
    # sample center 40% region
    cy0, cy1 = int(h * 0.3), int(h * 0.7)
    cx0, cx1 = int(w * 0.3), int(w * 0.7)
    center = rgb[cy0:cy1, cx0:cx1]
    f_center = (0.2126 * center[..., 0] + 0.7152 * center[..., 1] + 0.0722 * center[..., 2]) / 255.0
    f_full = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]) / 255.0
    return float(f_full.mean()) > 0.55 and float(f_center.mean()) < 0.25
