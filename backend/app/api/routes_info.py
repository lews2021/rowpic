"""Static info / capabilities API."""
from __future__ import annotations

import platform
import sys

from fastapi import APIRouter
from app import __version__
from app.core.config import settings
from app.services.decoder import RAW_EXTS

router = APIRouter(prefix="/api", tags=["info"])


@router.get("/info")
def info():
    raw = sorted(RAW_EXTS)
    raster = sorted(set(settings.supported_extensions) - RAW_EXTS)
    return {
        "name": "rowpic",
        "version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "formats": {
            "raw": raw,
            "raster": raster,
        },
        "supported_extensions": settings.supported_extensions,
        "enable_ai_color": settings.enable_ai_color,
        "ai_color_model": settings.ai_color_model,
    }