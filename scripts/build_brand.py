"""Render the original landscape-light icon for this community integration."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "custom_components/enbrighten_vibe/brand"


def main() -> None:
    """Create square PNG brand assets from simple original geometry."""
    image = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, 1023, 1023), radius=220, fill="#102235")
    for center, color in ((250, "#fb7185"), (512, "#5ee1aa"), (774, "#71b8ff")):
        draw.polygon(
            [
                (center - 62, 540),
                (center - 125, 190),
                (center + 125, 190),
                (center + 62, 540),
            ],
            fill=color,
        )
        draw.line((center, 660, center, 838), fill="#e7f0f7", width=33)
        draw.rounded_rectangle(
            (center - 92, 530, center + 92, 664), radius=42, fill="#e7f0f7"
        )
        draw.rounded_rectangle(
            (center - 66, 546, center + 66, 576), radius=14, fill=color
        )
        draw.ellipse((center - 20, 590, center + 20, 630), fill="#102235")
    draw.line((150, 842, 874, 842), fill="#e7f0f7", width=24)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename, size in (("icon.png", 256), ("icon@2x.png", 512)):
        image.resize((size, size), Image.Resampling.LANCZOS).save(
            OUTPUT / filename, optimize=True
        )


if __name__ == "__main__":
    main()
