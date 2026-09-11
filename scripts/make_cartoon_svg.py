from pathlib import Path
import base64
import io

import cv2
import numpy as np
from PIL import Image
from rembg import remove


INPUT = Path("source-photo.jpg")
OUTPUT = Path("gitansh-cartoon.svg")

WIDTH = 420
HEIGHT = 428

ROWS = 28


def make_cartoon(image):
    """
    Creates a clean digital-cartoon effect:
    - smooths skin/clothing
    - preserves facial features
    - reduces colors
    - adds soft outlines
    """

    image_np = np.array(image.convert("RGB"))

    # OpenCV uses BGR
    img = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

    # Smooth colors while preserving edges
    smooth = img.copy()

    for _ in range(2):
        smooth = cv2.bilateralFilter(
            smooth,
            d=9,
            sigmaColor=75,
            sigmaSpace=75
        )

    # Reduce color complexity for cartoon appearance
    data = smooth.reshape((-1, 3)).astype(np.float32)

    K = 12

    criteria = (
        cv2.TERM_CRITERIA_EPS +
        cv2.TERM_CRITERIA_MAX_ITER,
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

    quantized = centers[labels.flatten()]
    quantized = quantized.reshape(smooth.shape)

    # Detect edges
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gray = cv2.medianBlur(gray, 5)

    edges = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        9,
        5
    )

    # Slightly soften edge result
    edges = cv2.GaussianBlur(edges, (3, 3), 0)

    # Combine cartoon colors and outlines
    cartoon = cv2.bitwise_and(
        quantized,
        quantized,
        mask=edges
    )

    # Improve saturation slightly
    hsv = cv2.cvtColor(cartoon, cv2.COLOR_BGR2HSV)

    hsv[:, :, 1] = np.clip(
        hsv[:, :, 1].astype(np.float32) * 1.12,
        0,
        255
    ).astype(np.uint8)

    cartoon = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    return Image.fromarray(
        cv2.cvtColor(cartoon, cv2.COLOR_BGR2RGB)
    )


def prepare_subject():
    print("Loading profile photo...")

    original = Image.open(INPUT).convert("RGBA")

    print("Removing background...")

    foreground = remove(original).convert("RGBA")

    # Transparent output first
    bbox = foreground.getbbox()

    if bbox:
        foreground = foreground.crop(bbox)

    # Add padding around the subject
    padding_x = int(foreground.width * 0.12)
    padding_y = int(foreground.height * 0.08)

    canvas = Image.new(
        "RGBA",
        (
            foreground.width + padding_x * 2,
            foreground.height + padding_y * 2
        ),
        (0, 0, 0, 0)
    )

    canvas.alpha_composite(
        foreground,
        (padding_x, padding_y)
    )

    # Resize to final dimensions
    canvas.thumbnail(
        (WIDTH, HEIGHT),
        Image.Resampling.LANCZOS
    )

    # Center on transparent canvas
    result = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0)
    )

    x = (WIDTH - canvas.width) // 2
    y = HEIGHT - canvas.height

    result.alpha_composite(canvas, (x, y))

    return result


def image_to_base64(image):
    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
        optimize=True
    )

    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    return encoded


def main():

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT}"
        )

    subject = prepare_subject()

    # Cartoonize only the visible subject
    white_bg = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (255, 255, 255, 255)
    )

    white_bg.alpha_composite(subject)

    print("Creating cartoon effect...")

    cartoon_rgb = make_cartoon(
        white_bg.convert("RGB")
    )

    cartoon_rgba = cartoon_rgb.convert("RGBA")

    # Restore original transparency
    cartoon_rgba.putalpha(
        subject.getchannel("A")
    )

    image_data = image_to_base64(cartoon_rgba)

    print("Building animated SVG...")

    row_height = HEIGHT / ROWS

    svg = []

    svg.append(
        f'''<svg
xmlns="http://www.w3.org/2000/svg"
xmlns:xlink="http://www.w3.org/1999/xlink"
width="{WIDTH}"
height="{HEIGHT}"
viewBox="0 0 {WIDTH} {HEIGHT}"
>
<style>

.background {{
    fill: #0d1117;
}}

.row {{
    opacity: 0;
    animation: reveal 0.45s ease-out forwards;
}}

@keyframes reveal {{

    from {{
        opacity: 0;
        transform: translateY(12px);
    }}

    to {{
        opacity: 1;
        transform: translateY(0);
    }}

}}

</style>

<rect
class="background"
width="100%"
height="100%"
rx="16"
/>

'''
    )

    # Create animated strips
    for row in range(ROWS):

        y = row * row_height
        delay = row * 0.055

        svg.append(
            f'''
<clipPath id="clip{row}">
    <rect
        x="0"
        y="{y}"
        width="{WIDTH}"
        height="{row_height + 1}"
    />
</clipPath>

<g
class="row"
style="animation-delay:{delay:.3f}s"
clip-path="url(#clip{row})"
>
    <image
        x="0"
        y="0"
        width="{WIDTH}"
        height="{HEIGHT}"
        href="data:image/png;base64,{image_data}"
    />
</g>
'''
        )

    svg.append("</svg>")

    OUTPUT.write_text(
        "\n".join(svg),
        encoding="utf-8"
    )

    print(f"Done: {OUTPUT}")


if __name__ == "__main__":
    main()
