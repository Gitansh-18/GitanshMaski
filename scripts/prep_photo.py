from pathlib import Path

import cv2
import numpy as np
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

    # White background
    white = Image.new("RGBA", foreground.size, (255, 255, 255, 255))

    # Composite the subject onto white
    composited = Image.alpha_composite(white, foreground)

    # Convert to grayscale
    gray = np.array(composited.convert("L"))

    # Improve local contrast using CLAHE
    print("Enhancing contrast...")
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(gray)

    # Keep the image as PNG
    result = Image.fromarray(enhanced, mode="L")
    result.save(OUTPUT)

    print(f"Done: {OUTPUT}")


if __name__ == "__main__":
    main()