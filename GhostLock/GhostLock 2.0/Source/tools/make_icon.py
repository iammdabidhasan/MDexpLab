from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ICON_PATH = ASSETS / "ghostlock.ico"
PNG_PATH = ASSETS / "ghostlock.png"


def load_font(size):
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def make_icon(size):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = max(6, size // 5)
    pad = max(3, size // 14)

    draw.rounded_rectangle(
        (pad, pad, size - pad, size - pad),
        radius=radius,
        fill=(13, 21, 31, 255),
        outline=(61, 214, 163, 255),
        width=max(1, size // 20),
    )
    inner = pad + max(5, size // 8)
    draw.rounded_rectangle(
        (inner, inner + size // 14, size - inner, size - inner),
        radius=max(4, size // 9),
        fill=(24, 38, 53, 255),
    )

    shackle_width = max(2, size // 13)
    shackle_box = (
        size * 0.31,
        size * 0.23,
        size * 0.69,
        size * 0.61,
    )
    draw.arc(shackle_box, start=190, end=350, fill=(244, 247, 251, 255), width=shackle_width)

    body_box = (
        size * 0.28,
        size * 0.47,
        size * 0.72,
        size * 0.75,
    )
    draw.rounded_rectangle(
        body_box,
        radius=max(3, size // 12),
        fill=(61, 214, 163, 255),
    )
    key_x = size * 0.5
    key_y = size * 0.61
    draw.ellipse(
        (key_x - size * 0.055, key_y - size * 0.055, key_x + size * 0.055, key_y + size * 0.055),
        fill=(13, 21, 31, 255),
    )
    draw.rounded_rectangle(
        (key_x - size * 0.025, key_y, key_x + size * 0.025, key_y + size * 0.1),
        radius=max(1, size // 80),
        fill=(13, 21, 31, 255),
    )
    return image


def main():
    ASSETS.mkdir(exist_ok=True)
    base = make_icon(256)
    base.save(PNG_PATH)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    base.save(ICON_PATH, sizes=sizes)
    print(f"wrote {ICON_PATH}")


if __name__ == "__main__":
    main()
