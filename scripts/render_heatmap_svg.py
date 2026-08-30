from __future__ import annotations
 
import base64
import datetime
import json
import math
import os
import random
import struct
import sys
from typing import Optional
 
# ----------------------------------------------------------------------
# Paths (script lives in scripts/, repo root is its parent)
# ----------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
 
CONTRIBUTIONS_JSON = os.path.join(REPO_ROOT, "data", "contributions.json")
SNAKE_PNG = os.path.join(REPO_ROOT, "snake.png")
OUTPUT_SVG = os.path.join(REPO_ROOT, "contrib-heatmap.svg")
 
# ----------------------------------------------------------------------
# Grid geometry (exactly as specified)
# ----------------------------------------------------------------------
COLUMNS = 53
ROWS = 7
CELL = 13
GAP = 4
STEP = CELL + GAP  # 17, center-to-center
 
GRID_W = (COLUMNS - 1) * STEP + CELL  # pixel width of the cell grid
GRID_H = (ROWS - 1) * STEP + CELL     # pixel height of the cell grid
 
# ----------------------------------------------------------------------
# Layout / theme
# ----------------------------------------------------------------------
PAD = 20
HEADER_H = 34
STATS_H = 20
LEGEND_H = 24
ROW_GAP = 8
 
GRID_X = PAD
GRID_Y = PAD + HEADER_H + ROW_GAP
 
SVG_W = GRID_W + PAD * 2
SVG_H = GRID_Y + GRID_H + ROW_GAP + STATS_H + ROW_GAP + LEGEND_H + PAD
 
BG_COLOR = "#0d1117"
TEXT_COLOR = "#c9d1d9"
MUTED_TEXT_COLOR = "#8b949e"
LEVEL_COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
 
# ----------------------------------------------------------------------
# Snake behaviour tuning
# ----------------------------------------------------------------------
TARGET_SNAKE_LEN_CELLS = 1.75      # 1.5-2 cells long, per spec
TOTAL_STEPS = 420                  # "hundreds of movement steps"
MIN_STEP_SECONDS = 0.28
MAX_STEP_SECONDS = 0.55
BURROW_PROBABILITY_NEAR_EDGE = 0.12
BURROW_FADE_SECONDS = 0.35
BURROW_MIN_GAP_STEPS = 18          # don't burrow again too soon
 
STRAIGHT_WEIGHT = 6.0
TURN_WEIGHT = 2.5
REVERSE_WEIGHT = 0.6
 
DIRS = {
    "RIGHT": (1, 0),
    "LEFT": (-1, 0),
    "DOWN": (0, 1),
    "UP": (0, -1),
}
OPPOSITE = {"RIGHT": "LEFT", "LEFT": "RIGHT", "DOWN": "UP", "UP": "DOWN"}
ALL_DIRECTIONS = ["RIGHT", "LEFT", "DOWN", "UP"]
 
 
# ========================================================================
# Contribution data loading / normalizing
# ========================================================================
 
class ContribDay:
    __slots__ = ("date", "count", "level")
 
    def __init__(self, date: datetime.date, count: int, level: int):
        self.date = date
        self.count = count
        self.level = level
 
 
def _infer_level(count: int, max_count: int) -> int:
    if count <= 0:
        return 0
    if max_count <= 0:
        return 1
    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    if ratio <= 0.5:
        return 2
    if ratio <= 0.75:
        return 3
    return 4
 
 
def _coerce_day(entry: dict) -> Optional[ContribDay]:
    date_raw = entry.get("date") or entry.get("day") or entry.get("d")
    if not date_raw:
        return None
    try:
        date_val = datetime.date.fromisoformat(str(date_raw)[:10])
    except ValueError:
        return None
    count = entry.get("count")
    if count is None:
        count = entry.get("contributionCount", entry.get("value", 0))
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 0
    level = entry.get("level")
    if level is None:
        level = entry.get("contributionLevel")
    try:
        level = int(level) if level is not None else None
    except (TypeError, ValueError):
        level = None
    return ContribDay(date_val, count, level if level is not None else -1)
 
 
