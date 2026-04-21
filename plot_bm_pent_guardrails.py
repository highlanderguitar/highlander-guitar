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


OUTPUT_PATH = PROJECT_ROOT / "output" / "bm_pent_guardrail_shapes.svg"

NUM_FRETS = 15
NUM_STRINGS = 6
TUNING_BOTTOM_TO_TOP = ["E", "A", "D", "G", "B", "E"]

PAGE_WIDTH = 980
PAGE_HEIGHT = 760

MARGIN_LEFT = 36
MARGIN_TOP = 36
BOARD_GAP = 46

BOARD_WIDTH = 360
BOARD_HEIGHT = 500

NOTE_RADIUS = 13

RECTANGLE_COLOR = "#FF4A4A"
STACK_COLOR = "#46A8FF"

SUPER_ROOT = "B"

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
    inner_pad = board_width * 0.10
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


def draw_line(
    dwg: svgwrite.Drawing,
    p1: tuple[float, float],
    p2: tuple[float, float],
    color: str,
    width: float = 4.0,
) -> None:
    dwg.add(
        dwg.line(
            start=p1,
            end=p2,
            stroke=color,
            stroke_width=width,
            stroke_linecap="round",
            opacity=0.92,
        )
    )


def draw_rectangle_group(
    dwg: svgwrite.Drawing,
    shape: dict,
    board_left: float,
    board_width: float,
    fret_y: list[float],
) -> None:
    rect = shape["rectangle"]
    rows: list[list[tuple[float, float]]] = []

    for string_name, note_names in rect.items():
        s = STRING_NAME_TO_INDEX[string_name]
        pts: list[tuple[float, float]] = []
        for note_name in note_names:
            fret = choose_position_in_region(
                note_name, s, shape["fret_region"][0], shape["fret_region"][1]
            )
            if fret is not None:
                pts.append((string_x(board_left, board_width, s), note_center_y(fret_y, fret)))
        pts.sort(key=lambda p: p[1])
        if len(pts) == 2:
            rows.append(pts)

    for row in rows:
        draw_line(dwg, row[0], row[1], RECTANGLE_COLOR)

    rows.sort(key=lambda row: row[0][0])
    for i in range(len(rows) - 1):
        left_row = rows[i]
        right_row = rows[i + 1]
        draw_line(dwg, left_row[0], right_row[0], RECTANGLE_COLOR)
        draw_line(dwg, left_row[1], right_row[1], RECTANGLE_COLOR)


def draw_stack_group(
    dwg: svgwrite.Drawing,
    shape: dict,
    board_left: float,
    board_width: float,
    fret_y: list[float],
) -> None:
    stack = shape["stack"]

    columns: list[tuple[int, list[tuple[float, float]]]] = []
    for string_name, note_names in stack.items():
        s = STRING_NAME_TO_INDEX[string_name]
        pts: list[tuple[float, float]] = []
        for note_name in note_names:
            fret = choose_position_in_region(
                note_name, s, shape["fret_region"][0], shape["fret_region"][1]
            )
            if fret is not None:
                pts.append((string_x(board_left, board_width, s), note_center_y(fret_y, fret)))
        pts.sort(key=lambda p: p[1])
        if len(pts) == 2:
            columns.append((s, pts))

    columns.sort(key=lambda item: item[0])

    for _, pts in columns:
        draw_line(dwg, pts[0], pts[1], STACK_COLOR)

    for i in range(len(columns) - 1):
        _, left_pts = columns[i]
        _, right_pts = columns[i + 1]
        draw_line(dwg, left_pts[0], right_pts[0], STACK_COLOR)
        draw_line(dwg, left_pts[1], right_pts[1], STACK_COLOR)


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


def chord_interval_from_super_root(note_name: str) -> str:
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
    if note_name == "B":
        return "#FF4A4A", "#FFFFFF", "#111111"
    if note_name == "D":
        return "#64B5F6", "#FFFFFF", "#111111"
    if note_name == "F#":
        return "#A9712C", "#D6A85C", "#FFFFFF"
    if note_name in {"E", "A"}:
        return "#FF38D4", "#FFFFFF", "#111111"
    return "#CCCCCC", "#FFFFFF", "#111111"


def draw_board(
    dwg: svgwrite.Drawing,
    shape: dict,
    left: float,
    top: float,
    colors: dict[str, str],
) -> None:
    panel_height = BOARD_HEIGHT + 92

    dwg.add(
        dwg.rect(
            insert=(left, top),
            size=(BOARD_WIDTH, panel_height),
            rx=8,
            ry=8,
            fill=colors["background"],
            stroke=colors["event_divider"],
            stroke_width=1,
        )
    )

    dwg.add(
        dwg.text(
            shape["name"],
            insert=(left + 12, top + 20),
            font_size=18,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["title"],
        )
    )

    dwg.add(
        dwg.text(
            f'frets {shape["fret_region"][0]}-{shape["fret_region"][1]}',
            insert=(left + 12, top + 42),
            font_size=12,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["subtitle"],
        )
    )

    board_left = left + 18
    board_top = top + 88
    board_width = BOARD_WIDTH - 36
    board_height = BOARD_HEIGHT
    fret_y = build_vertical_fret_positions(board_top, board_height)

    # no border rectangle

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

    draw_rectangle_group(dwg, shape, board_left, board_width, fret_y)
    draw_stack_group(dwg, shape, board_left, board_width, fret_y)

    plotted = set()
    for group_name in ("rectangle", "stack"):
        for string_name, note_names in shape[group_name].items():
            s = STRING_NAME_TO_INDEX[string_name]
            for note_name in note_names:
                fret = choose_position_in_region(
                    note_name, s, shape["fret_region"][0], shape["fret_region"][1]
                )
                if fret is None:
                    continue
                key = (s, fret, note_name)
                if key in plotted:
                    continue
                plotted.add(key)

                x = string_x(board_left, board_width, s)
                y = note_center_y(fret_y, fret)
                fill, outline, text_fill = tone_style(note_name)
                label = chord_interval_from_super_root(note_name)
                draw_note(dwg, x, y, label, fill, outline, text_fill)


def main() -> None:
    colors = get_theme("dark")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    dwg = svgwrite.Drawing(str(OUTPUT_PATH), size=(PAGE_WIDTH, PAGE_HEIGHT))
    dwg.add(dwg.rect(insert=(0, 0), size=(PAGE_WIDTH, PAGE_HEIGHT), fill=colors["background"]))

    dwg.add(
        dwg.text(
            "Bm Pent Guardrail Shapes Over G",
            insert=(MARGIN_LEFT, MARGIN_TOP),
            font_size=24,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["title"],
        )
    )
    dwg.add(
        dwg.text(
            "Diagnostic plate — Shape 1 and Shape 2 only",
            insert=(MARGIN_LEFT, MARGIN_TOP + 28),
            font_size=13,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["subtitle"],
        )
    )

    x = MARGIN_LEFT
    y = MARGIN_TOP + 60
    for shape in SHAPES:
        draw_board(dwg, shape, x, y, colors)
        x += BOARD_WIDTH + BOARD_GAP

    dwg.save()
    print(f"Wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()