import base64
import json
import random
from pathlib import Path

INPUT = Path("data/contributions.json")
SNAKE = Path("snake.png")
OUTPUT = Path("contrib-heatmap.svg")

# GitHub contribution colors
PALETTE = [
    "#161b22",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
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

# Around 2 contribution cells wide.
SNAKE_WIDTH = 30
SNAKE_HEIGHT = 15

# Number of random grid moves in one animation.
MOVES = 500

# Total animation duration.
DURATION = 60


def load_snake():

    if not SNAKE.exists():
        raise FileNotFoundError(
            "snake.png not found. "
            "Put snake.png in the GitanshMaski root folder."
        )

    encoded = base64.b64encode(
        SNAKE.read_bytes()
    ).decode("ascii")

    return f"data:image/png;base64,{encoded}"


def grid_position(column, row):
    """
    Return the CENTER of a contribution cell.
    """

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


def random_snake_walk():
    """
    Completely random movement.

    The snake can move:

        UP
        DOWN
        LEFT
        RIGHT

    It never leaves the heatmap.
    """

    rng = random.SystemRandom()

    column = rng.randrange(COLS)
    row = rng.randrange(ROWS)

    points = [(column, row)]

    previous_direction = None

    directions = [
        ("right", 1, 0),
        ("left", -1, 0),
        ("down", 0, 1),
        ("up", 0, -1),
    ]

    for _ in range(MOVES - 1):

        valid = []

        for name, dx, dy in directions:

            new_column = column + dx
            new_row = row + dy

            if (
                0 <= new_column < COLS
                and 0 <= new_row < ROWS
            ):
                valid.append(
                    (name, dx, dy)
                )

        # Prefer changing direction sometimes.
        # This prevents extremely long straight lines.
        if previous_direction and len(valid) > 1:

            changed = [
                direction
                for direction in valid
                if direction[0] != previous_direction
            ]

            # 65% chance of changing direction.
            if rng.random() < 0.65:
                valid = changed

        direction = rng.choice(valid)

        name, dx, dy = direction

        column += dx
        row += dy

        previous_direction = name

        points.append(
            (column, row)
        )

    return points


def create_motion_path(points):

    coordinates = [
        grid_position(column, row)
        for column, row in points
    ]

    first_x, first_y = coordinates[0]

    commands = [
        f"M {first_x:.1f} {first_y:.1f}"
    ]

    for x, y in coordinates[1:]:
        commands.append(
            f"L {x:.1f} {y:.1f}"
        )

    return " ".join(commands)


def main():

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT}"
        )

    data = json.loads(
        INPUT.read_text(
            encoding="utf-8"
        )
    )

    days = data["days"]

    # 53 weeks × 7 days
    days = days[-(COLS * ROWS):]

    while len(days) < COLS * ROWS:

        days.insert(
            0,
            {
                "date": "",
                "count": 0,
                "level": 0,
            }
        )

    # -----------------------------------------------------
    # SNAKE DATA
    # -----------------------------------------------------

    snake_image = load_snake()

    snake_points = random_snake_walk()

    motion_path = create_motion_path(
        snake_points
    )

    first_x, first_y = grid_position(
        *snake_points[0]
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
    # CONTRIBUTION CELLS
    # -----------------------------------------------------

    for index, day in enumerate(days):

        column = index // ROWS
        row = index % ROWS

        x = START_X + column * STEP
        y = START_Y + row * STEP

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
style="animation-delay:{delay:.3f}s">

<title>{title}</title>

</rect>
'''
        )

    # -----------------------------------------------------
    # SNAKE
    # -----------------------------------------------------

    # IMPORTANT:
    # The image is positioned by its CENTER.
    #
    # This prevents the snake from being pushed
    # outside the heatmap when it reaches an edge.

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
<!-- RANDOM ROAMING SNAKE -->

<image
x="{snake_x:.1f}"
y="{snake_y:.1f}"
width="{SNAKE_WIDTH}"
height="{SNAKE_HEIGHT}"
href="{snake_image}"
xlink:href="{snake_image}"
preserveAspectRatio="none">

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

Current streak: {current} days

</text>

<text
x="360"
y="{footer_y}"
class="text"
font-size="11">

Longest streak: {longest} days

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
    # WRITE
    # -----------------------------------------------------

    OUTPUT.write_text(
        "\n".join(svg),
        encoding="utf-8"
    )

    print(
        f"Done: {OUTPUT}"
    )

    print(
        f"Random snake moves: {MOVES}"
    )


if __name__ == "__main__":
    main()