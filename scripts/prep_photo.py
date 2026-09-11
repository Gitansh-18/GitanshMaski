from pathlib import Path

from PIL import Image
from rembg import remove


INPUT = Path("source-photo.jpg")
OUTPUT = Path("source-prepped.png")


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Could not find {INPUT}")

    print("Loading photo...")

    original = Image.open(INPUT).convert("RGBA")

    print("Removing background...")

    foreground = remove(original).convert("RGBA")

    # Create a clean white background
    background = Image.new(
        "RGBA",
        foreground.size,
        (255, 255, 255, 255)
    )

    # Put the subject on the background
    composited = Image.alpha_composite(
        background,
        foreground
    )

    # Keep the original colors
    result = composited.convert("RGB")

    result.save(
        OUTPUT,
        format="PNG",
        optimize=True
    )

    print(f"Done: {OUTPUT}")


if __name__ == "__main__":
    main()
