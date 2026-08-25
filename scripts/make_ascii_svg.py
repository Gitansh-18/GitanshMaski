from pathlib import Path
from PIL import Image


INPUT = Path("source-prepped.png")
OUTPUT = Path("gitansh-ascii.svg")

# Bright -> dark
RAMP = " .`:-=+*cs#%@"

# ASCII dimensions
COLS = 100
ROWS = 53

# Character dimensions
CHAR_W = 7
CHAR_H = 12

TEXT_COLOR = "#b8c0c8"


def brightness_to_char(value):
    # White = sparse character
    # Black = dense character
    index = int((255 - value) / 255 * (len(RAMP) - 1))
    return RAMP[index]


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Could not find {INPUT}")

    print("Loading preprocessed image...")

    image = Image.open(INPUT).convert("L")

    # Resize while preserving the intended ASCII proportions.
    image = image.resize((COLS, ROWS))

    width = COLS * CHAR_W
    height = ROWS * CHAR_H

    print("Converting image to ASCII...")

    rows = []

    for y in range(ROWS):
        chars = []

        for x in range(COLS):
            brightness = image.getpixel((x, y))
            chars.append(brightness_to_char(brightness))

        rows.append("".join(chars))

    print("Building animated SVG...")

    svg = []

    svg.append(
        f'''<svg xmlns="http://www.w3.org/2000/svg"
        width="{width}"
        height="{height}"
        viewBox="0 0 {width} {height}">

        <rect width="100%" height="100%" fill="white"/>

        <style>
            .ascii {{
                font-family: "Courier New", monospace;
                font-size: {CHAR_H}px;
                fill: {TEXT_COLOR};
                white-space: pre;
            }}

            .row {{
                opacity: 0;
                animation: reveal 0.08s ease-out forwards;
            }}

            @keyframes reveal {{
                from {{
                    opacity: 0;
                    transform: translateX(-20px);
                }}

                to {{
                    opacity: 1;
                    transform: translateX(0);
                }}
            }}
        </style>
        '''
    )

    for y, row in enumerate(rows):
        delay = y * 0.045

        svg.append(
            f'''
            <text
                x="0"
                y="{(y + 1) * CHAR_H}"
                class="ascii row"
                style="animation-delay:{delay:.3f}s"
            >{row}</text>
            '''
        )

    svg.append("</svg>")

    OUTPUT.write_text("\n".join(svg), encoding="utf-8")

    print(f"Done: {OUTPUT}")


if __name__ == "__main__":
    main()