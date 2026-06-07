"""Generate placeholder Tauri icons (PNG + ICO)."""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "src-tauri", "icons")
os.makedirs(OUT, exist_ok=True)

def make(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (14, 16, 20, 255))
    d = ImageDraw.Draw(img)
    # outer ring
    pad = max(2, size // 16)
    d.ellipse([pad, pad, size - pad, size - pad], outline=(77, 171, 247, 255), width=max(1, size // 24))
    # camera body
    bw = size * 0.55
    bh = size * 0.4
    bx = (size - bw) / 2
    by = (size - bh) / 2 + size * 0.05
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=size * 0.05,
                        fill=(28, 32, 39, 255), outline=(116, 192, 252, 255),
                        width=max(1, size // 32))
    # lens
    lr = size * 0.16
    cx = size / 2
    cy = by + bh / 2
    d.ellipse([cx - lr, cy - lr, cx + lr, cy + lr], fill=(14, 16, 20, 255),
              outline=(116, 192, 252, 255), width=max(1, size // 32))
    # inner glass
    ir = size * 0.08
    d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=(77, 171, 247, 255))
    # top bump (viewfinder)
    bw2 = size * 0.2
    bh2 = size * 0.05
    bx2 = cx - bw2 / 2
    by2 = by - bh2
    d.rounded_rectangle([bx2, by2, bx2 + bw2, by2 + bh2 * 2], radius=size * 0.01,
                        fill=(28, 32, 39, 255), outline=(116, 192, 252, 255),
                        width=max(1, size // 32))
    return img

sizes = [32, 128, 256, 512]
for s in sizes:
    img = make(s)
    img.save(os.path.join(OUT, f"{s}x{s}.png"))
    img.save(os.path.join(OUT, f"{s}x{s}@2x.png" if s < 256 else f"{s}x{s}.png"))
img128 = make(128)
img128.save(os.path.join(OUT, "icon.png"))
img256 = make(256)
# ICO with multiple sizes
ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ico_imgs = [make(s).resize(sz, Image.LANCZOS) for sz in ico_sizes]
ico_imgs[0].save(os.path.join(OUT, "icon.ico"), sizes=[i.size for i in ico_imgs],
                  append_images=ico_imgs[1:])
# ICNS (basic) - we save a PNG, Tauri tolerates this for cross-platform
try:
    make(512).save(os.path.join(OUT, "icon.icns"))
except Exception as e:
    print("icns skip:", e)
print("icons written to", OUT)
