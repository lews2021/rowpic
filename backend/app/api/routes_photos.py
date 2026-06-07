"""Photo browse / scan / metadata API."""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.core.config import settings
from app.models.schemas import (
    HistogramData,
    PhotoDetail,
    PhotoMeta,
    ScanRequest,
    ScanResult,
)
from app.services.decoder import (
    decode_to_array,
    encode_jpeg,
    is_raw,
    make_preview,
    make_thumb,
    safe_stat,
)
from app.services.exif_service import extract_exif, get_dimensions
from app.services.histogram_service import compute_histogram
from app.services.focus_service import analyze as analyze_focus
from app.services.scanner import _classify_ext, scan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/photos", tags=["photos"])


# ---------------- cache keys ----------------

def _key(path: str) -> str:
    st = os.stat(path)
    h = hashlib.md5(path.encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"{h}-{st.st_size:x}-{int(st.st_mtime):x}"


def _thumb_path(key: str) -> Path:
    return settings.thumb_cache_dir / f"{key}.jpg"


def _preview_path(key: str) -> Path:
    return settings.preview_cache_dir / f"{key}.jpg"


# ---------------- routes ----------------

@router.post("/scan", response_model=ScanResult)
def scan_folder(req: ScanRequest):
    if settings.allowed_roots:
        allowed = any(
            str(Path(req.root).resolve()).startswith(Path(r).resolve().__str__())
            for r in settings.allowed_roots
        )
        if not allowed:
            raise HTTPException(403, f"Root not in allowed_roots: {req.root}")
    photos, skipped, errors = scan(req.root, req.recursive, req.include_hidden)
    return ScanResult(root=req.root, total=len(photos), photos=photos, skipped=skipped, errors=errors)


@router.get("/detail", response_model=PhotoDetail)
def photo_detail(path: str, with_histogram: bool = True, with_focus: bool = True):
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(404, f"File not found: {path}")
    size, mtime = safe_stat(p)
    width, height = get_dimensions(str(p))
    exif = extract_exif(str(p))
    key = _key(str(p))

    hist = None
    focus = None
    if with_histogram or with_focus:
        rgb = decode_to_array(str(p), max_dim=1600)
        if with_histogram:
            hist = compute_histogram(rgb).model_dump()
            hist = HistogramData(**hist)
        if with_focus:
            focus = analyze_focus(
                rgb,
                blur_threshold=settings.blur_threshold,
                face_blur_threshold=settings.face_blur_threshold,
                face_min_size=settings.face_min_size,
            )

    return PhotoDetail(
        id=key,
        path=str(p),
        name=p.name,
        ext=p.suffix.lower(),
        format=_classify_ext(p.suffix),
        size=size,
        mtime=mtime,
        width=width,
        height=height,
        has_preview=True,
        exif=exif,
        histogram=hist,
        focus=focus,
        thumb_url=f"/api/photos/thumb?path={p}",
        preview_url=f"/api/photos/preview?path={p}",
    )


@router.get("/thumb")
def thumb(path: str):
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(404, "File not found")
    key = _key(str(p))
    cache = _thumb_path(key)
    if not cache.exists():
        try:
            data = make_thumb(str(p), settings.max_thumb_size)
            cache.write_bytes(data)
        except Exception as exc:
            logger.error("thumb decode failed: %s", exc)
            raise HTTPException(500, f"Failed to decode image: {exc}")
    return Response(cache.read_bytes(), media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.get("/preview")
def preview(path: str, max_dim: int = Query(0, ge=0, le=8000)):
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(404, "File not found")
    key = _key(str(p))
    cache = _preview_path(key)
    if not cache.exists():
        try:
            dim = max_dim or settings.max_preview_size
            data = make_preview(str(p), dim)
            cache.write_bytes(data)
        except Exception as exc:
            logger.error("preview decode failed: %s", exc)
            raise HTTPException(500, f"Failed to decode image: {exc}")
    return Response(cache.read_bytes(), media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.get("/raw")
def raw_image(path: str, max_dim: int = Query(0, ge=0, le=8000)):
    """Stream the fully decoded image (PNG) — for color editing and analysis."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(404, "File not found")
    try:
        rgb = decode_to_array(str(p), max_dim=max_dim or 0)
        data = encode_jpeg(rgb, quality=92)
        return Response(data, media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"})
    except Exception as exc:
        raise HTTPException(500, f"Failed to decode: {exc}")
