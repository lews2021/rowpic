"""Color grading service.

Pipeline (CPU-first, OpenCV + NumPy):
  1) decode -> RGB float32 (0..1)
  2) auto white balance (gray-world)
  3) auto exposure (mean-luma target)
  4) contrast around 0.5
  5) highlights / shadows lift
  6) whites / blacks
  7) saturation + vibrance
  8) temperature (warm/cool) + tint (green/magenta)
  9) encode back to PNG/JPEG bytes

AI look (learnable, no GPU required):
  - default: gray-world WB + tone transfer via cumulative histogram matching
    against an internal "pleasant" reference look, plus vibrance.
  - the public entry point `apply_look(rgb, look)` accepts a pre-computed
    look dict so the UI can offer "Learn from this photo -> apply to others".
  - `run_ai_model(rgb, model_name)` dispatches to a registered model. Models
    may be lightweight NumPy heuristics or ONNX / PyTorch networks; both are
    loaded lazily on first use and cached for the process lifetime.

All public functions are pure (input rgb -> output rgb) so the same code
works for one-off adjustment, batch processing, and live preview.
"""
from __future__ import annotations

import base64
import io
import logging
import threading
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import cv2
import numpy as np

from app.models.schemas import ColorAdjustRequest, ColorAdjustResult
from app.core.config import settings

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------- helpers

_LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def _to_float(rgb: np.ndarray) -> np.ndarray:
    return rgb.astype(np.float32) / 255.0


def _to_uint8(rgb: np.ndarray) -> np.ndarray:
    return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)


def _luma3(img: np.ndarray) -> np.ndarray:
    """Luminance as a (H, W, 1) broadcastable view."""
    return (img @ _LUMA)[..., None]


def _gray_world_wb(img: np.ndarray) -> np.ndarray:
    """Scale channels so their means are equal (gray-world assumption)."""
    means = img.reshape(-1, 3).mean(axis=0)
    gray = means.mean()
    scale = gray / np.maximum(means, 1e-6)
    return np.clip(img * scale, 0, 1)


def _auto_exposure(img: np.ndarray, target: float = 0.45) -> np.ndarray:
    """Multiplicative exposure so that the mean luminance reaches `target`."""
    lum = _luma3(img)
    m = float(lum.mean()) or 1e-6
    return np.clip(img * (target / m), 0, 1)


def _exposure(img: np.ndarray, ev: float) -> np.ndarray:
    return img * (2.0 ** ev)


def _contrast(img: np.ndarray, c: float) -> np.ndarray:
    return (img - 0.5) * c + 0.5


def _highlights_shadows(img: np.ndarray, hi: float, sh: float) -> np.ndarray:
    lum = _luma3(img)
    hi_mask = np.clip((lum - 0.5) / 0.5, 0, 1)
    sh_mask = np.clip((0.5 - lum) / 0.5, 0, 1)
    out = img - hi_mask * hi * 0.5
    out = out + sh_mask * sh * 0.5
    return out


def _whites_blacks(img: np.ndarray, w: float, b: float) -> np.ndarray:
    out = img + w * 0.15
    return out - b * 0.15


def _saturation(img: np.ndarray, s: float) -> np.ndarray:
    lum = _luma3(img)
    return lum + (img - lum) * s


def _vibrance(img: np.ndarray, v: float) -> np.ndarray:
    """Boost saturation more for low-saturation pixels (skin-tones friendly)."""
    lum = _luma3(img)
    sat = np.max(img, axis=-1, keepdims=True) - np.min(img, axis=-1, keepdims=True)
    boost = (1.0 - np.clip(sat, 0, 1))
    return img + (img - lum) * v * boost * 0.5


def _temperature_tint(img: np.ndarray, temp: float, tint: float) -> np.ndarray:
    """temp: -100..100 (negative=cooler, positive=warmer). tint: -100..100 (neg=green, pos=magenta)."""
    t = temp / 100.0
    tn = tint / 100.0
    out = img.copy()
    out[..., 0] += t * 0.10
    out[..., 1] += t * 0.02
    out[..., 2] -= t * 0.10
    out[..., 0] -= tn * 0.04
    out[..., 1] += tn * 0.06
    out[..., 2] -= tn * 0.04
    return out


def _auto_tone(img: np.ndarray) -> np.ndarray:
    """Per-channel percentile stretch to [0.5%, 99.5%]."""
    out = np.zeros_like(img)
    for c in range(3):
        ch = img[..., c]
        lo, hi = np.percentile(ch, [0.5, 99.5])
        if hi - lo < 1e-6:
            out[..., c] = ch
        else:
            out[..., c] = (ch - lo) / (hi - lo)
    return out


