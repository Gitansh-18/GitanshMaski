import json
from pathlib import Path

INPUT = Path("data/contributions.json")
OUTPUT = Path("contrib-heatmap.svg")

# GitHub-style contribution colors
PALETTE = [
    "#161b22",  # 0
    "#0e4429",  # 1
    "#006d32",  # 2
    "#26a641",  # 3
    "#39d353",  # 4
]

CELL = 13
GAP = 4

COLS = 53
ROWS = 7

WIDTH = 860
HEIGHT = 155


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Could not find {INPUT}")

    data = json.loads(INPUT.read_text(encoding="utf-8"))

    days = data["days"]

    # Keep latest 371 days = 53 weeks × 7 days
    days = days[-(COLS * ROWS):]

    # Pad the beginning if necessary
    while len(days) < COLS * ROWS:
        days.insert(
            0,
            {
                "date": "",
                "count": 0,
                "level": 0,
            },
        )

    # ---------------------------------------------------------
    # GRID POSITION
    # ---------------------------------------------------------

    grid_width = COLS * (CELL + GAP) - GAP
    grid_height = ROWS * (CELL + GAP) - GAP

    start_x = (WIDTH - grid_width) / 2
    start_y = 22

    # ---------------------------------------------------------
    # BUILD SNAKE PATH
    #
    # The snake moves across each row and changes direction
    # at the end of every row.
    # ---------------------------------------------------------

    path_points = []

    xs = [
        start_x + column * (CELL + GAP) + CELL / 2
        for column in range(COLS)
    ]

    ys = [
        start_y + row * (CELL + GAP) + CELL / 2
        for row in range(ROWS)
    ]

    for row in range(ROWS):
        row_xs = xs if row % 2 == 0 else list(reversed(xs))

        for x in row_xs:
            path_points.append((x, ys[row]))

    snake_path = (
        f"M {path_points[0][0]:.1f},{path_points[0][1]:.1f} "
        + " ".join(
            f"L {x:.1f},{y:.1f}"
            for x, y in path_points[1:]
        )
    )

    svg = []

    # ---------------------------------------------------------
    # SVG HEADER
    # ---------------------------------------------------------

    svg.append(
        f'''<svg xmlns="http://www.w3.org/2000/svg"
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
                animation: reveal 0.45s ease-out forwards;
            }}

            @keyframes reveal {{
                from {{
                    opacity: 0;
                    transform: translateY(-10px);
                }}

                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}

            .text {{
                font-family: Arial, sans-serif;
                fill: #8b949e;
            }}

            .stat {{
                font-family: "Courier New", monospace;
                fill: #c9d1d9;
            }}

            /* Snake */
            .snake-body {{
                fill: #26a641;
            }}

            .snake-head {{
                fill: #39d353;
            }}

            .snake-eye {{
                fill: #0d1117;
            }}

            .snake-tongue {{
                stroke: #39d353;
                stroke-width: 1.5;
                stroke-linecap: round;
            }}
        </style>

        <!-- Invisible path used by the snake -->
        <path
            id="snakePath"
            d="{snake_path}"
            fill="none"
            stroke="none"
        />
        '''
    )

    # ---------------------------------------------------------
    # CONTRIBUTION CELLS
    # ---------------------------------------------------------

    for index, day in enumerate(days):
        column = index // ROWS
        row = index % ROWS

        x = start_x + column * (CELL + GAP)
        y = start_y + row * (CELL + GAP)

        level = int(day.get("level", 0))

        # Protect against unexpected values
        level = max(0, min(level, len(PALETTE) - 1))

        delay = (column * 0.035) + (row * 0.02)

        date = day.get("date", "")
        count = day.get("count", 0)

        title = f"{count} contributions on {date}"

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
                style="animation-delay:{delay:.3f}s"
            >
                <title>{title}</title>
            </rect>
            '''
        )

    # ---------------------------------------------------------
    # SNAKE
    # ---------------------------------------------------------

    # Body segments.
    # Each segment starts slightly later on the path,
    # creating the appearance of a moving snake.
    snake_segments = 8

    for segment in range(snake_segments, 0, -1):
        delay = -(segment * 0.22)

        svg.append(
            f'''
            <g
                class="snake-body"
                opacity="{0.45 + (segment / snake_segments) * 0.5:.2f}"
            >
                <circle
                    r="{4.0 if segment > 2 else 4.3}"
                >
                    <animateMotion
                        dur="24s"
                        begin="{delay}s"
                        repeatCount="indefinite"
                        rotate="auto"
                    >
                        <mpath href="#snakePath" />
                    </animateMotion>
                </circle>
            </g>
            '''
        )

    # Snake head
    svg.append(
        '''
        <g>
            <animateMotion
                dur="24s"
                begin="0s"
                repeatCount="indefinite"
                rotate="auto"
            >
                <mpath href="#snakePath" />
            </animateMotion>

            <!-- Head -->
            <circle
                class="snake-head"
                cx="0"
                cy="0"
                r="5"
            />

            <!-- Eyes -->
            <circle
                class="snake-eye"
                cx="-1.8"
                cy="-1.7"
                r="0.8"
            />

            <circle
                class="snake-eye"
                cx="1.8"
                cy="-1.7"
                r="0.8"
            />

            <!-- Tongue -->
            <line
                class="snake-tongue"
                x1="0"
                y1="4"
                x2="0"
                y2="7"
            />

            <line
                class="snake-tongue"
                x1="0"
                y1="7"
                x2="-1.5"
                y2="8.5"
            />

            <line
                class="snake-tongue"
                x1="0"
                y1="7"
                x2="1.5"
                y2="8.5"
            />
        </g>
        '''
    )

    # ---------------------------------------------------------
    # STATS / FOOTER
    # ---------------------------------------------------------

    total = data.get("total_contributions", 0)
    current = data.get("current_streak", 0)
    longest = data.get("longest_streak", 0)

    footer_y = start_y + grid_height + 28

    svg.append(
        f'''
        <text
            x="24"
            y="{footer_y}"
            class="stat"
            font-size="12"
        >
            {total:,} contributions
        </text>

        <text
            x="190"
            y="{footer_y}"
            class="text"
            font-size="11"
        >
            Current streak: {current} days
        </text>

        <text
            x="360"
            y="{footer_y}"
            class="text"
            font-size="11"
        >
            Longest streak: {longest} days
        </text>

        <text
            x="680"
            y="{footer_y}"
            class="text"
            font-size="10"
        >
            Less
        </text>
        '''
    )

    # ---------------------------------------------------------
    # LEGEND
    # ---------------------------------------------------------

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
            font-size="10"
        >
            More
        </text>

        </svg>
        '''
    )

    OUTPUT.write_text(
        "\n".join(svg),
        encoding="utf-8",
    )

    print(f"Done: {OUTPUT}")


if __name__ == "__main__":
    main()