def load_contributions(path: str) -> dict:
    """
    Accepts several common shapes produced by contribution-fetching
    scripts, without needing to touch fetch_contributions.py:
 
      A) {"weeks": [{"days": [{"date","count","level"}, ...]}, ...]}
      B) {"contributions": [{"date","count","level"}, ...]}   (flat)
      C) [{"date","count","level"}, ...]                      (flat, bare list)
 
    Optional top-level stats, used if present, else computed:
      "totalContributions", "currentStreak", "longestStreak"
    """
    if not os.path.exists(path):
        print(f"ERROR: contribution data not found at: {path}", file=sys.stderr)
        print(
            "Expected data/contributions.json produced by "
            "scripts/fetch_contributions.py (flat list of "
            "{date,count,level} or {weeks:[{days:[...]}]}).",
            file=sys.stderr,
        )
        sys.exit(1)
 
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
 
    days: list[ContribDay] = []
    top_stats = {}
 
    if isinstance(raw, list):
        for entry in raw:
            d = _coerce_day(entry)
            if d:
                days.append(d)
    elif isinstance(raw, dict):
        top_stats = {
            k: raw.get(k)
            for k in ("totalContributions", "currentStreak", "longestStreak")
            if k in raw
        }
        if isinstance(raw.get("weeks"), list):
            for week in raw["weeks"]:
                for entry in week.get("days", []):
                    d = _coerce_day(entry)
                    if d:
                        days.append(d)
        elif isinstance(raw.get("contributions"), list):
            for entry in raw["contributions"]:
                d = _coerce_day(entry)
                if d:
                    days.append(d)
        elif isinstance(raw.get("days"), list):
            for entry in raw["days"]:
                d = _coerce_day(entry)
                if d:
                    days.append(d)
 
    if not days:
        print(
            "ERROR: could not find any recognizable day entries inside "
            f"{path}. Adjust load_contributions() to match your actual "
            "contributions.json schema (only this function needs to "
            "change).",
            file=sys.stderr,
        )
        sys.exit(1)
 
    days.sort(key=lambda d: d.date)
 
    max_count = max((d.count for d in days), default=0)
    for d in days:
        if d.level < 0:
            d.level = _infer_level(d.count, max_count)
        d.level = max(0, min(4, d.level))
 
    total = top_stats.get("totalContributions")
    if total is None:
        total = sum(d.count for d in days)
 
    current_streak = top_stats.get("currentStreak")
    longest_streak = top_stats.get("longestStreak")
    if current_streak is None or longest_streak is None:
        longest = 0
        run = 0
        for d in days:
            if d.count > 0:
                run += 1
                longest = max(longest, run)
            else:
                run = 0
        cur = 0
        for d in reversed(days):
            if d.count > 0:
                cur += 1
            else:
                break
        current_streak = cur if current_streak is None else current_streak
        longest_streak = longest if longest_streak is None else longest_streak
 
    return {
        "days": days,
        "total": int(total),
        "current_streak": int(current_streak),
        "longest_streak": int(longest_streak),
    }
 
 
def days_to_grid(days: list[ContribDay]) -> list[list[Optional[ContribDay]]]:
    """
    Lay the (already date-sorted) days out into a COLUMNS x ROWS grid,
    GitHub-style: columns are weeks, rows are weekdays (Sun=0..Sat=6),
    right-aligned so the most recent day lands in the last column.
    """
    grid: list[list[Optional[ContribDay]]] = [
        [None] * ROWS for _ in range(COLUMNS)
    ]
    if not days:
        return grid
 
    last_date = days[-1].date
    last_col = COLUMNS - 1
    last_row = (last_date.isoweekday() % 7)  # Sun=0 .. Sat=6
 
    by_date = {d.date: d for d in days}
    col, row = last_col, last_row
    cur_date = last_date
    filled = 0
    total_cells = COLUMNS * ROWS
    while filled < total_cells and col >= 0:
        if 0 <= col < COLUMNS and 0 <= row < ROWS:
            grid[col][row] = by_date.get(cur_date)
            filled += 1
        row -= 1
        if row < 0:
            row = ROWS - 1
            col -= 1
        cur_date = cur_date - datetime.timedelta(days=1)
    return grid
 
 
