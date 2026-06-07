import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

os.makedirs("samples", exist_ok=True)

def make_synthetic(out_path, w=1800, h=1200, blur=False):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    # gradient background
    for y in range(h):
        for x in range(0, w, 4):
            arr[y, x:x+4, 0] = int(255*x/w)
            arr[y, x:x+4, 1] = int(255*y/h)
            arr[y, x:x+4, 2] = 128
    # sharp rectangle
    arr[300:600, 400:900] = (240, 240, 240)
    # sharp face-like region
    arr[700:900, 1000:1300] = (200, 200, 220)

    if blur:
        # heavy box blur
        from PIL import ImageFilter
        img = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=8))
        img.save(out_path, quality=85)
    else:
        Image.fromarray(arr).save(out_path, quality=92)

make_synthetic("samples/sharp.jpg", blur=False)
make_synthetic("samples/blurry.jpg", blur=True)
print("created sharp.jpg and blurry.jpg")