# ----------------------------------------------------- histogram matching (AI)

def _cdf(sample: np.ndarray):
    """Return a normalized CDF for a 1D histogram of values in [0, 1]."""
    hist, bins = np.histogram(sample, bins=256, range=(0.0, 1.0))
    cdf = hist.cumsum()
    cdf = cdf / cdf[-1] if cdf[-1] > 0 else cdf
    return cdf, bins


def _match_to_cdf(src: np.ndarray, ref_cdfs, ref_bins) -> np.ndarray:
    """Map `src` so its per-channel CDF aligns with the reference CDFs."""
    out = np.zeros_like(src)
    for c in range(3):
        s_cdf, _ = _cdf(src[..., c].ravel())
        interp = np.interp(s_cdf, ref_cdfs[c], ref_bins[c][1:])
        idx = np.clip((src[..., c] * 255.0).astype(np.int32), 0, 255)
        out[..., c] = interp[idx]
    return out


def _reference_cdfs():
    """Built-in 'pleasant' reference CDFs (one per channel).

    Mimics a slightly warm, mid-contrast look that flatters most photos.
    """
    x = np.linspace(0.0, 1.0, 256)
    s = 1.0 / (1.0 + np.exp(-8 * (x - 0.5)))  # logistic S-curve
    s = (s - s.min()) / (s.max() - s.min())
    bins = np.concatenate([[0.0], x])
    warm_r = np.clip(s * 1.04, 0, 1)
    warm_g = s
    warm_b = np.clip(s * 0.97, 0, 1)
    return [warm_r, warm_g, warm_b], [bins, bins, bins]


def _histogram_transfer(img: np.ndarray) -> np.ndarray:
    cdfs, bins = _reference_cdfs()
    return _match_to_cdf(img, cdfs, bins)


# ----------------------------------------------------- learnable "look"

def extract_look(rgb_uint8: np.ndarray) -> dict:
    """Extract a transferable color/tone profile from a reference image.

    The resulting dict can be serialized to JSON and reused for batch
    processing.  This is the 'AI Look' learnable representation.
    """
    img = _to_float(rgb_uint8)
    cdfs = []
    bins_per = []
    for c in range(3):
        cdf, bins = _cdf(img[..., c].ravel())
        cdfs.append(cdf.tolist())
        bins_per.append(bins.tolist())
    means = img.reshape(-1, 3).mean(axis=0).tolist()
    lum = float((img @ _LUMA).mean())
    return {
        "version": 1,
        "channel_cdfs": cdfs,
        "channel_bins": bins_per,
        "channel_means": means,
        "mean_luminance": lum,
    }


def apply_look(rgb_uint8: np.ndarray, look: dict) -> np.ndarray:
    """Apply a previously extracted look to a new image."""
    if not look or not look.get("channel_cdfs"):
        return rgb_uint8
    img = _to_float(rgb_uint8)
    cdfs = [np.asarray(c, dtype=np.float32) for c in look["channel_cdfs"]]
    bins = [np.asarray(b, dtype=np.float32) for b in look["channel_bins"]]
    out = np.zeros_like(img)
    for c in range(3):
        s_cdf, _ = _cdf(img[..., c].ravel())
        interp = np.interp(s_cdf, cdfs[c], bins[c][1:])
        idx = np.clip((img[..., c] * 255.0).astype(np.int32), 0, 255)
        out[..., c] = interp[idx]
    return _to_uint8(np.clip(out, 0, 1))


# ----------------------------------------------------- AI model registry

_MODEL_REGISTRY: Dict[str, Callable[[np.ndarray], np.ndarray]] = {}
_MODEL_LOCK = threading.Lock()
_MODEL_LOADED: Dict[str, bool] = {}


def register_ai_model(name: str, fn: Callable[[np.ndarray], np.ndarray]) -> None:
    _MODEL_REGISTRY[name] = fn


def _builtin_ai_look(img: np.ndarray) -> np.ndarray:
    """The default no-model AI look.  Good baseline; replaceable via registry."""
    out = _gray_world_wb(img)
    out = _auto_exposure(out, 0.45)
    out = _histogram_transfer(out)
    out = _contrast(out, 1.05)
    out = _saturation(out, 1.08)
    out = _vibrance(out, 0.35)
    out = _temperature_tint(out, 4.0, 0.0)
    return out


