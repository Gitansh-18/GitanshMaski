import base64
import json
import random
from pathlib import Path

INPUT = Path("data/contributions.json")
SNAKE = Path("snake.png")
OUTPUT = Path("contrib-heatmap.svg")

# GitHub-style contribution colors
PALETTE = [
    "#161b22",  # 0
    "#0e4429",  # 1
    "#006d32",  # 2
    "#26a641",  # 3
    "#39d353",  # 4
]

# ---------------------------------------------------------
# HEATMAP
# ---------------------------------------------------------

CELL = 13
GAP = 4

STEP = CELL + GAP

COLS = 53
ROWS = 7

WIDTH = 860
HEIGHT = 175

GRID_WIDTH = COLS * STEP - GAP
GRID_HEIGHT = ROWS * STEP - GAP

START_X = (WIDTH - GRID_WIDTH) / 2
START_Y = 22

# ---------------------------------------------------------
# SNAKE
# ---------------------------------------------------------

# Approximately two contribution cells long.
SNAKE_WIDTH = 34
SNAKE_HEIGHT = 17

# How many random grid positions the snake visits.
# Higher = more wandering before the animation repeats.
PATH_LENGTH = 450

# Animation duration.
DURATION = 55


def load_snake():
    """Read snake.png and embed it directly into the SVG."""

    if not SNAKE.exists():
        raise FileNotFoundError(
            f"Could not find {SNAKE}. "
            f"Put snake.png in the repository root."
        )

    image_data = SNAKE.read_bytes()
    encoded = base64.b64encode(image_data).decode("ascii")

    return f"data:image/png;base64,{encoded}"


def random_walk():
    """
    Generate a completely random walk through the 53 x 7 grid.

    The snake can move:
        UP
        DOWN
        LEFT
        RIGHT

    There is no predefined route.
    """

    rng = random.SystemRandom()

    # Random starting position.
    column = rng.randrange(COLS)
    row = rng.randrange(ROWS)

    path = [(column, row)]

    directions = [
        (1, 0),    # right
        (-1, 0),   # left
        (0, 1),    # down
        (0, -1),   # up
    ]

    for _ in range(PATH_LENGTH - 1):

        possible = []

        for dx, dy in directions:

            new_column = column + dx
            new_row = row + dy

            # Stay inside the heatmap.
            if (
                0 <= new_column < COLS
                and 0 <= new_row < ROWS
            ):
                possible.append(
                    (new_column, new_row)
                )

        # Completely random valid direction.
        column, row = rng.choice(possible)

        path.append((column, row))

    return path


def grid_to_screen(column, row):
    """Convert grid coordinates to SVG coordinates."""

    x = (
        START_X
        + column * STEP
        + CELL / 2
    )

    y = (
        START_Y
        + row * STEP
        + CELL / 2
    )

    return x, y


def make_motion_path(points):
    """
    Convert random grid positions into an SVG path.

    The path follows the center of each contribution cell.
    """

    coordinates = [
        grid_to_screen(column, row)
        for column, row in points
    ]

    if not coordinates:
        return ""

    first_x, first_y = coordinates[0]

    path = [
        f"M {first_x:.1f} {first_y:.1f}"
    ]

    for x, y in coordinates[1:]:
        path.append(
            f"L {x:.1f} {y:.1f}"
        )

    return " ".join(path)


