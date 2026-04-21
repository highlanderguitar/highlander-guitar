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


OUTPUT_PATH = PROJECT_ROOT / "output" / "string_span_bm_pent.svg"

NUM_STRINGS = 6
NUM_FRETS = 15
TUNING_BOTTOM_TO_TOP = ["E", "A", "D", "G", "B", "E"]

PAGE_WIDTH = 760
PAGE_HEIGHT = 1120

MARGIN_LEFT = 36
MARGIN_TOP = 36

PANEL_WIDTH = 640
PANEL_HEIGHT = 980

BOARD_LEFT_PAD = 34
BOARD_RIGHT_PAD = 18
BOARD_TOP_PAD = 110
BOARD_BOTTOM_PAD = 34

NOTE_RADIUS = 13

RECTANGLE_COLOR = "#FF4A4A"
STACK_COLOR = "#46A8FF"

# B minor pent over G
# Red = rectangle spans
# Blue = stack spans
STRING_SPANS = {
    0: [  # low E
        ("blue", 0, 2),
        ("red", 2, 5),
        ("red", 7, 10),
        ("blue", 10, 12),
        ("blue", 12, 14),
    ],
    1: [  # A
        ("red", 2, 5),
        ("blue", 5, 7),
        ("blue", 7, 9),
        ("red", 9, 12),
    ],
    2: [  # D
        ("blue", 0, 2),
        ("blue", 2, 4),
        ("red", 4, 7),
        ("red", 9, 12),
        ("blue", 12, 14),
    ],
    3: [  # G
        ("red", 0, 2),
        ("red", 4, 7),
        ("blue", 7, 9),
        ("blue", 9, 11),
        ("red", 11, 14),
    ],
    4: [  # B
        ("red", 0, 3),
        ("blue", 3, 5),
        ("blue", 5, 7),
        ("red", 7, 10),
        ("red", 12, 15),
    ],
    5: [  # high E
        ("blue", 0, 2),
        ("red", 2, 5),
        ("red", 7, 10),
        ("blue", 10, 12),
        ("blue", 12, 14),
    ],
}

BM_PENT_NOTES = {"B", "D", "E", "F#", "A"}


def build_vertical_fret_positions(top_y: float, board_height: float) -> list[float]:
    step = board_height / NUM_FRETS
    return [top_y + (step * f) for f in range(NUM_FRETS + 1)]


def string_x(left_x: float, board_width: float, string_index: int) -> float:
    inner_pad = board_width * 0.12
    usable = board_width - (2 * inner_pad)
    spacing = usable / (NUM_STRINGS - 1)
    return left_x + inner_pad + string_index * spacing


def note_center_y(fret_y: list[float], fret_number: int) -> float:
    if fret_number == 0:
        return fret_y[0] - 2.0
    return (fret_y[fret_number - 1] + fret_y[fret_number]) / 2.0


def note_name_at(string_open: str, fret: int) -> str:
    idx = (note_to_index(string_open) + fret) % 12
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return names[idx]


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
    opacity: float = 0.92,
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


def collect_bm_pent_positions() -> list[tuple[int, int, str]]:
    positions: list[tuple[int, int, str]] = []
    for string_index, open_name in enumerate(TUNING_BOTTOM_TO_TOP):
        for fret in range(0, NUM_FRETS + 1):
            name = note_name_at(open_name, fret)
            if name in BM_PENT_NOTES:
                positions.append((string_index, fret, name))
    return positions


def span_color(color_role: str) -> str:
    return RECTANGLE_COLOR if color_role == "red" else STACK_COLOR


def build_colored_nodes() -> dict[str, set[tuple[int, int]]]:
    """
    Each span contributes two endpoint nodes:
      (string_index, fret)
    grouped by color role.
    """
    nodes: dict[str, set[tuple[int, int]]] = {"red": set(), "blue": set()}
    for string_index, spans in STRING_SPANS.items():
        for color_role, fret_a, fret_b in spans:
            nodes[color_role].add((string_index, fret_a))
            nodes[color_role].add((string_index, fret_b))
    return nodes


def draw_vertical_spans(
    dwg: svgwrite.Drawing,
    board_left: float,
    board_width: float,
    fret_y: list[float],
) -> None:
    for string_index, spans in STRING_SPANS.items():
        x = string_x(board_left, board_width, string_index)
        for color_role, fret_a, fret_b in spans:
            y1 = note_center_y(fret_y, fret_a)
            y2 = note_center_y(fret_y, fret_b)
            draw_line(dwg, (x, y1), (x, y2), span_color(color_role))


def draw_horizontal_connectors(
    dwg: svgwrite.Drawing,
    board_left: float,
    board_width: float,
    fret_y: list[float],
) -> None:
    """
    Connect same-color endpoint nodes across adjacent strings
    when they sit on the same fret. This is the simplest clean
    polygon-outline layer on top of the string spans.
    """
    colored_nodes = build_colored_nodes()

    for color_role, nodes in colored_nodes.items():
        color = span_color(color_role)
        for string_index in range(NUM_STRINGS - 1):
            left_nodes = {fret for s, fret in nodes if s == string_index}
            right_nodes = {fret for s, fret in nodes if s == string_index + 1}
            shared_frets = sorted(left_nodes & right_nodes)

            for fret in shared_frets:
                x1 = string_x(board_left, board_width, string_index)
                x2 = string_x(board_left, board_width, string_index + 1)
                y = note_center_y(fret_y, fret)
                draw_line(dwg, (x1, y), (x2, y), color)


def main() -> None:
    colors = get_theme("dark")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    dwg = svgwrite.Drawing(str(OUTPUT_PATH), size=(PAGE_WIDTH, PAGE_HEIGHT))
    dwg.add(dwg.rect(insert=(0, 0), size=(PAGE_WIDTH, PAGE_HEIGHT), fill=colors["background"]))

    dwg.add(
        dwg.text(
            "Bm Pent Over G — String Span Diagnostic",
            insert=(MARGIN_LEFT, MARGIN_TOP),
            font_size=24,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["title"],
        )
    )
    dwg.add(
        dwg.text(
            "Red = rectangle spans, Blue = stack spans",
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

    # draw verticals first
    draw_vertical_spans(dwg, board_left, board_width, fret_y)

    # then connect outlines horizontally
    draw_horizontal_connectors(dwg, board_left, board_width, fret_y)

    # notes on top
    for string_index, fret, note_name in collect_bm_pent_positions():
        x = string_x(board_left, board_width, string_index)
        y = note_center_y(fret_y, fret)
        fill, outline, text_fill = tone_style(note_name)
        label = chord_interval_from_g(note_name)
        draw_note(dwg, x, y, label, fill, outline, text_fill)

    dwg.save()
    print(f"Wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()