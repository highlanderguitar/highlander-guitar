from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import svgwrite

from highlander_render.config import NUM_FRETS, NUM_STRINGS
from highlander_render.guardrail_cell_builder import build_guardrail_cells_from_spans
from highlander_render.guardrail_cells import GuardrailCell, GuardrailSegment
from highlander_render.harmony_engine import build_minor_pent_string_spans


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

CONNECTOR_INSET_PX = 5.0
RED_STROKE_WIDTH = 5.0
BLUE_STROKE_WIDTH = 4.0


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


def _segment_is_connector(segment: GuardrailSegment) -> bool:
    return segment.start.string_index != segment.end.string_index


def _cell_fret_bounds(cell: GuardrailCell) -> tuple[float, float]:
    frets = [point.fret for point in cell.points]
    return min(frets), max(frets)


def _connector_inset_for_cell(cell: GuardrailCell, segment: GuardrailSegment) -> float:
    if not _segment_is_connector(segment):
        return 0.0

    min_fret, max_fret = _cell_fret_bounds(cell)
    segment_mid_fret = (segment.start.fret + segment.end.fret) / 2.0
    cell_mid_fret = (min_fret + max_fret) / 2.0

    return CONNECTOR_INSET_PX if segment_mid_fret <= cell_mid_fret else -CONNECTOR_INSET_PX


def _build_endpoint_offsets(
    cells: list[GuardrailCell],
) -> dict[tuple[str, int, int], list[float]]:
    offsets: dict[tuple[str, int, int], list[float]] = {}

    for cell in cells:
        for segment in cell.segments:
            if not _segment_is_connector(segment):
                continue

            inset = _connector_inset_for_cell(cell, segment)

            for point in (segment.start, segment.end):
                key = (segment.color, point.string_index, point.fret)
                offsets.setdefault(key, []).append(inset)

    return offsets


def _choose_endpoint_offset(
    offsets: dict[tuple[str, int, int], list[float]],
    color: str,
    string_index: int,
    fret: int,
    preferred_sign: int,
) -> float:
    choices = offsets.get((color, string_index, fret), [])
    if not choices:
        return 0.0

    signed = [value for value in choices if value * preferred_sign > 0]
    if signed:
        return signed[0]

    return choices[0]


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


def draw_vertical_spans(
    dwg: svgwrite.Drawing,
    spans: dict[int, list[tuple[str, int, int]]],
    endpoint_offsets: dict[tuple[str, int, int], list[float]],
) -> None:
    for string_index in range(NUM_STRINGS):
        x = string_x(string_index)

        for color, fret_a, fret_b in spans.get(string_index, []):
            a, b = sorted((fret_a, fret_b))

            y1 = fret_y(a) + _choose_endpoint_offset(
                endpoint_offsets,
                color,
                string_index,
                a,
                preferred_sign=1,
            )
            y2 = fret_y(b) + _choose_endpoint_offset(
                endpoint_offsets,
                color,
                string_index,
                b,
                preferred_sign=-1,
            )

            dwg.add(
                dwg.line(
                    start=(x, y1),
                    end=(x, y2),
                    stroke=color_hex(color),
                    stroke_width=stroke_width(color),
                    stroke_linecap="butt",
                    opacity=1.0,
                )
            )


def draw_connector_segment(
    dwg: svgwrite.Drawing,
    cell: GuardrailCell,
    segment: GuardrailSegment,
) -> None:
    if not _segment_is_connector(segment):
        return

    y_inset = _connector_inset_for_cell(cell, segment)

    x1 = string_x(segment.start.string_index)
    y1 = fret_y(segment.start.fret) + y_inset
    x2 = string_x(segment.end.string_index)
    y2 = fret_y(segment.end.fret) + y_inset

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


def draw_cell_connectors(dwg: svgwrite.Drawing, cells: list[GuardrailCell]) -> None:
    for role in ("rectangle", "stack"):
        for cell in cells:
            if cell.role != role:
                continue

            for segment in cell.segments:
                draw_connector_segment(dwg, cell, segment)


def render_debug(root: str = "B") -> Path:
    output_dir = ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / f"debug_{root.lower()}_minor_guardrail_cells.svg"

    spans = build_minor_pent_string_spans(root, max_fret=NUM_FRETS)
    cells = build_guardrail_cells_from_spans(spans)
    endpoint_offsets = _build_endpoint_offsets(cells)

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

    draw_vertical_spans(dwg, spans, endpoint_offsets)
    draw_cell_connectors(dwg, cells)
    dwg.save()

    print(f"Wrote: {out_path}")
    print(f"Cells: {len(cells)}")
    print(f"Rectangles: {sum(1 for c in cells if c.role == 'rectangle')}")
    print(f"Stacks: {sum(1 for c in cells if c.role == 'stack')}")
    print("Spans:")
    for string_index in range(NUM_STRINGS):
        print(f"  {STRING_LABELS[string_index]}[{string_index}]: {spans.get(string_index, [])}")

    return out_path


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "B"
    render_debug(root)