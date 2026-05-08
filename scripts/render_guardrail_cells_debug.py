from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import svgwrite

from highlander_render.config import NUM_FRETS, NUM_STRINGS
from highlander_render.guardrail_cell_builder import build_minor_pent_guardrail_geometry
from highlander_render.guardrail_cells import GuardrailGeometry, GuardrailSegment


RECTANGLE_COLOR = "#FF1744"
STACK_COLOR = "#00A6FF"

WIDTH = 520
HEIGHT = 1320
MARGIN_X = 80
MARGIN_TOP = 80
MARGIN_BOTTOM = 80

STRING_TOP = MARGIN_TOP
STRING_BOTTOM = HEIGHT - MARGIN_BOTTOM
BOARD_WIDTH = WIDTH - (2 * MARGIN_X)

STRING_LABELS = ["E", "A", "D", "G", "B", "E"]

RED_STROKE_WIDTH = 5.0
BLUE_STROKE_WIDTH = 4.0
SHARED_BOUNDARY_OFFSET_PX = 2.2


def string_x(string_index: int) -> float:
    spacing = BOARD_WIDTH / (NUM_STRINGS - 1)
    return MARGIN_X + (string_index * spacing)


def fret_y(fret: int) -> float:
    usable_height = STRING_BOTTOM - STRING_TOP
    return STRING_TOP + (usable_height / NUM_FRETS) * fret


def color_hex(color: str) -> str:
    return RECTANGLE_COLOR if color == "red" else STACK_COLOR


def stroke_width(color: str) -> float:
    return RED_STROKE_WIDTH if color == "red" else BLUE_STROKE_WIDTH


def segment_physical_key(segment: GuardrailSegment) -> tuple[tuple[int, int], tuple[int, int]]:
    endpoints = (
        (segment.start.string_index, segment.start.fret),
        (segment.end.string_index, segment.end.fret),
    )
    return tuple(sorted(endpoints))


def build_shared_boundary_keys(
    geometry: GuardrailGeometry,
) -> set[tuple[tuple[int, int], tuple[int, int]]]:
    colors_by_key: dict[tuple[tuple[int, int], tuple[int, int]], set[str]] = defaultdict(set)

    for segment in geometry.segments:
        colors_by_key[segment_physical_key(segment)].add(segment.color)

    return {
        key
        for key, colors in colors_by_key.items()
        if "red" in colors and "blue" in colors
    }


def perpendicular_offset(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    amount: float,
) -> tuple[float, float]:
    dx = x2 - x1
    dy = y2 - y1
    length = (dx * dx + dy * dy) ** 0.5

    if length == 0:
        return 0.0, 0.0

    return (-dy / length * amount, dx / length * amount)


def draw_board(dwg: svgwrite.Drawing) -> None:
    dwg.add(dwg.rect(insert=(0, 0), size=(WIDTH, HEIGHT), fill="#111111"))

    for s in range(NUM_STRINGS):
        x = string_x(s)
        dwg.add(
            dwg.line(
                start=(x, STRING_TOP),
                end=(x, STRING_BOTTOM),
                stroke="#777777",
                stroke_width=1.2,
                opacity=0.7,
            )
        )
        dwg.add(
            dwg.text(
                STRING_LABELS[s],
                insert=(x, STRING_TOP - 28),
                text_anchor="middle",
                font_size=18,
                font_weight="bold",
                font_family="Arial",
                fill="#DDDDDD",
            )
        )

    for f in range(NUM_FRETS + 1):
        y = fret_y(f)
        dwg.add(
            dwg.line(
                start=(MARGIN_X, y),
                end=(MARGIN_X + BOARD_WIDTH, y),
                stroke="#DDDDDD" if f == 0 else "#555555",
                stroke_width=2.2 if f == 0 else 0.8,
                opacity=0.9 if f == 0 else 0.55,
            )
        )

        if f > 0:
            dwg.add(
                dwg.text(
                    str(f),
                    insert=(MARGIN_X - 34, y + 5),
                    text_anchor="middle",
                    font_size=14,
                    font_family="Arial",
                    fill="#BBBBBB",
                )
            )


def draw_guardrail_segment(
    dwg: svgwrite.Drawing,
    segment: GuardrailSegment,
    shared_boundary_keys: set[tuple[tuple[int, int], tuple[int, int]]],
) -> None:
    x1 = string_x(segment.start.string_index)
    x2 = string_x(segment.end.string_index)
    y1 = fret_y(segment.start.fret)
    y2 = fret_y(segment.end.fret)

    if segment_physical_key(segment) in shared_boundary_keys:
        direction = -1.0 if segment.color == "red" else 1.0
        offset_x, offset_y = perpendicular_offset(
            x1,
            y1,
            x2,
            y2,
            SHARED_BOUNDARY_OFFSET_PX * direction,
        )
        x1 += offset_x
        x2 += offset_x
        y1 += offset_y
        y2 += offset_y

    dwg.add(
        dwg.line(
            start=(x1, y1),
            end=(x2, y2),
            stroke=color_hex(segment.color),
            stroke_width=stroke_width(segment.color),
            stroke_linecap="butt",
            opacity=1.0,
        )
    )


def draw_guardrail_geometry(dwg: svgwrite.Drawing, geometry: GuardrailGeometry) -> int:
    shared_boundary_keys = build_shared_boundary_keys(geometry)

    for role in ("rectangle", "stack"):
        for segment in geometry.segments:
            if segment.role != role:
                continue
            draw_guardrail_segment(dwg, segment, shared_boundary_keys)

    return len(shared_boundary_keys)


def render_debug(root: str = "B") -> Path:
    output_dir = ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / f"debug_{root.lower()}_minor_guardrail_cells.svg"

    geometry = build_minor_pent_guardrail_geometry(root, max_fret=NUM_FRETS)

    dwg = svgwrite.Drawing(str(out_path), size=(WIDTH, HEIGHT))
    draw_board(dwg)

    dwg.add(
        dwg.text(
            f"{root} minor pentatonic guardrail cells",
            insert=(MARGIN_X, 38),
            font_size=22,
            font_weight="bold",
            font_family="Arial",
            fill="#FFFFFF",
        )
    )

    shared_boundary_count = draw_guardrail_geometry(dwg, geometry)
    dwg.save()

    red_segments = sum(1 for segment in geometry.segments if segment.color == "red")
    blue_segments = sum(1 for segment in geometry.segments if segment.color == "blue")

    print(f"Wrote: {out_path}")
    print(f"Cells: {len(geometry.cells)}")
    print(f"Rectangles: {sum(1 for c in geometry.cells if c.role == 'rectangle')}")
    print(f"Stacks: {sum(1 for c in geometry.cells if c.role == 'stack')}")
    print(f"Segments: {len(geometry.segments)}")
    print(f"Red segments: {red_segments}")
    print(f"Blue segments: {blue_segments}")
    print(f"Shared red/blue boundaries: {shared_boundary_count}")
    print(f"Shared-boundary offset px: {SHARED_BOUNDARY_OFFSET_PX}")

    return out_path


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "B"
    render_debug(root)
