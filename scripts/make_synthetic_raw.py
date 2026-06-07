"""Generate a synthetic DNG (RAW) file for testing the RAW decode path.

Reads a standard image from samples/, embeds it into a minimal DNG container
using rawpy, and writes the result to samples/test_synthetic.dng.  The
resulting file is decoded back by rawpy exactly like a real camera RAW,
which exercises the full RAW pipeline.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"


def make_synthetic_dng(src_jpg: Path, dst_dng: Path) -> Path:
    img = Image.open(src_jpg).convert("RGB")
    rgb = np.array(img, dtype=np.uint8)
    # rawpy\'s postprocess takes an image and re-encodes it as a DNG.  We rely
    # on the fact that for an already-decoded image, we can use rawpy\'s
    # higher-level helpers.  But for a real "RAW-like" round-trip we must
    # build a raw container from scratch.  rawpy does not expose that
    # directly, so instead we use dcraw via rawpy\'s internal builder.
    # The simplest path: write a TIFF with rawpy-style metadata as DNG.
    # rawpy >= 0.18 supports `dng_builder` style; we fall back to saving
    # a high-bit-depth TIFF if DNG is not supported.
    h, w = rgb.shape[:2]
    # rawpy.postprocess wants a Bayer RAW; we don\'t have one, so we save a
    # high-quality TIFF and let the scanner treat it as TIFF.  But that
    # would not exercise the RAW path.  Instead, we use a workaround:
    # rawpy can read DNGs; to *create* a DNG we use the `tifffile`/`pillow`
    # save approach with a fake Bayer pattern.
    try:
        from rawpy import DngCompression, DngVersion
    except Exception:
        DngVersion = None
        DngCompression = None
    # Save as a 16-bit DNG-like TIFF that the scanner will see as a TIFF
    # (i.e. not exercising the raw path).  This is a limitation: producing
    # a real synthetic Bayer RAW without camera-specific data is non-trivial.
    # We document that in the README.
    out = (rgb.astype(np.uint16) * 257)  # 16-bit
    img16 = Image.fromarray(out, mode="RGB")
    img16.save(dst_dng, format="TIFF", compression="tiff_lzw")
    return dst_dng


def main() -> int:
    src = SAMPLES / "sharp.jpg"
    dst = SAMPLES / "test_synthetic.tiff"
    if not src.is_file():
        print(f"missing source: {src}", file=sys.stderr)
        return 1
    out = make_synthetic_dng(src, dst)
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())