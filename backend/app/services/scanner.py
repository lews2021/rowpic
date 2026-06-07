"""Folder scanner service."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable, List, Optional

from app.core.config import settings
from app.models.schemas import FileFormat, PhotoMeta
from app.services.decoder import is_raw, safe_stat
from app.services.exif_service import extract_exif, get_dimensions

logger = logging.getLogger(__name__)


_RAW_EXTS = {
    ".raw", ".arw", ".sr2", ".srf", ".nef", ".nrw", ".cr2", ".cr3",
    ".dng", ".orf", ".rw2", ".raf", ".pef", ".srw", ".3fr", ".iiq",
    ".x3f", ".mrw", ".mef", ".erf", ".kdc", ".dcr", ".fit", ".fts",
}


def _classify_ext(ext: str) -> FileFormat:
    e = ext.lower()
    if e in _RAW_EXTS:
        return FileFormat.RAW
    mapping = {
        ".jpg": FileFormat.JPEG, ".jpeg": FileFormat.JPEG,
        ".png": FileFormat.PNG,
        ".tif": FileFormat.TIFF, ".tiff": FileFormat.TIFF,
        ".webp": FileFormat.WEBP,
        ".bmp": FileFormat.BMP,
        ".heic": FileFormat.HEIC, ".heif": FileFormat.HEIC,
    }
    return mapping.get(e, FileFormat.OTHER)


def _iter_files(root: Path, recursive: bool, include_hidden: bool) -> Iterable[Path]:
    if recursive:
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if not include_hidden and any(part.startswith(".") for part in p.parts):
                continue
            if p.suffix.lower() in settings.supported_extensions:
                yield p
    else:
        for p in root.iterdir():
            if not p.is_file():
                continue
            if not include_hidden and p.name.startswith("."):
                continue
            if p.suffix.lower() in settings.supported_extensions:
                yield p


def scan(root: str, recursive: bool = True, include_hidden: bool = False,
         limit: Optional[int] = None) -> tuple[List[PhotoMeta], int, List[str]]:
    """Scan a folder, build PhotoMeta for each supported image.

    Returns (photos, skipped_count, errors).
    """
    p_root = Path(root).expanduser().resolve()
    if not p_root.exists() or not p_root.is_dir():
        return [], 0, [f"Root not found: {root}"]

    photos: List[PhotoMeta] = []
    skipped = 0
    errors: List[str] = []

    for i, path in enumerate(_iter_files(p_root, recursive, include_hidden)):
        if limit and i >= limit:
            break
        try:
            size, mtime = safe_stat(path)
            width, height = get_dimensions(path)
            exif = extract_exif(str(path))
            pid = f"{size:x}-{int(mtime):x}-{abs(hash(str(path))) & 0xFFFFFFFF:x}"
            photos.append(PhotoMeta(
                id=pid,
                path=str(path),
                name=path.name,
                ext=path.suffix.lower(),
                format=_classify_ext(path.suffix),
                size=size,
                mtime=mtime,
                width=width,
                height=height,
                has_preview=True,
                exif=exif,
            ))
        except Exception as exc:
            logger.warning("scan error on %s: %s", path, exc)
            errors.append(f"{path}: {exc}")
            skipped += 1
    return photos, skipped, errors
