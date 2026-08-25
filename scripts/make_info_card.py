from pathlib import Path

OUTPUT = Path("info-card.svg")

WIDTH = 490
HEIGHT = 330

BG = "#0d1117"
BORDER = "#30363d"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
ACCENT = "#58a6ff"
GREEN = "#39d353"


LINES = [
    ("Role", "B.Tech IT Student"),
    ("Stack", "React · Next.js · TypeScript"),
    ("", "Python · C++ · Node.js"),
    ("AI", "LLMs · RAG · LangChain"),
    ("", "Gemini · Groq · ChromaDB"),
    ("Projects", "SkillPilot"),
    ("", "SmartDoc · AeroHand"),
    ("Education", "B.Tech IT · 2023–2027"),
    ("", "G.L. Bajaj"),
]


def escape(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def main():
    svg = []

    svg.append(
        f'''<svg xmlns="http://www.w3.org/2000/svg"
        width="{WIDTH}"
        height="{HEIGHT}"
        viewBox="0 0 {WIDTH} {HEIGHT}">

        <rect
            x="1"
            y="1"
            width="{WIDTH - 2}"
            height="{HEIGHT - 2}"
            rx="12"
            fill="{BG}"
            stroke="{BORDER}"
        />

        <style>
            .title {{
                font-family: "Courier New", monospace;
                font-size: 16px;
                font-weight: bold;
                fill: {TEXT};
            }}

            .label {{
                font-family: "Courier New", monospace;
                font-size: 13px;
                font-weight: bold;
                fill: {ACCENT};
            }}

            .value {{
                font-family: "Courier New", monospace;
                font-size: 13px;
                fill: {TEXT};
            }}

            .muted {{
                font-family: "Courier New", monospace;
                font-size: 12px;
                fill: {MUTED};
            }}

            .line {{
                opacity: 0;
                animation: show 0.35s ease-out forwards;
            }}

            @keyframes show {{
                from {{
                    opacity: 0;
                    transform: translateX(-12px);
                }}

                to {{
                    opacity: 1;
                    transform: translateX(0);
                }}
            }}
        </style>

        <text x="24" y="32" class="title">
            gitansh@github ~ $ whoami
        </text>

        <line
            x1="24"
            y1="47"
            x2="466"
            y2="47"
            stroke="{BORDER}"
        />
        '''
    )

    y = 76

    for index, (label, value) in enumerate(LINES):
        delay = 0.25 + index * 0.12

        if label:
            svg.append(
                f'''
                <g class="line" style="animation-delay:{delay:.2f}s">
                    <text x="24" y="{y}" class="label">
                        {escape(label)}
                    </text>

                    <text x="125" y="{y}" class="value">
                        {escape(value)}
                    </text>
                </g>
                '''
            )
        else:
            svg.append(
                f'''
                <text
                    x="125"
                    y="{y}"
                    class="value line"
                    style="animation-delay:{delay:.2f}s"
                >
                    {escape(value)}
                </text>
                '''
            )

        y += 27

    svg.append(
        f'''
        <text x="24" y="{HEIGHT - 18}" class="muted">
            gitansh@github:~$
        </text>

        </svg>
        '''
    )

    OUTPUT.write_text("\n".join(svg), encoding="utf-8")

    print(f"Done: {OUTPUT}")


if __name__ == "__main__":
    main()