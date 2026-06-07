"""Filesystem browsing API for the path picker.

Used by the frontend to build an expand/collapse tree of folders.  Honors
the same `ROWPIC_ALLOWED_ROOTS` whitelist as the scanner (when set).
"""
from __future__ import annotations

import logging
import os
import string
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fs", tags=["fs"])


def _is_allowed(path: str) -> bool:
    """If `allowed_roots` is configured, the path must be inside one of them."""
    if not settings.allowed_roots:
        return True
    try:
        p = str(Path(path).resolve())
    except Exception:
        return False
    return any(p.startswith(str(Path(r).resolve())) for r in settings.allowed_roots)


def _safe_iterdir(p: Path):
    try:
        return list(p.iterdir())
    except PermissionError as exc:
        raise HTTPException(403, f"Permission denied: {p}") from exc
    except OSError as exc:
        raise HTTPException(400, f"Cannot read directory: {exc}") from exc


def _list_drives_windows() -> List[str]:
    """Return available drive letters on Windows (e.g. ['C:\\', 'D:\\'])."""
    try:
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        return [f"{letter}:\\" for letter in string.ascii_uppercase if bitmask & (1 << (ord(letter) - ord("A")))]
    except Exception:
        return ["C:\\"]


class DirEntry(BaseModel):
    name: str
    path: str
    has_children: bool


class DirListing(BaseModel):
    path: str
    parent: Optional[str]
    dirs: List[DirEntry]
    file_count: int = 0
    total: int = 0


@router.get("/roots", response_model=List[str])
def list_roots():
    """List filesystem roots (Windows drives, or '/' on POSIX)."""
    if os.name == "nt":
        return _list_drives_windows()
    return ["/"]


@router.get("/list", response_model=DirListing)
def list_dir(
    path: str = Query(..., description="Directory to list."),
    include_files: bool = Query(False, description="Also count files in the directory."),
    limit: int = Query(500, ge=1, le=5000, description="Max subdirs to return"),
):
    """List immediate subdirectories of `path` (one level only).

    Returns directory metadata so the frontend can lazily expand the tree.
    """
    p = Path(path)
    if not p.exists():
        raise HTTPException(404, f"Path not found: {path}")
    if not p.is_dir():
        raise HTTPException(400, f"Not a directory: {path}")
    if not _is_allowed(path):
        raise HTTPException(403, f"Path not in allowed_roots: {path}")

    entries = _safe_iterdir(p)
    dirs: List[DirEntry] = []
    file_count = 0
    for e in entries:
        try:
            if e.is_dir():
                # Heuristic: peek one child to know if the node is expandable
                try:
                    has_children = any(True for _ in e.iterdir())
                except (PermissionError, OSError):
                    has_children = False
                dirs.append(DirEntry(name=e.name, path=str(e), has_children=has_children))
            elif e.is_file():
                file_count += 1
        except OSError:
            continue

    dirs.sort(key=lambda d: d.name.lower())
    if len(dirs) > limit:
        dirs = dirs[:limit]

    parent = None
    try:
        parent_path = p.parent
        if parent_path != p and parent_path.exists() and _is_allowed(str(parent_path)):
            parent = str(parent_path)
    except Exception:
        pass

    return DirListing(
        path=str(p),
        parent=parent,
        dirs=dirs,
        file_count=file_count,
        total=len(dirs) + file_count,
    )