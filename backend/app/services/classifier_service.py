"""One-click classifier.

Rules (composable, all optional):
- blurry        : overall Laplacian variance < settings.blur_threshold
- blurry_face   : at least one detected face with sharpness < settings.face_blur_threshold
- exposure      : mean luminance < 0.18 (underexposed) or > 0.85 (overexposed)
- backlit       : backlit heuristic (currently keeps as 'keep')

Optionally moves files into category subfolders and returns a per-photo
mapping so the frontend can update its UI.
"""
from __future__ import annotations

import logging
import shutil
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings
from app.models.schemas import (
    CategoryLabel,
    ClassifyRequest,
    ClassifyResult,
    FocusQuality,
    PhotoMeta,
)
from app.services.decoder import decode_to_array
from app.services.focus_service import analyze as analyze_focus

logger = logging.getLogger(__name__)


def _exposure_category(mean_lum: float) -> Optional[CategoryLabel]:
    if mean_lum is None:
        return None
    if mean_lum < 0.18:
        return CategoryLabel.UNDEREXPOSED
    if mean_lum > 0.85:
        return CategoryLabel.OVEREXPOSED
    return None


def _classify_one(rgb, rules: List[str]) -> CategoryLabel:
    """Given a decoded RGB array and a rule list, return the category."""
    if "blurry_face" in rules or "blurry" in rules:
        focus = analyze_focus(
            rgb,
            blur_threshold=settings.blur_threshold,
            face_blur_threshold=settings.face_blur_threshold,
            face_min_size=settings.face_min_size,
            include_heatmap=False,
        )
        if "blurry_face" in rules and any(f.quality in (FocusQuality.BLURRY, FocusQuality.SOFT) for f in focus.faces):
            return CategoryLabel.BLURRY_FACE
        if "blurry" in rules and focus.overall_quality == FocusQuality.BLURRY:
            return CategoryLabel.BLURRY

    if "exposure" in rules:
        from app.services.histogram_service import mean_luminance
        cat = _exposure_category(mean_luminance(rgb))
        if cat:
            return cat

    return CategoryLabel.KEEP


def classify_all(
    photos: List[PhotoMeta],
    req: ClassifyRequest,
) -> ClassifyResult:
    counts: Counter = Counter()
    moves: List[dict] = []
    per_photo: Dict[str, str] = {}  # path -> category

    for photo in photos:
        try:
            rgb = decode_to_array(photo.path, max_dim=1600)
            cat = _classify_one(rgb, req.rules)
        except Exception as exc:
            logger.warning("classify error on %s: %s", photo.path, exc)
            cat = CategoryLabel.UNCLASSIFIED
        photo.category = cat
        per_photo[photo.path] = cat.value
        counts[cat.value] += 1

        if req.move and cat not in (CategoryLabel.KEEP, CategoryLabel.UNCLASSIFIED):
            src = Path(photo.path)
            dest = src.parent / cat.value / src.name
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.move(str(src), str(dest))
                    moves.append({"src": str(src), "dest": str(dest), "category": cat.value})
                    photo.path = str(dest)
                    per_photo[str(dest)] = cat.value
                    # refresh the key in per_photo
                    per_photo.pop(str(src), None)
            except Exception as exc:
                logger.warning("move failed %s -> %s: %s", src, dest, exc)

    return ClassifyResult(
        total=len(photos),
        categories=dict(counts),
        moves=moves,
        per_photo=per_photo,
    )