register_ai_model("builtin", _builtin_ai_look)
register_ai_model("auto", _builtin_ai_look)


def _try_load_onnx_model(name: str) -> Optional[Callable[[np.ndarray], np.ndarray]]:
    """Lazy-load a Zero-DCE-style ONNX model from models/<name>.onnx.

    Contract: model takes (1, 3, H, W) float32 in [0, 1] and returns the same
    shape.  H and W must be divisible by 8.
    """
    try:
        import onnxruntime as ort
    except Exception:
        return None
    path_candidates = [
        Path(__file__).resolve().parent.parent.parent / "models" / f"{name}.onnx",
        Path.cwd() / "models" / f"{name}.onnx",
    ]
    for p in path_candidates:
        if p.is_file():
            sess = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
            in_name = sess.get_inputs()[0].name
            out_name = sess.get_outputs()[0].name

            def _run(img, _sess=sess, _in=in_name, _out=out_name):
                h0, w0 = img.shape[:2]
                ph = (8 - h0 % 8) % 8
                pw = (8 - w0 % 8) % 8
                x = np.pad(img, ((0, ph), (0, pw), (0, 0)), mode="reflect")
                x = np.transpose(x, (2, 0, 1))[None].astype(np.float32)
                y = _sess.run([_out], {_in: x})[0]
                y = np.transpose(y[0], (1, 2, 0))[:h0, :w0]
                return np.clip(y, 0, 1)

            return _run
    return None


def run_ai_model(img: np.ndarray, model_name: Optional[str] = None) -> Tuple[np.ndarray, str]:
    """Run the requested AI model.  Falls back to `builtin` if the model
    cannot be loaded.
    """
    name = (model_name or settings.ai_color_model or "builtin").lower()
    with _MODEL_LOCK:
        if name in _MODEL_REGISTRY and _MODEL_LOADED.get(name):
            return _MODEL_REGISTRY[name](img), name
        if name not in _MODEL_LOADED:
            loader = _try_load_onnx_model(name)
            if loader is not None:
                _MODEL_REGISTRY[name] = loader
                _MODEL_LOADED[name] = True
                return loader(img), name
            _MODEL_LOADED[name] = False
            logger.info("AI model '%s' not found on disk; using builtin", name)
    return _MODEL_REGISTRY["builtin"](img), "builtin"


# --------------------------------------------------------------------- public

def adjust(rgb: np.ndarray, req: ColorAdjustRequest) -> ColorAdjustResult:
    img = _to_float(rgb)
    h, w = img.shape[:2]
    applied = {}

    if req.ai:
        out, used = run_ai_model(img, req.ai_model)
        img = out
        applied["ai"] = used
    else:
        if req.auto:
            img = _auto_tone(img)
            applied["auto"] = True
        if req.exposure:
            img = _exposure(img, req.exposure); applied["exposure"] = req.exposure
        if req.contrast and req.contrast != 1.0:
            img = _contrast(img, req.contrast); applied["contrast"] = req.contrast
        if req.highlights:
            img = _highlights_shadows(img, req.highlights, 0); applied["highlights"] = req.highlights
        if req.shadows:
            img = _highlights_shadows(img, 0, req.shadows); applied["shadows"] = req.shadows
        if req.whites:
            img = _whites_blacks(img, req.whites, 0); applied["whites"] = req.whites
        if req.blacks:
            img = _whites_blacks(img, 0, req.blacks); applied["blacks"] = req.blacks
        if req.saturation and req.saturation != 1.0:
            img = _saturation(img, req.saturation); applied["saturation"] = req.saturation
        if req.vibrance:
            img = _vibrance(img, req.vibrance); applied["vibrance"] = req.vibrance
        if req.temperature or req.tint:
            img = _temperature_tint(img, req.temperature, req.tint)
            applied["temperature"] = req.temperature
            applied["tint"] = req.tint

    img = np.clip(img, 0, 1)
    out = _to_uint8(img)
    ok, buf = cv2.imencode(".png", cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    if not ok:
        raise RuntimeError("Failed to encode adjusted image")
    return ColorAdjustResult(
        image_b64=base64.b64encode(buf.tobytes()).decode("ascii"),
        width=w,
        height=h,
        applied=applied,
    )


def auto_adjust(rgb: np.ndarray) -> np.ndarray:
    """Returns a numpy RGB uint8 array (no base64) - used by the batch classifier."""
    img = _to_float(rgb)
    img = _auto_tone(img)
    return _to_uint8(img)