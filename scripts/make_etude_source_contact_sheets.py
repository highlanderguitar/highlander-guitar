from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


source = Path(sys.argv[1])
output = Path(sys.argv[2])
output.mkdir(parents=True, exist_ok=True)
files = sorted(source.glob("image-*"))
font = ImageFont.load_default()
cell_w, cell_h = 360, 280
cols, rows = 4, 5
for sheet_index in range(0, len(files), cols * rows):
    canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(canvas)
    for local_index, path in enumerate(files[sheet_index:sheet_index + cols * rows]):
        col, row = local_index % cols, local_index // cols
        x, y = col * cell_w, row * cell_h
        try:
            with Image.open(path) as image:
                image = image.convert("RGB")
                image.thumbnail((cell_w - 16, cell_h - 34))
                px = x + (cell_w - image.width) // 2
                py = y + 22 + (cell_h - 28 - image.height) // 2
                canvas.paste(image, (px, py))
        except Exception as exc:
            draw.text((x + 8, y + 40), f"Unreadable: {exc}", fill="red", font=font)
        draw.text((x + 8, y + 5), path.name, fill="black", font=font)
        draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline="#888888")
    canvas.save(output / f"contact-{sheet_index // (cols * rows) + 1:02d}.jpg", quality=88)
print(f"created {len(list(output.glob('contact-*.jpg')))} sheets for {len(files)} images")