# ========================================================================
# PNG helpers (no Pillow dependency: PNG dims read via the header chunk)
# ========================================================================
 
def read_png_size(path: str) -> tuple[int, int]:
    with open(path, "rb") as f:
        header = f.read(33)
    if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"{path} does not look like a valid PNG file")
    width, height = struct.unpack(">II", header[16:24])
    return width, height
 
 
def encode_png_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")
 
 
# ========================================================================
# Randomized grid-walk movement
# ========================================================================
 
class WalkStep:
    __slots__ = ("col", "row", "direction", "duration", "burrow_in")
 
    def __init__(self, col, row, direction, duration, burrow_in=False):
        self.col = col
        self.row = row
        self.direction = direction
        self.duration = duration
        # True if the transition arriving at this step is a "burrow"
        # (fade out at old spot, jump, fade in here) rather than a
        # normal smooth crawl.
        self.burrow_in = burrow_in
 
 
def orientation_margins(direction: str, half_w: float, half_h: float) -> tuple[int, int]:
    """
    Margin, in whole grid cells, that must be kept free on every side for
    the snake's actual pixel footprint (not just its center) to stay
    fully inside the grid, for the bounding box produced by `direction`.
    LEFT/RIGHT keep the sprite's natural (wide, short) footprint;
    UP/DOWN rotate the sprite 90 degrees so the footprint is (tall, thin)
    -- width/height are swapped.
    """
    if direction in ("LEFT", "RIGHT"):
        bw, bh = half_w, half_h
    else:
        bw, bh = half_h, half_w
    margin_col = max(0, math.ceil((bw - CELL / 2) / STEP))
    margin_row = max(0, math.ceil((bh - CELL / 2) / STEP))
    return margin_col, margin_row
 
 
def cell_is_valid(col: int, row: int, direction: str, half_w: float, half_h: float) -> bool:
    mc, mr = orientation_margins(direction, half_w, half_h)
    return mc <= col <= (COLUMNS - 1 - mc) and mr <= row <= (ROWS - 1 - mr)
 
 
def near_edge(col: int, row: int, half_w: float, half_h: float) -> bool:
    for direction in ALL_DIRECTIONS:
        mc, mr = orientation_margins(direction, half_w, half_h)
        if col <= mc + 1 or col >= (COLUMNS - 1 - mc - 1):
            return True
        if row <= mr + 1 or row >= (ROWS - 1 - mr - 1):
            return True
    return False
 
 
def pick_random_valid_cell(direction: str, half_w: float, half_h: float, rng: random.Random) -> tuple[int, int]:
    mc, mr = orientation_margins(direction, half_w, half_h)
    col = rng.randint(mc, COLUMNS - 1 - mc)
    row = rng.randint(mr, ROWS - 1 - mr)
    return col, row
 
 
def choose_next_direction(current_dir: str, col: int, row: int, half_w: float,
                           half_h: float, rng: random.Random) -> Optional[str]:
    weighted: list[tuple[str, float]] = []
    for d in ALL_DIRECTIONS:
        dc, dr = DIRS[d]
        nc, nr = col + dc, row + dr
        if not cell_is_valid(nc, nr, d, half_w, half_h):
            continue
        if d == current_dir:
            w = STRAIGHT_WEIGHT
        elif d == OPPOSITE[current_dir]:
            w = REVERSE_WEIGHT
        else:
            w = TURN_WEIGHT
        weighted.append((d, w))
 
    if not weighted:
        return None
 
    total = sum(w for _, w in weighted)
    r = rng.uniform(0, total)
    upto = 0.0
    for d, w in weighted:
        upto += w
        if r <= upto:
            return d
    return weighted[-1][0]
 
 
