"""Image decoding service.

Handles RAW (via rawpy / LibRaw) and standard raster formats. Returns
RGB uint8 numpy arrays plus a thumbnail-friendly preview.
"""
from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Tuple

import numpy as np
import rawpy
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)


RAW_EXTS = {
    ".raw", ".arw", ".sr2", ".srf", ".nef", ".nrw", ".cr2", ".cr3",
    ".dng", ".orf", ".rw2", ".raf", ".pef", ".srw", ".3fr", ".iiq",
    ".x3f", ".mrw", ".mef", ".erf", ".kdc", ".dcr", ".fit", ".fts",
}


def is_raw(path: str | Path) -> bool:
    return Path(path).suffix.lower() in RAW_EXTS


def decode_to_array(
    path: str | Path,
    max_dim: int = 0,
    apply_orientation: bool = True,
) -> np.ndarray:
    """Decode an image (RAW or raster) to an RGB uint8 numpy array.

    Args:
        path: file path
        max_dim: if > 0, downscale so the longer edge <= this value
        apply_orientation: apply EXIF orientation if present
    """
    path = str(path)
    if is_raw(path):
        return _decode_raw(path, max_dim)
    return _decode_standard(path, max_dim, apply_orientation)


def _decode_raw(path: str, max_dim: int) -> np.ndarray:
    try:
        with rawpy.imread(path) as raw:
            # use_camera_wb gives a reasonable starting white balance
            try:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    no_auto_bright=False,
                    output_bps=8,
                    demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
                )
            except Exception:
                rgb = raw.postprocess(output_bps=8)
            h, w = rgb.shape[:2]
            if max_dim and max(h, w) > max_dim:
                scale = max_dim / float(max(h, w))
                img = Image.fromarray(rgb)
                img = img.resize(
                    (int(w * scale), int(h * scale)),
                    Image.LANCZOS,
                )
                rgb = np.array(img)
            return rgb
    except Exception as exc:
        logger.warning("rawpy failed for %s: %s, falling back to embedded preview", path, exc)
        return _decode_standard(path, max_dim, apply_orientation=True)


def _decode_standard(path: str, max_dim: int, apply_orientation: bool) -> np.ndarray:
    try:
        img = Image.open(path)
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Unsupported or corrupt image: {path}") from exc

    if apply_orientation:
        img = ImageOps.exif_transpose(img)

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")

    w, h = img.size
    if max_dim and max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    return np.array(img, dtype=np.uint8)


def encode_png(arr: np.ndarray) -> bytes:
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def encode_jpeg(arr: np.ndarray, quality: int = 92) -> bytes:
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def make_thumb(path: str, max_dim: int) -> bytes:
    arr = decode_to_array(path, max_dim=max_dim)
    return encode_jpeg(arr, quality=85)


def make_preview(path: str, max_dim: int) -> bytes:
    arr = decode_to_array(path, max_dim=max_dim)
    return encode_jpeg(arr, quality=90)


def safe_stat(path: str | Path) -> Tuple[int, float]:
    """Return (size_bytes, mtime_epoch). Returns (-1, 0) on error."""
    try:
        st = os.stat(str(path))
        return st.st_size, st.st_mtime
    except OSError:
        return -1, 0.0
