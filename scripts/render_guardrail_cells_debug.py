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
SHARED_PAIR_OFFSET_PX = 1.35
SHARED_PAIR_STROKE_WIDTH = 2.0


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


def group_segments_by_physical_key(
    geometry: GuardrailGeometry,
) -> dict[tuple[tuple[int, int], tuple[int, int]], list[GuardrailSegment]]:
    segments_by_key: dict[tuple[tuple[int, int], tuple[int, int]], list[GuardrailSegment]] = defaultdict(list)

    for segment in geometry.segments:
        segments_by_key[segment_physical_key(segment)].append(segment)

    return segments_by_key


def is_shared_red_blue(segments: list[GuardrailSegment]) -> bool:
    colors = {segment.color for segment in segments}
    return "red" in colors and "blue" in colors


def first_segment_with_color(
    segments: list[GuardrailSegment],
    color: str,
) -> GuardrailSegment:
    for segment in segments:
        if segment.color == color:
            return segment
    raise ValueError(f"No {color} segment found")


def cell_by_id(geometry: GuardrailGeometry) -> dict[str, object]:
    return {cell.cell_id: cell for cell in geometry.cells}


def point_xy(string_index: int, fret: int) -> tuple[float, float]:
    return string_x(string_index), fret_y(fret)


def cell_centroid(cell) -> tuple[float, float]:
    points = [point_xy(point.string_index, point.fret) for point in cell.points]
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def inward_offset_for_segment(
    segment: GuardrailSegment,
    cells_by_id: dict[str, object],
    amount: float,
) -> tuple[float, float]:
    cell = cells_by_id.get(segment.cell_id)
    if cell is None:
        return 0.0, 0.0

    x1, y1 = point_xy(segment.start.string_index, segment.start.fret)
    x2, y2 = point_xy(segment.end.string_index, segment.end.fret)
    dx = x2 - x1
    dy = y2 - y1
    length = (dx * dx + dy * dy) ** 0.5

    if length == 0:
        return 0.0, 0.0

    normal_x = -dy / length
    normal_y = dx / length
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2
    centroid_x, centroid_y = cell_centroid(cell)
    toward_cell = (
        (centroid_x - mid_x) * normal_x
        + (centroid_y - mid_y) * normal_y
    )
    direction = 1.0 if toward_cell >= 0 else -1.0

    return normal_x * amount * direction, normal_y * amount * direction


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
    offset: tuple[float, float] = (0.0, 0.0),
    width: float | None = None,
) -> None:
    x1 = string_x(segment.start.string_index)
    x2 = string_x(segment.end.string_index)
    y1 = fret_y(segment.start.fret)
    y2 = fret_y(segment.end.fret)
    offset_x, offset_y = offset

    dwg.add(
        dwg.line(
            start=(x1 + offset_x, y1 + offset_y),
            end=(x2 + offset_x, y2 + offset_y),
            stroke=color_hex(segment.color),
            stroke_width=width if width is not None else stroke_width(segment.color),
            stroke_linecap="butt",
            opacity=1.0,
        )
    )


def draw_shared_guardrail_segment(
    dwg: svgwrite.Drawing,
    red_segment: GuardrailSegment,
    blue_segment: GuardrailSegment,
    cells_by_id: dict[str, object],
) -> None:
    draw_guardrail_segment(
        dwg,
        blue_segment,
        offset=inward_offset_for_segment(
            blue_segment,
            cells_by_id,
            SHARED_PAIR_OFFSET_PX,
        ),
        width=SHARED_PAIR_STROKE_WIDTH,
    )
    draw_guardrail_segment(
        dwg,
        red_segment,
        offset=inward_offset_for_segment(
            red_segment,
            cells_by_id,
            SHARED_PAIR_OFFSET_PX,
        ),
        width=SHARED_PAIR_STROKE_WIDTH,
    )


def draw_guardrail_geometry(dwg: svgwrite.Drawing, geometry: GuardrailGeometry) -> int:
    segments_by_key = group_segments_by_physical_key(geometry)
    cells_by_id = cell_by_id(geometry)
    shared_boundary_keys = {
        key for key, segments in segments_by_key.items() if is_shared_red_blue(segments)
    }

    for role in ("rectangle", "stack"):
        for segment in geometry.segments:
            if segment.role != role:
                continue
            if segment_physical_key(segment) in shared_boundary_keys:
                continue
            draw_guardrail_segment(dwg, segment)

    for key in sorted(shared_boundary_keys):
        draw_shared_guardrail_segment(
            dwg,
            first_segment_with_color(segments_by_key[key], "red"),
            first_segment_with_color(segments_by_key[key], "blue"),
            cells_by_id,
        )

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
    print(f"Shared-boundary offset px: {SHARED_PAIR_OFFSET_PX}")
    print(f"Shared-boundary treatment: paired inward rails")

    return out_path


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "B"
    render_debug(root)
