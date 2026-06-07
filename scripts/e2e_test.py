"""End-to-end test: hits a running backend at $ROWPIC_URL (default 127.0.0.1:8765)
and exercises every major API path.

Run with the backend already started (e.g. via scripts/start_web.py).
Exits 0 on success, 1 on any failure.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import urllib.request
import urllib.error

BASE = os.environ.get("ROWPIC_URL", "http://127.0.0.1:8765")
SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def http_json(path: str, method: str = "GET", body: Any = None, timeout: float = 60.0) -> Any:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ct = resp.headers.get("Content-Type", "")
        if "application/json" in ct:
            return json.loads(resp.read().decode("utf-8"))
        return resp.read()


def http_bytes(path: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(f"{BASE}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def main() -> int:
    failures: List[str] = []

    def check(cond: bool, name: str) -> None:
        mark = "OK " if cond else "FAIL"
        print(f"  [{mark}] {name}")
        if not cond:
            failures.append(name)

    print(f"[test] target: {BASE}")
    print(f"[test] samples: {SAMPLES}")

    # 1. health
    print("\n[1] health")
    try:
        h = http_json("/healthz")
        check(h.get("ok") is True, "/healthz ok")
    except Exception as exc:
        print(f"  cannot reach backend: {exc}")
        return 1

    # 2. info
    print("\n[2] info")
    info = http_json("/api/info")
    check(isinstance(info, dict), "/api/info returns dict")
    print(f"      name={info.get('name')} version={info.get('version')}")
    print(f"      formats={list((info.get('formats') or {}).keys())}")

    # 3. scan
    print("\n[3] scan samples folder")
    scan = http_json("/api/photos/scan", "POST", {"root": str(SAMPLES), "recursive": True})
    photos = scan.get("photos", [])
    check(len(photos) > 0, f"scan returned {len(photos)} photos")
    if not photos:
        return 1
    sample = photos[0]
    print(f"      sample: {sample['name']}  format={sample['format']}  size={sample['size']}")

    # 4. thumb
    print("\n[4] thumb")
    t0 = time.time()
    thumb = http_bytes(f"/api/photos/thumb?path={urllib.parse.quote(sample['path'])}")
    check(len(thumb) > 100, f"thumb {len(thumb)} bytes in {(time.time()-t0)*1000:.0f}ms")

    # 5. preview
    print("\n[5] preview")
    t0 = time.time()
    prev = http_bytes(f"/api/photos/preview?path={urllib.parse.quote(sample['path'])}")
    check(len(prev) > 1000, f"preview {len(prev)} bytes in {(time.time()-t0)*1000:.0f}ms")

    # 6. detail
    print("\n[6] detail (exif + histogram + focus)")
    t0 = time.time()
    detail = http_json(f"/api/photos/detail?path={urllib.parse.quote(sample['path'])}")
    check(detail.get("width", 0) > 0, f"width={detail.get('width')}")
    check(detail.get("exif") is not None, "exif present")
    hist = detail.get("histogram")
    check(hist is not None and len(hist.get("luminance", [])) == 256, "histogram 256 bins")
    focus = detail.get("focus")
    check(focus is not None, "focus present")
    print(f"      sharpness={focus['overall_sharpness']:.1f}  quality={focus['overall_quality']}  "
          f"faces={len(focus['faces'])}  exif_keys={list((detail['exif'] or {}).keys())[:6]}")
    print(f"      detail in {(time.time()-t0)*1000:.0f}ms")

    # 7. color adjust (auto)
    print("\n[7] color adjust (auto)")
    t0 = time.time()
    res = http_json("/api/color/adjust_path", "POST",
                    {"image_path": sample["path"], "auto": True})
    check("image_b64" in res and len(res["image_b64"]) > 100, "auto adjust returns image")
    check(res.get("applied", {}).get("auto") is True, "auto flag recorded")
    print(f"      size={res['width']}x{res['height']}  applied={res['applied']}  {(time.time()-t0)*1000:.0f}ms")

    # 8. color adjust (manual)
    print("\n[8] color adjust (manual exposure/contrast)")
    res = http_json("/api/color/adjust_path", "POST",
                    {"image_path": sample["path"], "exposure": 0.3, "contrast": 1.15,
                     "saturation": 1.1, "temperature": 5})
    check("image_b64" in res, "manual adjust returns image")
    print(f"      applied={res['applied']}")

    # 9. AI look
    print("\n[9] AI look (builtin)")
    res = http_json("/api/color/adjust_path", "POST",
                    {"image_path": sample["path"], "ai": True, "ai_model": "builtin"})
    check("image_b64" in res, "AI look returns image")
    check("ai" in res["applied"], f"AI applied flag: {res['applied']}")
    print(f"      applied={res['applied']}")

    # 10. learn look + apply
    print("\n[10] learn_look + apply_look (transfer)")
    if len(photos) >= 2:
        ref = photos[0]
        target = photos[1]
        look = http_json("/api/color/learn_look", "POST", {"image_path": ref["path"]})
        check("channel_cdfs" in look, "learn_look returns CDFs")
        applied = http_json("/api/color/apply_look", "POST",
                            {"image_path": target["path"], "look": look})
        check("image_b64" in applied, "apply_look returns image")
        print(f"      learned means={look['channel_means']}  ->  size={applied['width']}x{applied['height']}")
    else:
        print("      skipped (need >=2 sample images)")

    # 11. classify
    print("\n[11] classify")
    cls = http_json("/api/classify/run", "POST",
                    {"rules": ["blurry_face", "blurry", "exposure"], "move": False,
                     "dest_template": "{category}/{name}", "photos": photos})
    check("per_photo" in cls, "classify returns per_photo")
    print(f"      categories={cls['categories']}  total={cls['total']}")

    # 12. duplicates
    print("\n[12] duplicates (pHash)")
    dup = http_json("/api/tools/duplicates", "POST", {"photos": photos, "threshold": 10})
    check("groups" in dup, "duplicates endpoint responds")
    print(f"      hashed={dup['hashed']}/{dup['total']}  groups={len(dup['groups'])}  duplicates={dup['duplicates']}")

    # 13. color models
    print("\n[13] color /models")
    m = http_json("/api/color/models")
    print(f"      enable_ai_color={m['enable_ai_color']}  model={m['ai_color_model']}  available={m['available']}")

    print("\n" + "=" * 50)
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    import urllib.parse  # late import for clarity
    raise SystemExit(main())