def generate_walk(rng: random.Random, half_w: float, half_h: float) -> list[WalkStep]:
    direction = rng.choice(ALL_DIRECTIONS)
    col, row = pick_random_valid_cell(direction, half_w, half_h, rng)
 
    steps: list[WalkStep] = [
        WalkStep(col, row, direction, rng.uniform(MIN_STEP_SECONDS, MAX_STEP_SECONDS))
    ]
    start_col, start_row, start_dir = col, row, direction
 
    steps_since_burrow = BURROW_MIN_GAP_STEPS  # allow an early burrow if needed
 
    while len(steps) < TOTAL_STEPS:
        steps_since_burrow += 1
        do_burrow = (
            steps_since_burrow >= BURROW_MIN_GAP_STEPS
            and near_edge(col, row, half_w, half_h)
            and rng.random() < BURROW_PROBABILITY_NEAR_EDGE
        )
 
        if do_burrow:
            new_direction = rng.choice(ALL_DIRECTIONS)
            col, row = pick_random_valid_cell(new_direction, half_w, half_h, rng)
            direction = new_direction
            steps.append(
                WalkStep(col, row, direction, BURROW_FADE_SECONDS, burrow_in=True)
            )
            steps_since_burrow = 0
            continue
 
        next_dir = choose_next_direction(direction, col, row, half_w, half_h, rng)
        if next_dir is None:
            # Boxed in (shouldn't really happen on a 53x7 grid) -- burrow out.
            next_dir = rng.choice(ALL_DIRECTIONS)
            col, row = pick_random_valid_cell(next_dir, half_w, half_h, rng)
            direction = next_dir
            steps.append(
                WalkStep(col, row, direction, BURROW_FADE_SECONDS, burrow_in=True)
            )
            steps_since_burrow = 0
            continue
 
        dc, dr = DIRS[next_dir]
        col, row = col + dc, row + dr
        direction = next_dir
        steps.append(
            WalkStep(col, row, direction, rng.uniform(MIN_STEP_SECONDS, MAX_STEP_SECONDS))
        )
 
    # Close the loop invisibly: burrow back toward the starting cell so
    # repeatCount="indefinite" doesn't produce a visible slide/jump.
    steps.append(WalkStep(start_col, start_row, start_dir, BURROW_FADE_SECONDS, burrow_in=True))
 
    return steps
 
 
# ========================================================================
# SVG assembly
# ========================================================================
 
def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
 
 
def cell_x(col: int) -> float:
    return GRID_X + col * STEP
 
 
def cell_y(row: int) -> float:
    return GRID_Y + row * STEP
 
 
def build_grid_svg(grid: list[list[Optional[ContribDay]]]) -> str:
    parts = ['<g id="contribution-cells">']
    for col in range(COLUMNS):
        for row in range(ROWS):
            day = grid[col][row]
            x = cell_x(col)
            y = cell_y(row)
            if day is None:
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" '
                    f'rx="2" ry="2" fill="{LEVEL_COLORS[0]}" />'
                )
                continue
            color = LEVEL_COLORS[day.level]
            tooltip = f"{day.count} contribution{'s' if day.count != 1 else ''} on {day.date.isoformat()}"
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" '
                f'rx="2" ry="2" fill="{color}"><title>{esc(tooltip)}</title></rect>'
            )
    parts.append("</g>")
    return "".join(parts)
 
 
def build_stats_and_legend_svg(stats: dict) -> str:
    stats_y = GRID_Y + GRID_H + ROW_GAP + (STATS_H * 0.75)
    stats_text = (
        f"{stats['total']} contributions in the last year &#183; "
        f"current streak {stats['current_streak']} day"
        f"{'s' if stats['current_streak'] != 1 else ''} &#183; "
        f"longest streak {stats['longest_streak']} day"
        f"{'s' if stats['longest_streak'] != 1 else ''}"
    )
 
    legend_y = GRID_Y + GRID_H + ROW_GAP + STATS_H + ROW_GAP
    legend_sq = 10
    legend_gap = 3
    less_label_w = 30
    legend_x = SVG_W - PAD - less_label_w - len(LEVEL_COLORS) * (legend_sq + legend_gap) - 34
 
    parts = [
        f'<text x="{GRID_X}" y="{stats_y:.1f}" fill="{MUTED_TEXT_COLOR}" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" '
        f'font-size="12">{stats_text}</text>',
        f'<g id="legend">',
        f'<text x="{legend_x:.1f}" y="{legend_y + legend_sq:.1f}" fill="{MUTED_TEXT_COLOR}" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" '
        f'font-size="11">Less</text>',
    ]
    swatch_x = legend_x + 30
    for color in LEVEL_COLORS:
        parts.append(
            f'<rect x="{swatch_x:.1f}" y="{legend_y:.1f}" width="{legend_sq}" height="{legend_sq}" '
            f'rx="2" ry="2" fill="{color}" />'
        )
        swatch_x += legend_sq + legend_gap
    parts.append(
        f'<text x="{swatch_x + 2:.1f}" y="{legend_y + legend_sq:.1f}" fill="{MUTED_TEXT_COLOR}" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" '
        f'font-size="11">More</text>'
    )
    parts.append("</g>")
    return "".join(parts)
 
 
