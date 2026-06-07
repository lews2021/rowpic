"""Perceptual hash (pHash) for near-duplicate detection.

Implementation: 64-bit DCT-based pHash, similar to Christoph Zauner\'s
"pHash" approach.  We downscale to 32x32 grayscale, take the 2D DCT,
keep the top-left 8x8 low-frequency block (excluding DC), compute the
median, and emit a 64-bit hash from the sign map.

Two images with Hamming distance <= 10 are considered near-duplicates.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

import numpy as np
from PIL import Image, ImageOps


def _dct_2d(a: np.ndarray) -> np.ndarray:
    """Pure NumPy 2D DCT-II (no scipy dependency)."""
    n, m = a.shape
    # 1D DCT-II rows then columns
    def dct1(x: np.ndarray) -> np.ndarray:
        n = x.shape[-1]
        k = np.arange(n)[None, :]
        i = np.arange(n)[:, None]
        coef = np.cos(np.pi / n * (i + 0.5) * k)
        return coef @ x
    A = dct1(a)
    return dct1(A.T).T


def phash(rgb: np.ndarray, hash_size: int = 8, highfreq_factor: int = 4) -> int:
    """Compute a 64-bit (default) perceptual hash from an RGB uint8 array."""
    if rgb.dtype != np.uint8:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    img = Image.fromarray(rgb).convert("L")
    # 1) remove EXIF orientation
    #    (PIL\'s ImageOps.exif_transpose on a "L" image only needs the tag)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    # 2) resize to (hash_size * highfreq_factor)
    n = hash_size * highfreq_factor
    img = img.resize((n, n), Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float32)
    # 3) subtract mean to be robust to exposure
    arr = arr - arr.mean()
    # 4) DCT
    dct = _dct_2d(arr)
    # 5) keep top-left hash_size x hash_size
    low = dct[:hash_size, :hash_size]
    # 6) median excluding DC
    flat = low.flatten()
    med = np.median(flat[1:]) if flat.size > 1 else 0.0
    # 7) bit pattern
    bits = (low > med).flatten()
    h = 0
    for b in bits:
        h = (h << 1) | (1 if b else 0)
    return int(h)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def hamming_norm(a: int, b: int) -> float:
    return hamming(a, b) / 64.0


def find_duplicates(hashes: List[Tuple[str, int]], threshold: int = 10) -> List[List[str]]:
    """Group near-duplicate paths.  Returns a list of groups (>=2 members)."""
    parent = list(range(len(hashes)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    n = len(hashes)
    for i in range(n):
        for j in range(i + 1, n):
            if hamming(hashes[i][1], hashes[j][1]) <= threshold:
                union(i, j)
    groups: dict = {}
    for i in range(n):
        r = find(i)
        groups.setdefault(r, []).append(hashes[i][0])
    return [g for g in groups.values() if len(g) >= 2]