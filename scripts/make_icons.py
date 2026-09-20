"""Draw a minimal native extension icon; no remote assets."""

from pathlib import Path

from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1] / "extension" / "icons"
root.mkdir(parents=True, exist_ok=True)
for size in (16, 48, 128):
    scale = 4
    canvas = Image.new("RGBA", (size * scale, size * scale), "#f4f7f5")
    draw = ImageDraw.Draw(canvas)
    inset = round(size * scale * 0.2)
    diameter = round(size * scale * 0.5)
    stroke = max(3, round(size * scale * 0.075))
    draw.ellipse((inset, inset, inset + diameter, inset + diameter), outline="#0b7565", width=stroke)
    inner = round(size * scale * 0.35)
    draw.ellipse((inner, inner, inner + round(size * scale * 0.18), inner + round(size * scale * 0.18)), fill="#b7dfca")
    draw.line((inset + diameter - stroke, inset + diameter - stroke,
               round(size * scale * 0.84), round(size * scale * 0.84)), fill="#0b7565", width=stroke)
    canvas.resize((size, size), Image.Resampling.LANCZOS).save(root / f"icon{size}.png")