def main():

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT}"
        )

    data = json.loads(
        INPUT.read_text(encoding="utf-8")
    )

    days = data["days"]

    # Latest 371 days = 53 weeks × 7 days.
    days = days[-(COLS * ROWS):]

    # Pad if necessary.
    while len(days) < COLS * ROWS:

        days.insert(
            0,
            {
                "date": "",
                "count": 0,
                "level": 0,
            },
        )

    # -----------------------------------------------------
    # LOAD SNAKE
    # -----------------------------------------------------

    snake_data = load_snake()

    # -----------------------------------------------------
    # GENERATE RANDOM SNAKE ROUTE
    # -----------------------------------------------------

    snake_path = random_walk()

    motion_path = make_motion_path(
        snake_path
    )

    # -----------------------------------------------------
    # SVG
    # -----------------------------------------------------

    svg = []

    svg.append(
        f'''<svg
        xmlns="http://www.w3.org/2000/svg"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        width="{WIDTH}"
        height="{HEIGHT}"
        viewBox="0 0 {WIDTH} {HEIGHT}">

        <rect
            width="100%"
            height="100%"
            rx="12"
            fill="#0d1117"
        />

        <style>

            .cell {{
                opacity: 0;
                animation:
                    reveal 0.45s
                    ease-out
                    forwards;
            }}

            @keyframes reveal {{

                from {{
                    opacity: 0;
                    transform:
                        translateY(-10px);
                }}

                to {{
                    opacity: 1;
                    transform:
                        translateY(0);
                }}

            }}

            .text {{
                font-family:
                    Arial,
                    sans-serif;
                fill: #8b949e;
            }}

            .stat {{
                font-family:
                    "Courier New",
                    monospace;
                fill: #c9d1d9;
            }}

        </style>
        '''
    )

    # -----------------------------------------------------
    # CONTRIBUTION GRID
    # -----------------------------------------------------

    for index, day in enumerate(days):

        column = index // ROWS
        row = index % ROWS

        x = (
            START_X
            + column * STEP
        )

        y = (
            START_Y
            + row * STEP
        )

        level = int(
            day.get("level", 0)
        )

        level = max(
            0,
            min(
                level,
                len(PALETTE) - 1
            )
        )

        delay = (
            column * 0.035
            + row * 0.02
        )

        date = day.get(
            "date",
            ""
        )

        count = day.get(
            "count",
            0
        )

        title = (
            f"{count} contributions "
            f"on {date}"
        )

        svg.append(
            f'''
            <rect
                class="cell"
                x="{x:.1f}"
                y="{y:.1f}"
                width="{CELL}"
                height="{CELL}"
                rx="3"
                fill="{PALETTE[level]}"
                style="
                    animation-delay:
                    {delay:.3f}s
                "
            >
                <title>
                    {title}
                </title>
            </rect>
            '''
        )

    # -----------------------------------------------------
    # SNAKE
    # -----------------------------------------------------

    # Start the snake centered on the first grid cell.
    first_x, first_y = grid_to_screen(
        *snake_path[0]
    )

    snake_x = (
        first_x
        - SNAKE_WIDTH / 2
    )

    snake_y = (
        first_y
        - SNAKE_HEIGHT / 2
    )

    svg.append(
        f'''
        <image
            x="{snake_x:.1f}"
            y="{snake_y:.1f}"
            width="{SNAKE_WIDTH}"
            height="{SNAKE_HEIGHT}"
            preserveAspectRatio="xMidYMid meet"
            href="{snake_data}"
            xlink:href="{snake_data}">

            <animateMotion
                dur="{DURATION}s"
                begin="0s"
                repeatCount="indefinite"
                rotate="auto"
                path="{motion_path}"
            />

        </image>
        '''
    )

    # -----------------------------------------------------
    # FOOTER
    # -----------------------------------------------------

    total = data.get(
        "total_contributions",
        0
    )

    current = data.get(
        "current_streak",
        0
    )

    longest = data.get(
        "longest_streak",
        0
    )

    footer_y = (
        START_Y
        + GRID_HEIGHT
        + 28
    )

    svg.append(
        f'''
        <text
            x="24"
            y="{footer_y}"
            class="stat"
            font-size="12">
            {total:,} contributions
        </text>

        <text
            x="190"
            y="{footer_y}"
            class="text"
            font-size="11">
            Current streak:
            {current} days
        </text>

        <text
            x="360"
            y="{footer_y}"
            class="text"
            font-size="11">
            Longest streak:
            {longest} days
        </text>

        <text
            x="680"
            y="{footer_y}"
            class="text"
            font-size="10">
            Less
        </text>
        '''
    )

    # -----------------------------------------------------
    # LEGEND
    # -----------------------------------------------------

    legend_x = 712

    for i, color in enumerate(PALETTE):

        svg.append(
            f'''
            <rect
                x="{legend_x + i * 16}"
                y="{footer_y - 10}"
                width="11"
                height="11"
                rx="2"
                fill="{color}"
            />
            '''
        )

    svg.append(
        f'''
        <text
            x="{legend_x + 86}"
            y="{footer_y}"
            class="text"
            font-size="10">
            More
        </text>

        </svg>
        '''
    )

    # -----------------------------------------------------
    # WRITE SVG
    # -----------------------------------------------------

    OUTPUT.write_text(
        "\n".join(svg),
        encoding="utf-8",
    )

    print(
        f"Done: {OUTPUT}"
    )

    print(
        f"Snake route: {PATH_LENGTH} random positions"
    )


if __name__ == "__main__":
    main()