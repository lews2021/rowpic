"""Color grading API (with AI hook)."""
from __future__ import annotations

import base64
import io
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.schemas import ColorAdjustRequest, ColorAdjustResult
from app.services.color_service import (
    adjust as color_adjust,
    apply_look,
    extract_look,
)
from app.services.decoder import decode_to_array

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/color", tags=["color"])


class ColorAdjustPathRequest(ColorAdjustRequest):
    image_path: str = Field(..., description="Absolute path to source image")


@router.post("/adjust_path", response_model=ColorAdjustResult)
def adjust_with_path(req: ColorAdjustPathRequest):
    try:
        rgb = decode_to_array(req.image_path, max_dim=2400)
    except Exception as exc:
        logger.exception("color adjust decode failed for %s", req.image_path)
        raise HTTPException(400, f"Failed to load image: {exc}")
    return color_adjust(rgb, req)


class ColorAdjustBytesRequest(ColorAdjustRequest):
    image_b64: str = Field(..., description="Base64 encoded image (PNG/JPEG)")


@router.post("/adjust", response_model=ColorAdjustResult)
def adjust_bytes(req: ColorAdjustBytesRequest):
    """In-memory adjust: client sends a base64 image, we return a base64 result.
    Use this for small previews; for files on disk use /adjust_path instead.
    """
    import numpy as np
    from PIL import Image

    try:
        raw = base64.b64decode(req.image_b64)
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        rgb = np.array(img, dtype=np.uint8)
        if max(rgb.shape[:2]) > 2400:
            scale = 2400 / float(max(rgb.shape[:2]))
            img = img.resize(
                (int(rgb.shape[1] * scale), int(rgb.shape[0] * scale)),
                Image.LANCZOS,
            )
            rgb = np.array(img, dtype=np.uint8)
    except Exception as exc:
        raise HTTPException(400, f"Failed to decode base64 image: {exc}")
    return color_adjust(rgb, req)


@router.get("/models")
def list_ai_models():
    """Report which AI color models are available on this machine."""
    available = []
    try:
        import onnxruntime  # noqa: F401
        available.append("onnxruntime")
    except Exception:
        pass
    try:
        import torch  # noqa: F401
        available.append("torch")
    except Exception:
        pass
    return {
        "enable_ai_color": settings.enable_ai_color,
        "ai_color_model": settings.ai_color_model,
        "available": available,
    }


# ----------------------------------------------------- "Learn Look" workflow

class LearnLookRequest(BaseModel):
    image_path: str = Field(..., description="Reference image to learn the look from")


@router.post("/learn_look")
def learn_look(req: LearnLookRequest):
    """Extract a transferable 'look' (channel CDFs + tone profile) from a
    reference image.  The returned dict can be POSTed to /apply_look on other
    images to apply the same look.  This is the AI 'transfer learning' path
    that needs no GPU.
    """
    try:
        rgb = decode_to_array(req.image_path, max_dim=800)
    except Exception as exc:
        raise HTTPException(400, f"Failed to load image: {exc}")
    return extract_look(rgb)


class ApplyLookRequest(BaseModel):
    image_path: str
    look: dict


@router.post("/apply_look", response_model=ColorAdjustResult)
def apply_look_endpoint(req: ApplyLookRequest):
    try:
        rgb = decode_to_array(req.image_path, max_dim=2400)
    except Exception as exc:
        raise HTTPException(400, f"Failed to load image: {exc}")
    out = apply_look(rgb, req.look)
    import base64 as _b64
    import cv2 as _cv
    ok, buf = _cv.imencode(".png", _cv.cvtColor(out, _cv.COLOR_RGB2BGR))
    if not ok:
        raise HTTPException(500, "Failed to encode result")
    return ColorAdjustResult(
        image_b64=_b64.b64encode(buf.tobytes()).decode("ascii"),
        width=out.shape[1],
        height=out.shape[0],
        applied={"ai": "look_transfer"},
    )