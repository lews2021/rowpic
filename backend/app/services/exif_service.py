"""EXIF & shooting-parameter extraction.

RAW files: parse with rawpy (sizes, color matrix, makernotes).
Standard: parse with exifread (richer tag decoding) + raw fallback.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import exifread
import rawpy

from app.models.schemas import ExifInfo

logger = logging.getLogger(__name__)


_FRACTIONS = re.compile(r"^(\d+)/(\d+)$")


def _rational(value, as_float: bool = False):
    """Convert an exifread value (IFDRational / string) to float or string."""
    if value is None:
        return None
    if hasattr(value, "num") and hasattr(value, "den"):
        try:
            if value.den == 0:
                return None
            v = value.num / value.den
            return float(v) if as_float else f"{value.num}/{value.den}"
        except Exception:
            return None
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="ignore").strip("\x00").strip()
        except Exception:
            return None
    s = str(value).strip()
    if not s:
        return None
    m = _FRACTIONS.match(s)
    if m:
        n, d = int(m.group(1)), int(m.group(2))
        if d == 0:
            return None
        v = n / d
        return float(v) if as_float else s
    try:
        return float(s)
    except ValueError:
        return s


def _format_shutter(seconds: Optional[float]) -> Optional[str]:
    if seconds is None or seconds <= 0:
        return None
    if seconds >= 1:
        return f"{seconds:.1f}s"
    denom = round(1.0 / seconds)
    return f"1/{denom}s"


def _exposure_program_name(code) -> Optional[str]:
    mapping = {
        0: "Not defined", 1: "Manual", 2: "Program AE", 3: "Aperture-priority AE",
        4: "Shutter speed priority AE", 5: "Creative (Slow speed)", 6: "Action (High speed)",
        7: "Portrait", 8: "Landscape", 9: "Bulb",
    }
    try:
        c = int(float(str(code)))
    except (TypeError, ValueError):
        return None
    return mapping.get(c)


def _wb_name(code) -> Optional[str]:
    mapping = {
        0: "Auto", 1: "Manual", 2: "Daylight", 3: "Fluorescent",
        4: "Tungsten", 5: "Flash", 6: "Cloudy", 7: "Shade",
        8: "Kelvin", 9: "Custom",
    }
    try:
        c = int(float(str(code)))
    except (TypeError, ValueError):
        return None
    return mapping.get(c)


def _parse_exifread(path: str) -> ExifInfo:
    info = ExifInfo()
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=True)
    except Exception as exc:
        logger.debug("exifread failed for %s: %s", path, exc)
        return info

    def get(key, default=None):
        return tags.get(key, default)

    info.make = str(get("Image Make", "")).strip() or None
    info.model = str(get("Image Model", "")).strip() or None
    info.software = str(get("Image Software", "")).strip() or None
    info.lens = str(get("EXIF LensModel", "")).strip() or None
    info.lens_model = info.lens
    info.color_space = str(get("EXIF ColorSpace", "")).strip() or None

    fl = _rational(get("EXIF FocalLength"), as_float=True)
    if fl:
        info.focal_length = float(fl)
    fl35 = _rational(get("EXIF FocalLengthIn35mmFilm"), as_float=True)
    if fl35:
        info.focal_length_35mm = float(fl35)

    fnum = _rational(get("EXIF FNumber"), as_float=True)
    if fnum:
        info.aperture = float(fnum)

    expo = _rational(get("EXIF ExposureTime"), as_float=True)
    if expo:
        info.shutter_num = float(expo)
        info.shutter = _format_shutter(float(expo))

    iso_tag = get("EXIF ISOSpeedRatings") or get("EXIF PhotographicSensitivity")
    if iso_tag:
        try:
            info.iso = int(str(iso_tag).split(",")[0].strip())
        except (TypeError, ValueError):
            pass

    info.exposure_program = _exposure_program_name(_rational(get("EXIF ExposureProgram")))
    info.white_balance = _wb_name(_rational(get("EXIF WhiteBalance")))

    flash_val = _rational(get("EXIF Flash"), as_float=True)
    if flash_val is not None:
        try:
            info.flash = bool(int(float(flash_val)) & 1)
        except (TypeError, ValueError):
            info.flash = None

    dt = get("EXIF DateTimeOriginal") or get("Image DateTime")
    if dt:
        s = str(dt).strip()
        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                info.taken_at = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue

    orient = _rational(get("Image Orientation"), as_float=True)
    if orient:
        try:
            info.orientation = int(float(orient))
        except (TypeError, ValueError):
            pass

    # raw extras
    for key in ("EXIF ExposureBiasValue", "EXIF MeteringMode", "EXIF SceneCaptureType",
                "EXIF GainControl", "EXIF Contrast", "EXIF Saturation",
                "EXIF Sharpness", "EXIF DigitalZoomRatio"):
        v = _rational(get(key))
        if v is not None:
            info.raw_extras[key.split(".")[-1]] = v

    return info


def _parse_rawpy(path: str) -> ExifInfo:
    info = ExifInfo()
    try:
        with rawpy.imread(path) as raw:
            try:
                cam = raw.camera_name
                if cam:
                    info.model = cam.strip()
            except Exception:
                pass
            desc = raw.desc
            if desc:
                info.raw_extras["raw_desc"] = str(desc)[:300]
            # sizes
            info.raw_extras["raw_size"] = f"{raw.sizes.raw_width}x{raw.sizes.raw_height}"
            info.raw_extras["raw_type"] = str(raw.sizes.raw_type)
            # color_desc
            if raw.color_desc:
                info.raw_extras["raw_color_desc"] = str(raw.color_desc)
            # basic makernotes via topleft if available
            for attr in ("make", "model", "software"):
                v = getattr(raw, attr, None)
                if v and not getattr(info, attr):
                    setattr(info, attr, str(v).strip())
    except Exception as exc:
        logger.debug("rawpy exif failed for %s: %s", path, exc)
    return info


def extract_exif(path: str) -> ExifInfo:
    """Combine exifread + rawpy for best coverage."""
    info = _parse_exifread(path)
    # if it's a raw, enrich
    from app.services.decoder import is_raw
    if is_raw(path):
        raw_info = _parse_rawpy(path)
        # merge: keep richer values
        for fld in ("make", "model", "software", "lens", "lens_model", "focal_length",
                    "focal_length_35mm", "aperture", "shutter", "shutter_num", "iso",
                    "taken_at", "exposure_program", "white_balance"):
            existing = getattr(info, fld)
            new = getattr(raw_info, fld)
            if not existing and new:
                setattr(info, fld, new)
        # merge raw_extras
        for k, v in raw_info.raw_extras.items():
            info.raw_extras.setdefault(k, v)
    # synthesize lens label from make+model
    if not info.lens and info.make and info.model:
        info.lens = f"{info.make} {info.model}"
    return info


def get_dimensions(path: str) -> Tuple[int, int]:
    """Return (width, height) without fully decoding the pixels if possible."""
    from app.services.decoder import is_raw
    if is_raw(path):
        try:
            with rawpy.imread(path) as raw:
                return raw.sizes.width, raw.sizes.height
        except Exception:
            pass
    try:
        with open(path, "rb") as f:
            from PIL import Image
            img = Image.open(f)
            return img.size
    except Exception:
        return 0, 0