def build_header_svg() -> str:
    y = PAD + HEADER_H * 0.7
    return (
        f'<text x="{GRID_X}" y="{y:.1f}" fill="{TEXT_COLOR}" '
        f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" '
        f'font-size="16" font-weight="600">Contribution Activity</text>'
    )
 
 
def build_snake_svg(steps: list[WalkStep], png_b64: str, img_w: int, img_h: int,
                     scaled_w: float, scaled_h: float) -> str:
    half_w = scaled_w / 2.0
    half_h = scaled_h / 2.0
 
    # Timeline: keyTimes for translate + opacity are shared (0..1).
    total_duration = sum(s.duration for s in steps)
 
    translate_times = [0.0]
    translate_values = []
    opacity_times = [0.0]
    opacity_values = []
    orient_times = {d: [0.0] for d in ALL_DIRECTIONS}
    orient_values = {d: [] for d in ALL_DIRECTIONS}
 
    def center_xy(step: WalkStep) -> tuple[float, float]:
        return (
            cell_x(step.col) + CELL / 2.0,
            cell_y(step.row) + CELL / 2.0,
        )
 
    t = 0.0
    x0, y0 = center_xy(steps[0])
    translate_values.append(f"{x0 - half_w:.2f},{y0 - half_h:.2f}")
    opacity_values.append("1")
    for d in ALL_DIRECTIONS:
        orient_values[d].append("1" if d == steps[0].direction else "0")
 
    EPS = 0.0008  # tiny fraction of total duration, used to fake a teleport
 
    for i in range(1, len(steps)):
        step = steps[i]
        prev_visible_frac = step.duration / total_duration
        x, y = center_xy(step)
        pos_str = f"{x - half_w:.2f},{y - half_h:.2f}"
 
        if step.burrow_in:
            t_fade_start = t
            t_fade_end = t + prev_visible_frac * 0.35
            t_jump = min(t_fade_end + EPS, t_fade_end + prev_visible_frac * 0.1)
            t_fade_in_end = t + prev_visible_frac
 
            translate_times += [t_fade_end, t_jump]
            translate_values += [translate_values[-1], pos_str]
 
            opacity_times += [t_fade_start, t_fade_end, t_jump, t_fade_in_end]
            opacity_values += ["1", "0", "0", "1"]
 
            for d in ALL_DIRECTIONS:
                orient_times[d] += [t_jump]
                orient_values[d] += ["1" if d == step.direction else "0"]
 
            t = t_fade_in_end
        else:
            t_end = t + prev_visible_frac
            translate_times.append(t_end)
            translate_values.append(pos_str)
 
            for d in ALL_DIRECTIONS:
                orient_times[d].append(t)
                orient_values[d].append("1" if d == step.direction else "0")
 
            t = t_end
 
    translate_times[-1] = 1.0
    if opacity_times[-1] < 1.0:
        opacity_times.append(1.0)
        opacity_values.append(opacity_values[-1])
    for d in ALL_DIRECTIONS:
        if orient_times[d][-1] < 1.0:
            orient_times[d].append(1.0)
            orient_values[d].append(orient_values[d][-1])
 
    def fmt_times(times):
        return ";".join(f"{min(1.0, max(0.0, tt)):.6f}" for tt in times)
 
    def fmt_vals(vals):
        return ";".join(vals)
 
    dur_attr = f"{total_duration:.3f}s"
 
    translate_anim = (
        f'<animateTransform attributeName="transform" attributeType="XML" '
        f'type="translate" calcMode="linear" '
        f'keyTimes="{fmt_times(translate_times)}" '
        f'values="{fmt_vals(translate_values)}" '
        f'dur="{dur_attr}" repeatCount="indefinite" fill="freeze" />'
    )
    opacity_anim = (
        f'<animate attributeName="opacity" calcMode="discrete" '
        f'keyTimes="{fmt_times(opacity_times)}" '
        f'values="{fmt_vals(opacity_values)}" '
        f'dur="{dur_attr}" repeatCount="indefinite" fill="freeze" />'
    )
 
    cx, cy = scaled_w / 2.0, scaled_h / 2.0
    orientation_groups = []
    static_transform = {
        "RIGHT": "",
        "LEFT": f"translate({scaled_w:.2f},0) scale(-1,1)",
        "DOWN": f"translate({cx:.2f},{cy:.2f}) rotate(90) translate({-cx:.2f},{-cy:.2f})",
        "UP": f"translate({cx:.2f},{cy:.2f}) rotate(-90) translate({-cx:.2f},{-cy:.2f})",
    }
    for d in ALL_DIRECTIONS:
        anim = (
            f'<animate attributeName="opacity" calcMode="discrete" '
            f'keyTimes="{fmt_times(orient_times[d])}" '
            f'values="{fmt_vals(orient_values[d])}" '
            f'dur="{dur_attr}" repeatCount="indefinite" fill="freeze" />'
        )
        transform_attr = f' transform="{static_transform[d]}"' if static_transform[d] else ""
        orientation_groups.append(
            f'<g{transform_attr} opacity="{"1" if d == steps[0].direction else "0"}">'
            f'<use href="#snake-sprite" width="{scaled_w:.2f}" height="{scaled_h:.2f}" />'
            f"{anim}"
            f"</g>"
        )
 
    svg = (
        f'<defs><image id="snake-sprite" href="data:image/png;base64,{png_b64}" '
        f'width="{img_w}" height="{img_h}" preserveAspectRatio="none" /></defs>'
        f'<g id="snake" transform="translate({x0 - half_w:.2f},{y0 - half_h:.2f})">'
        f"{translate_anim}{opacity_anim}"
        f'<g width="{scaled_w:.2f}" height="{scaled_h:.2f}">'
        + "".join(orientation_groups)
        + "</g></g>"
    )
    return svg
 
 
