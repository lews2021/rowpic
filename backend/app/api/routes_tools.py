"""Tooling endpoints: duplicate detection, cache stats, format support matrix."""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.schemas import PhotoMeta
from app.services.decoder import decode_to_array
from app.services.phash_service import find_duplicates, phash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


class DuplicateRequest(BaseModel):
    photos: List[PhotoMeta] = Field(..., description="Photos to scan for duplicates")
    threshold: int = Field(10, ge=0, le=32, description="Hamming distance threshold (0..32)")


@router.post("/duplicates")
def detect_duplicates(req: DuplicateRequest):
    """Find near-duplicate groups using perceptual hashing (DCT pHash)."""
    hashes = []
    skipped = []
    for p in req.photos:
        try:
            rgb = decode_to_array(p.path, max_dim=512)
            h = phash(rgb)
            hashes.append((p.path, h))
        except Exception as exc:
            logger.debug("phash skip %s: %s", p.path, exc)
            skipped.append(p.path)
    groups = find_duplicates(hashes, threshold=req.threshold)
    return {
        "total": len(req.photos),
        "hashed": len(hashes),
        "skipped": skipped,
        "groups": groups,
        "duplicates": sum(len(g) - 1 for g in groups),
    }


@router.post("/phash")
def single_phash(body: dict):
    """Compute a single 64-bit pHash from a path (for debugging)."""
    path = body.get("path")
    if not path:
        raise HTTPException(400, "path required")
    try:
        rgb = decode_to_array(path, max_dim=512)
        h = phash(rgb)
        return {"path": path, "phash": f"{h:016x}"}
    except Exception as exc:
        raise HTTPException(400, f"Failed: {exc}")