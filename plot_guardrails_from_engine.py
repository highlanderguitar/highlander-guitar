from __future__ import annotations

from pathlib import Path
import sys

import svgwrite

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from highlander_render.config import get_theme, SVG_FONT_FAMILY
from highlander_render.harmony_engine import build_minor_pent_guardrail_diagram


OUTPUT_PATH = PROJECT_ROOT / "output" / "guardrail_engine_test.svg"

NUM_STRINGS = 6
NUM_FRETS_DISPLAY = 15
TUNING_BOTTOM_TO_TOP = ["E", "A", "D", "G", "B", "E"]

PAGE_WIDTH = 1500
PAGE_HEIGHT = 900

MARGIN_LEFT = 36
MARGIN_TOP = 36
PANEL_GAP_X = 36
PANEL_GAP_Y = 40

PANEL_WIDTH = 440
PANEL_HEIGHT = 330

BOARD_LEFT_PAD = 34
BOARD_RIGHT_PAD = 18
BOARD_TOP_PAD = 72
BOARD_BOTTOM_PAD = 28

NOTE_RADIUS = 11

RECT_COLOR = "#FF4A4A"
STACK_COLOR = "#46A8FF"


def string_x(left_x: float, board_width: float, string_index: int) -> float:
    inner_pad = board_width * 0.08
    usable = board_width - (2 * inner_pad)
    spacing = usable / (NUM_STRINGS - 1)
    return left_x + inner_pad + string_index * spacing


def build_fret_y(top_y: float, board_height: float, fret_min: int, fret_max: int) -> tuple[list[float], list[int]]:
    frets = list(range(fret_min, fret_max + 1))
    line_count = len(frets) + 1
    step = board_height / max(1, len(frets))
    y_positions = [top_y + step * i for i in range(line_count)]
    return y_positions, frets


def note_y(fret_y: list[float], fret_min: int, fret: int) -> float:
    if fret < fret_min:
        raise ValueError(f"fret {fret} below visible window min {fret_min}")
    idx = fret - fret_min + 1
    return (fret_y[idx - 1] + fret_y[idx]) / 2.0


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


def draw_edge(
    dwg: svgwrite.Drawing,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: str,
) -> None:
    dwg.add(
        dwg.line(
            start=(x1, y1),
            end=(x2, y2),
            stroke=color,
            stroke_width=4.0,
            stroke_linecap="round",
            opacity=0.92,
        )
    )


def draw_shape_panel(
    dwg: svgwrite.Drawing,
    shape_window,
    left: float,
    top: float,
    colors: dict[str, str],
) -> None:
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
            f"Shape {shape_window.shape_id}",
            insert=(left + 14, top + 22),
            font_size=18,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["title"],
        )
    )
    dwg.add(
        dwg.text(
            f"frets {shape_window.fret_min}-{shape_window.fret_max}",
            insert=(left + 14, top + 42),
            font_size=12,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["subtitle"],
        )
    )

    board_left = left + BOARD_LEFT_PAD
    board_top = top + BOARD_TOP_PAD
    board_width = PANEL_WIDTH - BOARD_LEFT_PAD - BOARD_RIGHT_PAD
    board_height = PANEL_HEIGHT - BOARD_TOP_PAD - BOARD_BOTTOM_PAD

    fret_y, frets = build_fret_y(board_top, board_height, shape_window.fret_min, shape_window.fret_max)

    # strings: ALWAYS draw all 6
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

    # fret lines
    for i, y in enumerate(fret_y):
        dwg.add(
            dwg.line(
                start=(board_left, y),
                end=(board_left + board_width, y),
                stroke=colors["nut_line"] if i == 0 else colors["fret_line"],
                stroke_width=1.6 if i == 0 else 0.65,
                opacity=0.85 if i == 0 else 0.55,
            )
        )

    # fret numbers
    for fret in frets:
        y = note_y(fret_y, shape_window.fret_min, fret)
        dwg.add(
            dwg.text(
                str(fret),
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
                insert=(x, board_top - 18),
                text_anchor="middle",
                font_size=10,
                font_weight="bold",
                font_family=SVG_FONT_FAMILY,
                fill=colors["label"],
            )
        )

    # edges
    for e in shape_window.edges:
        x1 = string_x(board_left, board_width, e.start_string_index)
        y1 = note_y(fret_y, shape_window.fret_min, e.start_fret)
        x2 = string_x(board_left, board_width, e.end_string_index)
        y2 = note_y(fret_y, shape_window.fret_min, e.end_fret)
        color = RECT_COLOR if e.color_role == "rectangle" else STACK_COLOR
        draw_edge(dwg, x1, y1, x2, y2, color)

    # tones
    for t in shape_window.tones:
        x = string_x(board_left, board_width, t.string_index)
        y = note_y(fret_y, shape_window.fret_min, t.fret)
        fill, outline, text_fill = tone_style(t.note_name)
        draw_note(dwg, x, y, t.degree_label, fill, outline, text_fill)


def main() -> None:
    colors = get_theme("dark")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    diagram = build_minor_pent_guardrail_diagram("B")

    dwg = svgwrite.Drawing(str(OUTPUT_PATH), size=(PAGE_WIDTH, PAGE_HEIGHT))
    dwg.add(
        dwg.rect(insert=(0, 0), size=(PAGE_WIDTH, PAGE_HEIGHT), fill=colors["background"])
    )

    dwg.add(
        dwg.text(
            "Guardrail Engine Test — B Minor Pent",
            insert=(MARGIN_LEFT, MARGIN_TOP),
            font_size=24,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["title"],
        )
    )

    x = MARGIN_LEFT
    y = MARGIN_TOP + 42

    for i, shape_window in enumerate(diagram.shape_windows[:5]):
        draw_shape_panel(dwg, shape_window, x, y, colors)
        x += PANEL_WIDTH + PANEL_GAP_X
        if (i + 1) % 3 == 0:
            x = MARGIN_LEFT
            y += PANEL_HEIGHT + PANEL_GAP_Y

    dwg.save()
    print(f"Wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()