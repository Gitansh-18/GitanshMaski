import json
from pathlib import Path

INPUT = Path("data/contributions.json")
OUTPUT = Path("contrib-heatmap.svg")

PALETTE = [
    "#161b22",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
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
    days = days[-(COLS * ROWS):]

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
    # GRID
    # ---------------------------------------------------------

    grid_width = COLS * (CELL + GAP) - GAP
    grid_height = ROWS * (CELL + GAP) - GAP

    start_x = (WIDTH - grid_width) / 2
    start_y = 22

    # ---------------------------------------------------------
    # SNAKE PATH
    #
    # Snake moves left -> right on row 1,
    # right -> left on row 2,
    # left -> right on row 3, etc.
    # ---------------------------------------------------------

    path_x = []
    path_y = []

    for row in range(ROWS):

        columns = range(COLS)

        if row % 2 == 1:
            columns = reversed(range(COLS))

        for column in columns:

            x = start_x + column * (CELL + GAP) + CELL / 2
            y = start_y + row * (CELL + GAP) + CELL / 2

            path_x.append(f"{x:.1f}")
            path_y.append(f"{y:.1f}")

    # Key times
    key_times = [
        f"{i / (len(path_x) - 1):.5f}"
        for i in range(len(path_x))
    ]

    values_x = ";".join(path_x)
    values_y = ";".join(path_y)
    times = ";".join(key_times)

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

            .snake-body {{
                fill: #26a641;
            }}

            .snake-head {{
                fill: #39d353;
            }}

            .snake-eye {{
                fill: #0d1117;
            }}

        </style>
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

        level = max(
            0,
            min(level, len(PALETTE) - 1)
        )

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
    # SNAKE BODY
    # ---------------------------------------------------------

    body_segments = 9

    for segment in range(body_segments, 0, -1):

        opacity = 0.35 + (
            segment / body_segments
        ) * 0.5

        delay = -(segment * 0.12)

        svg.append(
            f'''
            <circle
                class="snake-body"
                r="4"
                opacity="{opacity:.2f}"
            >

                <animate
                    attributeName="cx"
                    values="{values_x}"
                    keyTimes="{times}"
                    dur="30s"
                    begin="{delay:.2f}s"
                    repeatCount="indefinite"
                    calcMode="linear"
                />

                <animate
                    attributeName="cy"
                    values="{values_y}"
                    keyTimes="{times}"
                    dur="30s"
                    begin="{delay:.2f}s"
                    repeatCount="indefinite"
                    calcMode="linear"
                />

            </circle>
            '''
        )

    # ---------------------------------------------------------
    # SNAKE HEAD
    # ---------------------------------------------------------

    svg.append(
        f'''
        <g>

            <circle
                class="snake-head"
                r="5"
            >

                <animate
                    attributeName="cx"
                    values="{values_x}"
                    keyTimes="{times}"
                    dur="30s"
                    repeatCount="indefinite"
                    calcMode="linear"
                />

                <animate
                    attributeName="cy"
                    values="{values_y}"
                    keyTimes="{times}"
                    dur="30s"
                    repeatCount="indefinite"
                    calcMode="linear"
                />

            </circle>

        </g>
        '''
    )

    # ---------------------------------------------------------
    # FOOTER
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