from __future__ import annotations

from pathlib import Path
import sys

import svgwrite

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from highlander_render.config import get_theme, SVG_FONT_FAMILY
from highlander_render.harmony_engine import note_to_index


OUTPUT_PATH = PROJECT_ROOT / "output" / "bm_pent_overlay_vertical.svg"

NUM_STRINGS = 6
NUM_FRETS = 15
TUNING_BOTTOM_TO_TOP = ["E", "A", "D", "G", "B", "E"]

PAGE_WIDTH = 980
PAGE_HEIGHT = 1180

MARGIN_LEFT = 36
MARGIN_TOP = 36

PANEL_WIDTH = 760
PANEL_HEIGHT = 1040

BOARD_LEFT_PAD = 54
BOARD_RIGHT_PAD = 24
BOARD_TOP_PAD = 120
BOARD_BOTTOM_PAD = 40

NOTE_RADIUS = 13

RECTANGLE_COLOR = "#FF4A4A"
STACK_COLOR = "#46A8FF"

# B minor pentatonic over G
# This is intentionally explicit and tweakable.
# It overlays Shape 1 and Shape 2 on the SAME full-board format.
SHAPES = [
    {
        "name": "Shape 1",
        "fret_region": (7, 10),
        "rectangle": {
            "low_E": ["B", "D"],
            "B": ["F#", "A"],
            "high_E": ["B", "D"],
        },
        "stack": {
            "A": ["E", "F#"],
            "D": ["A", "B"],
            "G": ["D", "E"],
        },
    },
    {
        "name": "Shape 2",
        "fret_region": (9, 12),
        "rectangle": {
            "A": ["F#", "A"],
            "D": ["B", "D"],
        },
        "stack": {
            "low_E": ["D", "E"],
            "G": ["E", "F#"],
            "B": ["A", "B"],
            "high_E": ["D", "E"],
        },
    },
]

STRING_NAME_TO_INDEX = {
    "low_E": 0,
    "A": 1,
    "D": 2,
    "G": 3,
    "B": 4,
    "high_E": 5,
}


def build_vertical_fret_positions(top_y: float, board_height: float) -> list[float]:
    step = board_height / NUM_FRETS
    return [top_y + (step * f) for f in range(NUM_FRETS + 1)]


def string_x(left_x: float, board_width: float, string_index: int) -> float:
    inner_pad = board_width * 0.08
    usable = board_width - (2 * inner_pad)
    spacing = usable / (NUM_STRINGS - 1)
    return left_x + inner_pad + string_index * spacing


def note_center_y(fret_y: list[float], fret_number: int) -> float:
    if fret_number == 0:
        return fret_y[0] - 2.0
    return (fret_y[fret_number - 1] + fret_y[fret_number]) / 2.0


def iter_positions_for_note(note_name: str, max_fret: int = NUM_FRETS) -> list[tuple[int, int]]:
    target = note_to_index(note_name)
    results: list[tuple[int, int]] = []
    for s, open_name in enumerate(TUNING_BOTTOM_TO_TOP):
        open_pitch = note_to_index(open_name)
        for fret in range(0, max_fret + 1):
            if (open_pitch + fret) % 12 == target:
                results.append((s, fret))
    return results


def choose_position_in_region(
    note_name: str,
    string_index: int,
    fret_min: int,
    fret_max: int,
) -> int | None:
    candidates = [
        fret
        for s, fret in iter_positions_for_note(note_name)
        if s == string_index and fret_min <= fret <= fret_max
    ]
    if not candidates:
        return None
    return min(candidates)


def chord_interval_from_g(note_name: str) -> str:
    chord_root = "G"
    semitone_distance = (note_to_index(note_name) - note_to_index(chord_root)) % 12
    mapping = {
        0: "1",
        2: "2/9",
        4: "3",
        5: "4/11",
        7: "5",
        9: "6/13",
        10: "b7",
        11: "7",
    }
    return mapping.get(semitone_distance, note_name)


def tone_style(note_name: str) -> tuple[str, str, str]:
    # Bm pent over G
    if note_name == "B":
        return "#FF4A4A", "#FFFFFF", "#111111"
    if note_name == "D":
        return "#64B5F6", "#FFFFFF", "#111111"
    if note_name == "F#":
        return "#A9712C", "#D6A85C", "#FFFFFF"
    if note_name in {"E", "A"}:
        return "#FF38D4", "#FFFFFF", "#111111"
    return "#CCCCCC", "#FFFFFF", "#111111"


def draw_line(
    dwg: svgwrite.Drawing,
    p1: tuple[float, float],
    p2: tuple[float, float],
    color: str,
    width: float = 4.0,
    opacity: float = 0.9,
) -> None:
    dwg.add(
        dwg.line(
            start=p1,
            end=p2,
            stroke=color,
            stroke_width=width,
            stroke_linecap="round",
            opacity=opacity,
        )
    )