def build_svg(grid, stats, steps, png_b64, img_w, img_h, scaled_w, scaled_h) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {SVG_W} {SVG_H}" width="{SVG_W}" height="{SVG_H}">'
        f'<rect x="0" y="0" width="{SVG_W}" height="{SVG_H}" fill="{BG_COLOR}" rx="6" ry="6" />'
        f"{build_header_svg()}"
        f"{build_grid_svg(grid)}"
        f"{build_snake_svg(steps, png_b64, img_w, img_h, scaled_w, scaled_h)}"
        f"{build_stats_and_legend_svg(stats)}"
        f"</svg>"
    )
 
 
# ========================================================================
# Main
# ========================================================================
 
def main() -> None:
    if not os.path.exists(SNAKE_PNG):
        print(f"ERROR: snake sprite not found at: {SNAKE_PNG}", file=sys.stderr)
        sys.exit(1)
 
    data = load_contributions(CONTRIBUTIONS_JSON)
    grid = days_to_grid(data["days"])
    stats = {
        "total": data["total"],
        "current_streak": data["current_streak"],
        "longest_streak": data["longest_streak"],
    }
 
    img_w, img_h = read_png_size(SNAKE_PNG)
    png_b64 = encode_png_base64(SNAKE_PNG)
 
    target_len_px = TARGET_SNAKE_LEN_CELLS * STEP
    aspect = img_h / img_w if img_w else 1.0
    scaled_w = target_len_px
    scaled_h = target_len_px * aspect
 
    half_w, half_h = scaled_w / 2.0, scaled_h / 2.0
 
    rng = random.Random()  # os-seeded: a different route on every run
    steps = generate_walk(rng, half_w, half_h)
 
    svg = build_svg(grid, stats, steps, png_b64, img_w, img_h, scaled_w, scaled_h)
 
    with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg)
 
    print(f"Done: {os.path.relpath(OUTPUT_SVG, os.getcwd())}")
 
 
if __name__ == "__main__":
    main()