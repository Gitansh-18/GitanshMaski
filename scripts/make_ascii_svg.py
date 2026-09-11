from pathlib import Path
import base64
import io

import cv2
import numpy as np
from PIL import Image


INPUT = Path("source-prepped.png")
OUTPUT = Path("gitansh-ascii.svg")

WIDTH = 420
HEIGHT = 428


def make_cartoon(image):
    """Convert the prepared image into a clean cartoon-style image."""

    image_np = np.array(image.convert("RGB"))

    # PIL RGB -> OpenCV BGR
    img = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

    # Smooth the image while preserving important edges
    smooth = img.copy()

    for _ in range(2):
        smooth = cv2.bilateralFilter(
            smooth,
            d=9,
            sigmaColor=75,
            sigmaSpace=75
        )

    # Reduce the number of colors
    data = smooth.reshape((-1, 3)).astype(np.float32)

    K = 10

    criteria = (
        cv2.TERM_CRITERIA_EPS
        + cv2.TERM_CRITERIA_MAX_ITER,
        30,
        1.0
    )

    _, labels, centers = cv2.kmeans(
        data,
        K,
        None,
        criteria,
        5,
        cv2.KMEANS_PP_CENTERS
    )

    centers = np.uint8(centers)

    cartoon = centers[labels.flatten()]
    cartoon = cartoon.reshape(smooth.shape)

    # Detect facial/clothing outlines
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)

    edges = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        9,
        4
    )

    # Combine simplified colors with outlines
    cartoon = cv2.bitwise_and(
        cartoon,
        cartoon,
        mask=edges
    )

    # Slightly boost color
    hsv = cv2.cvtColor(
        cartoon,
        cv2.COLOR_BGR2HSV
    )

    hsv[:, :, 1] = np.clip(
        hsv[:, :, 1].astype(np.float32) * 1.15,
        0,
        255
    ).astype(np.uint8)

    cartoon = cv2.cvtColor(
        hsv,
        cv2.COLOR_HSV2BGR
    )

    return Image.fromarray(
        cv2.cvtColor(
            cartoon,
            cv2.COLOR_BGR2RGB
        )
    )


def image_to_base64(image):

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
        optimize=True
    )

    return base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")


def main():

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT}"
        )

    print("Loading preprocessed image...")

    image = Image.open(INPUT).convert("RGB")

    # Resize to match your existing profile image size
    image = image.resize(
        (WIDTH, HEIGHT),
        Image.Resampling.LANCZOS
    )

    print("Creating cartoon effect...")

    cartoon = make_cartoon(image)

    print("Embedding cartoon into SVG...")

    image_data = image_to_base64(cartoon)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
width="{WIDTH}"
height="{HEIGHT}"
viewBox="0 0 {WIDTH} {HEIGHT}">

<rect
width="100%"
height="100%"
fill="white"
/>

<image
href="data:image/png;base64,{image_data}"
x="0"
y="0"
width="{WIDTH}"
height="{HEIGHT}"
preserveAspectRatio="xMidYMid meet"
/>

</svg>
'''

    OUTPUT.write_text(
        svg,
        encoding="utf-8"
    )

    print(f"Done: {OUTPUT}")


if __name__ == "__main__":
    main()