def draw_note(
    dwg: svgwrite.Drawing,
    x: float,
    y: float,
    label: str,
    fill: str,
    outline: str,
    text_fill: str,
) -> None:
    dwg.add(
        dwg.circle(
            center=(x, y),
            r=NOTE_RADIUS + 1.5,
            fill="#1f2127",
            stroke="none",
        )
    )
    dwg.add(
        dwg.circle(
            center=(x, y),
            r=NOTE_RADIUS,
            fill=fill,
            stroke=outline,
            stroke_width=1.2,
        )
    )

    font_size = 8 if len(label) >= 4 else 10
    txt = dwg.text(
        label,
        insert=(x, y),
        text_anchor="middle",
        dominant_baseline="middle",
        font_size=font_size,
        font_weight="bold",
        font_family=SVG_FONT_FAMILY,
        fill=text_fill,
        transform=f"rotate(90 {x} {y})",
    )
    if "/" in label:
        txt["stroke"] = text_fill
        txt["stroke-width"] = 0.6
    dwg.add(txt)


def collect_shape_points(shape: dict) -> dict[tuple[str, str], tuple[int, int]]:
    """
    Returns mapping:
      (group_name, string_name, note_name) is simplified to (string_name, note_name) per group call
    """
    fret_min, fret_max = shape["fret_region"]
    points: dict[tuple[str, str], tuple[int, int]] = {}

    for group_name in ("rectangle", "stack"):
        for string_name, note_names in shape[group_name].items():
            s = STRING_NAME_TO_INDEX[string_name]
            for note_name in note_names:
                fret = choose_position_in_region(note_name, s, fret_min, fret_max)
                if fret is not None:
                    points[(f"{group_name}:{string_name}", note_name)] = (s, fret)

    return points


def group_points_for_string_set(
    group: dict[str, list[str]],
    fret_region: tuple[int, int],
) -> list[tuple[int, list[tuple[int, str]]]]:
    """
    Returns:
      [(string_index, [(fret, note_name), ...]), ...]
    """
    fret_min, fret_max = fret_region
    rows: list[tuple[int, list[tuple[int, str]]]] = []

    for string_name, note_names in group.items():
        s = STRING_NAME_TO_INDEX[string_name]
        pts: list[tuple[int, str]] = []
        for note_name in note_names:
            fret = choose_position_in_region(note_name, s, fret_min, fret_max)
            if fret is not None:
                pts.append((fret, note_name))
        pts.sort(key=lambda x: x[0])
        if pts:
            rows.append((s, pts))

    rows.sort(key=lambda x: x[0])
    return rows


def draw_rectangle_group(
    dwg: svgwrite.Drawing,
    shape: dict,
    board_left: float,
    board_width: float,
    fret_y: list[float],
) -> None:
    rows = group_points_for_string_set(shape["rectangle"], shape["fret_region"])

    # verticals on each string
    for s, pts in rows:
        if len(pts) < 2:
            continue
        p1 = (string_x(board_left, board_width, s), note_center_y(fret_y, pts[0][0]))
        p2 = (string_x(board_left, board_width, s), note_center_y(fret_y, pts[1][0]))
        draw_line(dwg, p1, p2, RECTANGLE_COLOR)

    # connect same ordinal across neighboring participating strings
    for i in range(len(rows) - 1):
        s1, pts1 = rows[i]
        s2, pts2 = rows[i + 1]
        limit = min(len(pts1), len(pts2))
        for j in range(limit):
            p1 = (string_x(board_left, board_width, s1), note_center_y(fret_y, pts1[j][0]))
            p2 = (string_x(board_left, board_width, s2), note_center_y(fret_y, pts2[j][0]))
            draw_line(dwg, p1, p2, RECTANGLE_COLOR)


def draw_stack_group(
    dwg: svgwrite.Drawing,
    shape: dict,
    board_left: float,
    board_width: float,
    fret_y: list[float],
) -> None:
    cols = group_points_for_string_set(shape["stack"], shape["fret_region"])

    # verticals on each participating string
    for s, pts in cols:
        if len(pts) < 2:
            continue
        p1 = (string_x(board_left, board_width, s), note_center_y(fret_y, pts[0][0]))
        p2 = (string_x(board_left, board_width, s), note_center_y(fret_y, pts[1][0]))
        draw_line(dwg, p1, p2, STACK_COLOR)

    # connect same ordinal across neighboring participating strings
    # this keeps the overlay in the "same board" format and is easy to tweak later
    for i in range(len(cols) - 1):
        s1, pts1 = cols[i]
        s2, pts2 = cols[i + 1]
        limit = min(len(pts1), len(pts2))
        for j in range(limit):
            p1 = (string_x(board_left, board_width, s1), note_center_y(fret_y, pts1[j][0]))
            p2 = (string_x(board_left, board_width, s2), note_center_y(fret_y, pts2[j][0]))
            draw_line(dwg, p1, p2, STACK_COLOR)


def collect_all_shape_notes(shapes: list[dict]) -> list[tuple[int, int, str]]:
    seen = set()
    notes: list[tuple[int, int, str]] = []

    for shape in shapes:
        fret_min, fret_max = shape["fret_region"]
        for group_name in ("rectangle", "stack"):
            for string_name, note_names in shape[group_name].items():
                s = STRING_NAME_TO_INDEX[string_name]
                for note_name in note_names:
                    fret = choose_position_in_region(note_name, s, fret_min, fret_max)
                    if fret is None:
                        continue
                    key = (s, fret, note_name)
                    if key in seen:
                        continue
                    seen.add(key)
                    notes.append(key)

    notes.sort(key=lambda x: (x[1], x[0], x[2]))
    return notes


def main() -> None:
    colors = get_theme("dark")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    dwg = svgwrite.Drawing(str(OUTPUT_PATH), size=(PAGE_WIDTH, PAGE_HEIGHT))
    dwg.add(dwg.rect(insert=(0, 0), size=(PAGE_WIDTH, PAGE_HEIGHT), fill=colors["background"]))

    dwg.add(
        dwg.text(
            "Bm Pent Over G — Overlay Diagnostic",
            insert=(MARGIN_LEFT, MARGIN_TOP),
            font_size=24,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["title"],
        )
    )
    dwg.add(
        dwg.text(
            "Full-board format with Shape 1 and Shape 2 overlaid",
            insert=(MARGIN_LEFT, MARGIN_TOP + 28),
            font_size=13,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["subtitle"],
        )
    )

    left = MARGIN_LEFT
    top = MARGIN_TOP + 70

    dwg.add(
        dwg.rect(
            insert=(left, top),
            size=(PANEL_WIDTH, PANEL_HEIGHT),
            rx=8,
            ry=8,
            fill=colors["background"],
            stroke=colors["event_divider"],
            stroke_width=1,
        )
    )

    dwg.add(
        dwg.text(
            "Bm pent over G",
            insert=(left + 14, top + 22),
            font_size=18,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["title"],
        )
    )

    board_left = left + BOARD_LEFT_PAD
    board_top = top + BOARD_TOP_PAD
    board_width = PANEL_WIDTH - BOARD_LEFT_PAD - BOARD_RIGHT_PAD
    board_height = PANEL_HEIGHT - BOARD_TOP_PAD - BOARD_BOTTOM_PAD

    fret_y = build_vertical_fret_positions(board_top, board_height)

    # strings
    for s in range(NUM_STRINGS):
        x = string_x(board_left, board_width, s)
        dwg.add(
            dwg.line(
                start=(x, board_top),
                end=(x, board_top + board_height),
                stroke=colors["string_line"],
                stroke_width=1.0 if s in (0, 5) else 0.75,
                opacity=0.55,
            )
        )

    # frets
    for f in range(NUM_FRETS + 1):
        y = fret_y[f]
        dwg.add(
            dwg.line(
                start=(board_left, y),
                end=(board_left + board_width, y),
                stroke=colors["nut_line"] if f == 0 else colors["fret_line"],
                stroke_width=1.6 if f == 0 else 0.65,
                opacity=0.85 if f == 0 else 0.55,
            )
        )

    # fret labels
    for f in range(1, NUM_FRETS + 1):
        y = note_center_y(fret_y, f)
        dwg.add(
            dwg.text(
                str(f),
                insert=(board_left - 18, y + 4),
                text_anchor="middle",
                font_size=11,
                font_weight="normal",
                font_family=SVG_FONT_FAMILY,
                fill=colors["label"],
            )
        )

    # string labels
    for s, name in enumerate(TUNING_BOTTOM_TO_TOP):
        x = string_x(board_left, board_width, s)
        dwg.add(
            dwg.text(
                name,
                insert=(x, board_top - 22),
                text_anchor="middle",
                font_size=10,
                font_weight="bold",
                font_family=SVG_FONT_FAMILY,
                fill=colors["label"],
            )
        )

    # overlay rails first
    for shape in SHAPES:
        draw_rectangle_group(dwg, shape, board_left, board_width, fret_y)
        draw_stack_group(dwg, shape, board_left, board_width, fret_y)

    # notes on top
    notes = collect_all_shape_notes(SHAPES)
    for s, fret, note_name in notes:
        x = string_x(board_left, board_width, s)
        y = note_center_y(fret_y, fret)
        fill, outline, text_fill = tone_style(note_name)
        label = chord_interval_from_g(note_name)
        draw_note(dwg, x, y, label, fill, outline, text_fill)

    dwg.save()
    print(f"Wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()