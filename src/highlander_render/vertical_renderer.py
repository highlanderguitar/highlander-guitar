from __future__ import annotations

from pathlib import Path

import svgwrite
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from .config import (
    BOARD_LABEL_GAP,
    DEFAULT_THEME,
    HEADER_HEIGHT,
    HEIGHT,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP,
    NUM_FRETS,
    NUM_STRINGS,
    ROW_GAP,
    SECTION_TITLE_GAP,
    SVG_FONT_FAMILY,
    TITLE_Y,
    TUNING_BOTTOM_TO_TOP,
    WIDTH,
    get_theme,
)
from .harmony_engine import build_string_span_overlay_for_event
from .models import EventRenderCell, GuardrailEdge, VerticalDiagramPage

RECTANGLE_COLOR = "#FF1744"
STACK_COLOR = "#00A6FF"

OUTER_STRING_STROKE = 1.3
INNER_STRING_STROKE = 0.9

# Note bubbles sit visually inside the fret box, not on the fret wire.
# Guardrails/polygon edges still use fret_line_y(...) below.
NOTE_CENTER_BIAS = 0.50

JOIN_INSET = 2.0
POLYGON_EDGE_PAD = 1.4

OPEN_STRING_RISE_PX = 6.0
STRING_LABEL_RISE_PX = 6.0
SLASH_LABEL_FONT_SIZE = 7.4
SLASH_LABEL_STROKE_WIDTH = 0.12
DERIVED_CONNECTOR_STROKE_WIDTH = 3.0
CONNECTOR_PARALLEL_OFFSET_PX = 3.6

# Current vertical renderer string indexing follows TUNING_BOTTOM_TO_TOP:
# 0=low E, 1=A, 2=D, 3=G, 4=B, 5=high E
G_STRING_INDEX = 3
B_STRING_INDEX = 4

TONE_FILL_OVERRIDES = {
    "root": "#7FD68B",        # light green, black text
    "third": "#B11226",       # darker red, white text
    "fifth": "#74C9FF",       # light blue, black text
    "seventh": "#A9712C",     # dark bronze, white text
    "super_tone": "#FF5CA8",  # bright pink, black text
}

FORCE_LIGHT_TEXT_ROLES = {"third", "seventh"}
FORCE_DARK_TEXT_ROLES = {"root", "fifth", "super_tone", "extension"}


def build_vertical_fret_positions(top_y: float, board_height: float) -> list[float]:
    step = board_height / NUM_FRETS
    return [top_y + (step * f) for f in range(NUM_FRETS + 1)]


def string_x(left_x: float, board_width: float, string_index: int) -> float:
    inner_pad = board_width * 0.045
    usable = board_width - (2 * inner_pad)
    spacing = usable / (NUM_STRINGS - 1)
    return left_x + inner_pad + string_index * spacing


def note_center_y(fret_y: list[float], fret_number: int) -> float:
    if fret_number == 0:
        return fret_y[0] - OPEN_STRING_RISE_PX
    y1 = fret_y[fret_number - 1]
    y2 = fret_y[fret_number]
    return y1 + ((y2 - y1) * NOTE_CENTER_BIAS)


def fret_line_y(fret_y: list[float], fret_number: int) -> float:
    return fret_y[fret_number]


def label_for_tone(note) -> str:
    return note.chord_interval if note.source == "super" else note.note_name


def font_size_for_label(label: str) -> float:
    if "/" in label:
        return SLASH_LABEL_FONT_SIZE
    if len(label) >= 6:
        return 7.0
    if len(label) >= 4:
        return 8.0
    return 10.0


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Expected 6-digit hex color, got: {hex_color}")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def relative_luminance(hex_color: str) -> float:
    r, g, b = hex_to_rgb(hex_color)

    def channel(c: int) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_l = channel(r)
    g_l = channel(g)
    b_l = channel(b)
    return 0.2126 * r_l + 0.7152 * g_l + 0.0722 * b_l


def fill_color_for_tone(role: str, colors: dict[str, str]) -> str:
    return TONE_FILL_OVERRIDES.get(role, colors.get(role, colors["default"]))


def text_color_for_tone(role: str, fill_hex: str, colors: dict[str, str]) -> str:
    if role in FORCE_LIGHT_TEXT_ROLES:
        return colors["note_text_light"]
    if role in FORCE_DARK_TEXT_ROLES:
        return colors["note_text_dark"]
    return (
        colors["note_text_dark"]
        if relative_luminance(fill_hex) >= 0.28
        else colors["note_text_light"]
    )


def outline_color_for_tone(role: str, colors: dict[str, str]) -> str:
    if role == "seventh":
        return colors.get("seventh_outline", colors["note_outline"])
    return colors["note_outline"]


def label_stroke_width(label: str) -> float:
    if "/" in label:
        return SLASH_LABEL_STROKE_WIDTH
    return 0.0


def span_color(color_role: str) -> str:
    return RECTANGLE_COLOR if color_role == "red" else STACK_COLOR


def edge_color(color_role: str) -> str:
    return RECTANGLE_COLOR if color_role == "rectangle" else STACK_COLOR


def string_stroke_width(string_index: int) -> float:
    return OUTER_STRING_STROKE if string_index in (0, 5) else INNER_STRING_STROKE


def guardrail_stroke_width_for_string(string_index: int) -> float:
    return string_stroke_width(string_index) * 2.0


def guardrail_cross_stroke_width(left_string_index: int, right_string_index: int) -> float:
    return min(
        guardrail_stroke_width_for_string(left_string_index),
        guardrail_stroke_width_for_string(right_string_index),
    )


def get_event_guardrail_spans(cell: EventRenderCell) -> dict[int, list[tuple[str, int, int]]]:
    spans = getattr(cell.event, "guardrail_spans", None)
    if spans:
        return spans
    return build_string_span_overlay_for_event(cell.event, max_fret=NUM_FRETS)


def get_event_guardrail_edges(cell: EventRenderCell) -> list[GuardrailEdge]:
    return list(getattr(cell.event, "guardrail_edges", []) or [])


def _connector_role_for_span_color(color_role: str) -> str:
    return "rectangle" if color_role == "red" else "stack"


def _span_color_for_connector_role(color_role: str) -> str:
    return "red" if color_role == "rectangle" else "blue"


def _guardrail_span_endpoints_by_color(
    spans: dict[int, list[tuple[str, int, int]]],
) -> dict[str, set[tuple[int, int]]]:
    """
    Collect guardrail span endpoints by connector role.

    IMPORTANT:
    Do NOT prune repeated stack endpoints here.

    The center blue stack span is already removed upstream in harmony_engine.py.
    If we also prune shared stack endpoints here, the stack/rectangle polygon
    edges lose valid shared vertices and the blue/red geometry gets jacked up.
    """
    endpoints: dict[str, set[tuple[int, int]]] = {
        "rectangle": set(),
        "stack": set(),
    }

    for string_index, string_spans in spans.items():
        if not 0 <= string_index < NUM_STRINGS:
            continue

        for span_role, fret_a, fret_b in string_spans:
            connector_role = _connector_role_for_span_color(span_role)

            if 0 <= fret_a <= NUM_FRETS:
                endpoints[connector_role].add((string_index, fret_a))

            if 0 <= fret_b <= NUM_FRETS:
                endpoints[connector_role].add((string_index, fret_b))

    return endpoints


def _derived_guardrail_connectors(
    spans: dict[int, list[tuple[str, int, int]]],
) -> list[tuple[str, int, int, int, int]]:
    endpoints_by_color = _guardrail_span_endpoints_by_color(spans)

    connectors: list[tuple[str, int, int, int, int]] = []
    seen: set[tuple[str, int, int, int, int]] = set()

    def add(color_role: str, s1: int, f1: int, s2: int, f2: int) -> None:
        key = (
            color_role,
            min(s1, s2),
            min(f1, f2),
            max(s1, s2),
            max(f1, f2),
        )
        if key in seen:
            return
        seen.add(key)
        connectors.append((color_role, s1, f1, s2, f2))

    for color_role, endpoints in endpoints_by_color.items():
        for string_index, fret in sorted(endpoints):
            next_string = string_index + 1
            if next_string >= NUM_STRINGS:
                continue

            is_g_to_b = string_index == G_STRING_INDEX and next_string == B_STRING_INDEX

            # SAME FRET CONNECT (standard behavior)
            if (next_string, fret) in endpoints:
                if not is_g_to_b:
                    add(color_role, string_index, fret, next_string, fret)

            # B STRING WARP
            if is_g_to_b and (B_STRING_INDEX, fret + 1) in endpoints:
                add(color_role, G_STRING_INDEX, fret, B_STRING_INDEX, fret + 1)

    return connectors


def _endpoint_inward_direction_for_span(
    spans: dict[int, list[tuple[str, int, int]]],
    connector_role: str,
    string_index: int,
    fret: int,
) -> int:
    """
    Return +1 if the same-colored span interior is below this endpoint,
    -1 if the same-colored span interior is above this endpoint,
    0 if no reliable same-colored span endpoint is found.

    Vertical board y increases downward, and fret numbers increase downward.
    """
    wanted_span_role = _span_color_for_connector_role(connector_role)

    for span_role, fret_a, fret_b in spans.get(string_index, []):
        if span_role != wanted_span_role:
            continue

        if fret == fret_a and fret_b != fret_a:
            return 1 if fret_b > fret_a else -1

        if fret == fret_b and fret_b != fret_a:
            return -1 if fret_b > fret_a else 1

    return 0


def _horizontal_connector_offset_direction(
    connector: tuple[str, int, int, int, int],
    spans: dict[int, list[tuple[str, int, int]]],
) -> float:
    color_role, s1, f1, s2, f2 = connector

    if f1 != f2:
        return 0.0

    d1 = _endpoint_inward_direction_for_span(spans, color_role, s1, f1)
    d2 = _endpoint_inward_direction_for_span(spans, color_role, s2, f2)

    if d1 == d2 and d1 != 0:
        return d1 * CONNECTOR_PARALLEL_OFFSET_PX

    if d1 != 0 and d2 == 0:
        return d1 * CONNECTOR_PARALLEL_OFFSET_PX

    if d2 != 0 and d1 == 0:
        return d2 * CONNECTOR_PARALLEL_OFFSET_PX

    return 0.0


def _offset_connector_points(
    connector: tuple[str, int, int, int, int],
    spans: dict[int, list[tuple[str, int, int]]],
    board_left: float,
    board_width: float,
    fret_y: list[float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    color_role, s1, f1, s2, f2 = connector

    x1 = string_x(board_left, board_width, s1)
    x2 = string_x(board_left, board_width, s2)
    y1 = fret_line_y(fret_y, f1)
    y2 = fret_line_y(fret_y, f2)

    if x1 <= x2:
        start_x = x1 + JOIN_INSET
        end_x = x2 - JOIN_INSET
    else:
        start_x = x1 - JOIN_INSET
        end_x = x2 + JOIN_INSET

    y_offset = _horizontal_connector_offset_direction(connector, spans)

    return (start_x, y1 + y_offset), (end_x, y2 + y_offset)


def draw_derived_guardrail_connectors_svg(
    dwg: svgwrite.Drawing,
    spans: dict[int, list[tuple[str, int, int]]],
    board_left: float,
    board_width: float,
    fret_y: list[float],
) -> None:
    connectors = _derived_guardrail_connectors(spans)

    for connector in connectors:
        color_role, *_ = connector
        start, end = _offset_connector_points(
            connector,
            spans,
            board_left,
            board_width,
            fret_y,
        )

        dwg.add(
            dwg.line(
                start=start,
                end=end,
                stroke=edge_color(color_role),
                stroke_width=DERIVED_CONNECTOR_STROKE_WIDTH,
                stroke_linecap="butt",
                opacity=1.0,
            )
        )


def draw_derived_guardrail_connectors_pdf(
    c,
    spans: dict[int, list[tuple[str, int, int]]],
    board_left: float,
    board_width: float,
    fret_y: list[float],
    tx,
    ty,
) -> None:
    c.setLineCap(0)
    connectors = _derived_guardrail_connectors(spans)

    for connector in connectors:
        color_role, *_ = connector
        start, end = _offset_connector_points(
            connector,
            spans,
            board_left,
            board_width,
            fret_y,
        )

        c.setStrokeColor(HexColor(edge_color(color_role)))
        c.setLineWidth(DERIVED_CONNECTOR_STROKE_WIDTH)
        c.line(tx(start[0]), ty(start[1]), tx(end[0]), ty(end[1]))


def _draw_edge_svg(
    dwg: svgwrite.Drawing,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str,
    left_string_index: int,
    right_string_index: int,
) -> None:
    dwg.add(
        dwg.line(
            start=start,
            end=end,
            stroke=color,
            stroke_width=guardrail_cross_stroke_width(left_string_index, right_string_index),
            stroke_linecap="butt",
            opacity=1.0,
        )
    )


def _draw_edge_pdf(
    c,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str,
    left_string_index: int,
    right_string_index: int,
    tx,
    ty,
) -> None:
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(guardrail_cross_stroke_width(left_string_index, right_string_index))
    c.line(tx(start[0]), ty(start[1]), tx(end[0]), ty(end[1]))


def _edge_points_for_guardrail_edge(
    edge: GuardrailEdge,
    board_left: float,
    board_width: float,
    fret_y: list[float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    x1 = string_x(board_left, board_width, edge.start_string_index) + JOIN_INSET
    x2 = string_x(board_left, board_width, edge.end_string_index) - JOIN_INSET

    base_y1 = fret_line_y(fret_y, edge.start_fret)
    base_y2 = fret_line_y(fret_y, edge.end_fret)

    if edge.side == "top":
        y1 = base_y1 + POLYGON_EDGE_PAD
        y2 = base_y2 + POLYGON_EDGE_PAD
    else:
        y1 = base_y1 - POLYGON_EDGE_PAD
        y2 = base_y2 - POLYGON_EDGE_PAD

    return (x1, y1), (x2, y2)


def _structural_node_centers(
    edges: list[GuardrailEdge],
    board_left: float,
    board_width: float,
    fret_y: list[float],
) -> list[tuple[float, float]]:
    seen: set[tuple[int, int]] = set()
    centers: list[tuple[float, float]] = []

    for edge in edges:
        for string_index, fret in (
            (edge.start_string_index, edge.start_fret),
            (edge.end_string_index, edge.end_fret),
        ):
            key = (string_index, fret)
            if key in seen:
                continue
            seen.add(key)

            x = string_x(board_left, board_width, string_index)
            y = note_center_y(fret_y, fret)
            centers.append((x, y))

    return centers


def draw_guardrail_nodes_svg(
    dwg: svgwrite.Drawing,
    edges: list[GuardrailEdge],
    board_left: float,
    board_width: float,
    fret_y: list[float],
    colors: dict[str, str],
) -> None:
    for x, y in _structural_node_centers(edges, board_left, board_width, fret_y):
        dwg.add(
            dwg.circle(
                center=(x, y),
                r=2.6,
                fill=colors["background"],
                stroke=colors["note_outline"],
                stroke_width=0.9,
            )
        )


def draw_guardrail_nodes_pdf(
    c,
    edges: list[GuardrailEdge],
    board_left: float,
    board_width: float,
    fret_y: list[float],
    tx,
    ty,
    colors: dict[str, str],
) -> None:
    for x, y in _structural_node_centers(edges, board_left, board_width, fret_y):
        c.setFillColor(HexColor(colors["background"]))
        c.setStrokeColor(HexColor(colors["note_outline"]))
        c.setLineWidth(0.9)
        c.circle(tx(x), ty(y), 2.6, fill=1, stroke=1)


def draw_guardrail_edges_svg(
    dwg: svgwrite.Drawing,
    edges: list[GuardrailEdge],
    board_left: float,
    board_width: float,
    fret_y: list[float],
) -> None:
    seen: set[tuple[str, int, int, int, int]] = set()

    for edge in edges:
        key = (
            edge.color_role,
            min(edge.start_string_index, edge.end_string_index),
            min(edge.start_fret, edge.end_fret),
            max(edge.start_string_index, edge.end_string_index),
            max(edge.start_fret, edge.end_fret),
        )
        if key in seen:
            continue
        seen.add(key)

        start_pt, end_pt = _edge_points_for_guardrail_edge(edge, board_left, board_width, fret_y)
        _draw_edge_svg(
            dwg,
            start_pt,
            end_pt,
            edge_color(edge.color_role),
            edge.start_string_index,
            edge.end_string_index,
        )


def draw_guardrail_edges_pdf(
    c,
    edges: list[GuardrailEdge],
    board_left: float,
    board_width: float,
    fret_y: list[float],
    tx,
    ty,
) -> None:
    seen: set[tuple[str, int, int, int, int]] = set()

    for edge in edges:
        key = (
            edge.color_role,
            min(edge.start_string_index, edge.end_string_index),
            min(edge.start_fret, edge.end_fret),
            max(edge.start_string_index, edge.end_string_index),
            max(edge.start_fret, edge.end_fret),
        )
        if key in seen:
            continue
        seen.add(key)

        start_pt, end_pt = _edge_points_for_guardrail_edge(edge, board_left, board_width, fret_y)
        _draw_edge_pdf(
            c,
            start_pt,
            end_pt,
            edge_color(edge.color_role),
            edge.start_string_index,
            edge.end_string_index,
            tx,
            ty,
        )


def draw_string_span_overlay_svg(
    dwg: svgwrite.Drawing,
    spans: dict[int, list[tuple[str, int, int]]],
    edges: list[GuardrailEdge],
    board_left: float,
    board_width: float,
    fret_y: list[float],
    colors: dict[str, str],
) -> None:
    for string_index, string_spans in spans.items():
        x = string_x(board_left, board_width, string_index)
        stroke_width = guardrail_stroke_width_for_string(string_index)

        for color_role, fret_a, fret_b in string_spans:
            y1 = fret_line_y(fret_y, fret_a)
            y2 = fret_line_y(fret_y, fret_b)

            dwg.add(
                dwg.line(
                    start=(x, y1),
                    end=(x, y2),
                    stroke=span_color(color_role),
                    stroke_width=stroke_width,
                    stroke_linecap="butt",
                    opacity=1.0,
                )
            )

    draw_derived_guardrail_connectors_svg(dwg, spans, board_left, board_width, fret_y)
    draw_guardrail_edges_svg(dwg, edges, board_left, board_width, fret_y)
    draw_guardrail_nodes_svg(dwg, edges, board_left, board_width, fret_y, colors)


def draw_string_span_overlay_pdf(
    c,
    spans: dict[int, list[tuple[str, int, int]]],
    edges: list[GuardrailEdge],
    board_left: float,
    board_width: float,
    fret_y: list[float],
    tx,
    ty,
    colors: dict[str, str],
) -> None:
    c.setLineCap(0)

    for string_index, string_spans in spans.items():
        x = string_x(board_left, board_width, string_index)
        stroke_width = guardrail_stroke_width_for_string(string_index)

        for color_role, fret_a, fret_b in string_spans:
            y1 = fret_line_y(fret_y, fret_a)
            y2 = fret_line_y(fret_y, fret_b)

            c.setStrokeColor(HexColor(span_color(color_role)))
            c.setLineWidth(stroke_width)
            c.line(tx(x), ty(y1), tx(x), ty(y2))

    draw_derived_guardrail_connectors_pdf(c, spans, board_left, board_width, fret_y, tx, ty)
    draw_guardrail_edges_pdf(c, edges, board_left, board_width, fret_y, tx, ty)
    draw_guardrail_nodes_pdf(c, edges, board_left, board_width, fret_y, tx, ty, colors)


def _row_height() -> float:
    return HEADER_HEIGHT + 760


def _max_cells_in_any_section(page: VerticalDiagramPage) -> int:
    return max((len(cells) for _, cells in page.sections), default=1)


def _layout_for_page(page: VerticalDiagramPage) -> dict[str, float]:
    max_cols = max(1, _max_cells_in_any_section(page))
    column_gap = 14
    column_width = 292
    total_width = (
        MARGIN_LEFT
        + MARGIN_RIGHT
        + (column_width * max_cols)
        + (column_gap * max(0, max_cols - 1))
    )
    page_width = max(WIDTH, int(total_width))
    return {
        "page_width": page_width,
        "column_gap": column_gap,
        "column_width": column_width,
        "board_left_pad": 42,
        "board_right_pad": 12,
        "board_top_pad": HEADER_HEIGHT + 96,
        "board_bottom_pad": 46,
    }


def _section_total_height(cells: list[EventRenderCell]) -> float:
    return _row_height()


def render_page_svg(
    page: VerticalDiagramPage,
    svg_path: Path,
    theme: str = DEFAULT_THEME,
) -> None:
    colors = get_theme(theme)
    layout = _layout_for_page(page)
    page_width = layout["page_width"]

    dwg = svgwrite.Drawing(str(svg_path), size=(page_width, HEIGHT))
    dwg.add(dwg.rect(insert=(0, 0), size=(page_width, HEIGHT), fill=colors["background"]))

    dwg.add(
        dwg.text(
            page.title,
            insert=(MARGIN_LEFT, TITLE_Y),
            font_size=24,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["title"],
        )
    )
    dwg.add(
        dwg.text(
            page.subtitle,
            insert=(MARGIN_LEFT, TITLE_Y + 28),
            font_size=13,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["subtitle"],
        )
    )

    y_cursor = MARGIN_TOP + 40
    for section_name, cells in page.sections:
        if not cells:
            continue

        dwg.add(
            dwg.text(
                section_name,
                insert=(MARGIN_LEFT, y_cursor),
                font_size=16,
                font_weight="bold",
                font_family=SVG_FONT_FAMILY,
                fill=colors["title"],
            )
        )

        y_cursor += SECTION_TITLE_GAP
        _render_section_svg(dwg, cells, y_cursor, colors, layout)
        y_cursor += _section_total_height(cells) + ROW_GAP

    dwg.save()


def _render_section_svg(
    dwg: svgwrite.Drawing,
    cells: list[EventRenderCell],
    top_y: float,
    colors: dict[str, str],
    layout: dict[str, float],
) -> None:
    column_gap = layout["column_gap"]
    column_width = layout["column_width"]
    board_left_pad = layout["board_left_pad"]
    board_right_pad = layout["board_right_pad"]
    board_top_pad = layout["board_top_pad"]
    board_bottom_pad = layout["board_bottom_pad"]

    board_width = column_width - board_left_pad - board_right_pad
    board_height = _row_height() - board_top_pad - board_bottom_pad

    y_cursor = top_y
    for row in [cells]:
        for col, cell in enumerate(row):
            left = MARGIN_LEFT + col * (column_width + column_gap)
            _render_event_svg(
                dwg,
                cell,
                left,
                y_cursor,
                column_width,
                board_left_pad,
                board_top_pad,
                board_width,
                board_height,
                colors,
            )
        y_cursor += _row_height()


def _render_event_svg(
    dwg,
    cell: EventRenderCell,
    left: float,
    top: float,
    column_width: float,
    board_left_pad: float,
    board_top_pad: float,
    board_width: float,
    board_height: float,
    colors: dict[str, str],
) -> None:
    panel_height = _row_height() - 12

    dwg.add(
        dwg.rect(
            insert=(left, top),
            size=(column_width, panel_height),
            rx=6,
            ry=6,
            fill=colors["background"],
            stroke=colors["event_divider"],
            stroke_width=1,
        )
    )

    title = f"{cell.event.display_label} ({cell.event.beats})"
    dwg.add(
        dwg.text(
            title,
            insert=(left + 10, top + 18),
            font_size=13,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=colors["title"],
        )
    )

    board_left = left + board_left_pad
    board_top = top + board_top_pad
    fret_y = build_vertical_fret_positions(board_top, board_height)
    note_radius = min(11, ((board_width - (board_width * 0.16)) / (NUM_STRINGS - 1)) * 0.24)

    dwg.add(
        dwg.rect(
            insert=(board_left, board_top),
            size=(board_width, board_height),
            fill="none",
            stroke=colors["fretboard_border"],
            stroke_width=1.2,
        )
    )

    for s in range(NUM_STRINGS):
        x = string_x(board_left, board_width, s)
        dwg.add(
            dwg.line(
                start=(x, board_top),
                end=(x, board_top + board_height),
                stroke=colors["string_line"],
                stroke_width=string_stroke_width(s),
                opacity=0.78,
            )
        )

    for f in range(NUM_FRETS + 1):
        y = fret_y[f]
        dwg.add(
            dwg.line(
                start=(board_left, y),
                end=(board_left + board_width, y),
                stroke=colors["nut_line"] if f == 0 else colors["fret_line"],
                stroke_width=2.0 if f == 0 else 0.8,
                opacity=1.0 if f == 0 else 0.8,
            )
        )

    for f in range(1, NUM_FRETS + 1):
        y = note_center_y(fret_y, f)
        dwg.add(
            dwg.text(
                str(f),
                insert=(board_left - BOARD_LABEL_GAP, y + 4),
                text_anchor="middle",
                font_size=13,
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
                insert=(x, board_top - 24 - STRING_LABEL_RISE_PX),
                text_anchor="middle",
                font_size=10,
                font_weight="bold",
                font_family=SVG_FONT_FAMILY,
                fill=colors["label"],
            )
        )

    marker_frets = [3, 5, 7, 9, 12, 15]
    for fret in marker_frets:
        if fret > NUM_FRETS:
            continue
        y = note_center_y(fret_y, fret)
        if fret == 12:
            for frac in (0.38, 0.62):
                dwg.add(
                    dwg.circle(
                        center=(board_left + board_width * frac, y),
                        r=4.2,
                        fill=colors["marker_dot"],
                    )
                )
        else:
            dwg.add(
                dwg.circle(
                    center=(board_left + board_width * 0.5, y),
                    r=4.2,
                    fill=colors["marker_dot_subtle"],
                )
            )

    show_guardrails = True
    print("DRAWING GUARDRAILS FOR", cell.event.display_label, getattr(cell.event, "super_root", None))
    if show_guardrails:
        spans = get_event_guardrail_spans(cell)
        if not spans:
            print("⚠️ NO SPANS for", cell.event.display_label)
        else:
            total = sum(len(v) for v in spans.values())
            print("SPAN COUNT:", total)
        edges = get_event_guardrail_edges(cell)
        draw_string_span_overlay_svg(
            dwg,
            spans,
            edges,
            board_left,
            board_width,
            fret_y,
            colors,
        )

    for tone in cell.tones:
        x = string_x(board_left, board_width, tone.string_index)
        y = note_center_y(fret_y, tone.fret)
        label = label_for_tone(tone)
        fill = fill_color_for_tone(tone.role, colors)
        text_fill = text_color_for_tone(tone.role, fill, colors)
        outline_fill = outline_color_for_tone(tone.role, colors)

        dwg.add(
            dwg.circle(
                center=(x, y),
                r=note_radius + 1.0,
                fill=colors["background"],
                stroke="none",
            )
        )
        dwg.add(
            dwg.circle(
                center=(x, y),
                r=note_radius,
                fill=fill,
                stroke=outline_fill,
                stroke_width=1.15 if tone.role == "seventh" else 0.9,
            )
        )

        txt = dwg.text(
            label,
            insert=(x, y),
            text_anchor="middle",
            dominant_baseline="middle",
            font_size=font_size_for_label(label),
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=text_fill,
            transform=f"rotate(90 {x} {y})",
        )
        if label_stroke_width(label) > 0:
            txt["stroke"] = text_fill
            txt["stroke-width"] = label_stroke_width(label)
        dwg.add(txt)


def build_pdf(
    page: VerticalDiagramPage,
    pdf_path: Path,
    theme: str = DEFAULT_THEME,
) -> None:
    colors = get_theme(theme)
    layout = _layout_for_page(page)

    page_w = layout["page_width"]
    page_h = HEIGHT

    c = canvas.Canvas(str(pdf_path), pagesize=(page_w, page_h))

    def tx(x: float) -> float:
        return x

    def ty(y: float) -> float:
        return page_h - y

    def draw_text(
        text: str,
        x: float,
        y: float,
        size: int,
        color: str,
        bold: bool = False,
        centered: bool = False,
    ) -> None:
        c.setFillColor(HexColor(color))
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        if centered:
            c.drawCentredString(tx(x), ty(y), text)
        else:
            c.drawString(tx(x), ty(y), text)

    c.setFillColor(HexColor(colors["background"]))
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    draw_text(page.title, MARGIN_LEFT, TITLE_Y, 24, colors["title"], bold=True)
    draw_text(page.subtitle, MARGIN_LEFT, TITLE_Y + 28, 13, colors["subtitle"], bold=True)

    y_cursor = MARGIN_TOP + 40
    for section_name, cells in page.sections:
        if not cells:
            continue
        draw_text(section_name, MARGIN_LEFT, y_cursor, 16, colors["title"], bold=True)
        y_cursor += SECTION_TITLE_GAP
        _render_section_pdf(c, cells, y_cursor, tx, ty, colors, layout)
        y_cursor += _section_total_height(cells) + ROW_GAP

    c.save()


def _render_section_pdf(
    c,
    cells: list[EventRenderCell],
    top_y: float,
    tx,
    ty,
    colors: dict[str, str],
    layout: dict[str, float],
) -> None:
    column_gap = layout["column_gap"]
    column_width = layout["column_width"]
    board_left_pad = layout["board_left_pad"]
    board_right_pad = layout["board_right_pad"]
    board_top_pad = layout["board_top_pad"]
    board_bottom_pad = layout["board_bottom_pad"]

    board_width = column_width - board_left_pad - board_right_pad
    board_height = _row_height() - board_top_pad - board_bottom_pad

    y_cursor = top_y
    for row in [cells]:
        for col, cell in enumerate(row):
            left = MARGIN_LEFT + col * (column_width + column_gap)
            _render_event_pdf(
                c,
                cell,
                left,
                y_cursor,
                column_width,
                board_left_pad,
                board_top_pad,
                board_width,
                board_height,
                tx,
                ty,
                colors,
            )
        y_cursor += _row_height()


def _render_event_pdf(
    c,
    cell: EventRenderCell,
    left: float,
    top: float,
    column_width: float,
    board_left_pad: float,
    board_top_pad: float,
    board_width: float,
    board_height: float,
    tx,
    ty,
    colors: dict[str, str],
):
    panel_height = _row_height() - 12

    c.setFillColor(HexColor(colors["background"]))
    c.setStrokeColor(HexColor(colors["event_divider"]))
    c.roundRect(
        tx(left),
        ty(top + panel_height),
        tx(column_width),
        tx(panel_height),
        6,
        fill=1,
        stroke=1,
    )

    c.setFillColor(HexColor(colors["title"]))
    c.setFont("Helvetica-Bold", 13)
    c.drawString(tx(left + 10), ty(top + 18), f"{cell.event.display_label} ({cell.event.beats})")

    board_left = left + board_left_pad
    board_top = top + board_top_pad
    fret_y = build_vertical_fret_positions(board_top, board_height)
    note_radius = min(11, ((board_width - (board_width * 0.16)) / (NUM_STRINGS - 1)) * 0.24)

    c.setStrokeColor(HexColor(colors["fretboard_border"]))
    c.rect(
        tx(board_left),
        ty(board_top + board_height),
        tx(board_width),
        tx(board_height),
        fill=0,
        stroke=1,
    )

    for s in range(NUM_STRINGS):
        x = string_x(board_left, board_width, s)
        c.setStrokeColor(HexColor(colors["string_line"]))
        c.setLineWidth(string_stroke_width(s))
        c.line(tx(x), ty(board_top), tx(x), ty(board_top + board_height))

    for f in range(NUM_FRETS + 1):
        y = fret_y[f]
        c.setStrokeColor(HexColor(colors["nut_line"] if f == 0 else colors["fret_line"]))
        c.setLineWidth(2.0 if f == 0 else 0.8)
        c.line(tx(board_left), ty(y), tx(board_left + board_width), ty(y))

    c.setFillColor(HexColor(colors["label"]))
    c.setFont("Helvetica", 13)
    for f in range(1, NUM_FRETS + 1):
        y = note_center_y(fret_y, f)
        c.drawCentredString(tx(board_left - BOARD_LABEL_GAP), ty(y) - 4, str(f))

    c.setFont("Helvetica-Bold", 10)
    for s, name in enumerate(TUNING_BOTTOM_TO_TOP):
        x = string_x(board_left, board_width, s)
        c.drawCentredString(tx(x), ty(board_top - 24 - STRING_LABEL_RISE_PX) - 1, name)

    marker_frets = [3, 5, 7, 9, 12, 15]
    for fret in marker_frets:
        if fret > NUM_FRETS:
            continue
        y = note_center_y(fret_y, fret)
        if fret == 12:
            c.setFillColor(HexColor(colors["marker_dot"]))
            for frac in (0.38, 0.62):
                c.circle(tx(board_left + board_width * frac), ty(y), 2.8, fill=1, stroke=0)
        else:
            c.setFillColor(HexColor(colors["marker_dot_subtle"]))
            c.circle(tx(board_left + board_width * 0.5), ty(y), 2.8, fill=1, stroke=0)

    show_guardrails = True
    print("DRAWING GUARDRAILS FOR", cell.event.display_label, getattr(cell.event, "super_root", None))
    if show_guardrails:
        spans = get_event_guardrail_spans(cell)
        if not spans:
            print("⚠️ NO SPANS for", cell.event.display_label)
        else:
            total = sum(len(v) for v in spans.values())
            print("SPAN COUNT:", total)
        edges = get_event_guardrail_edges(cell)
        draw_string_span_overlay_pdf(
            c,
            spans,
            edges,
            board_left,
            board_width,
            fret_y,
            tx,
            ty,
            colors,
        )

    for tone in cell.tones:
        x = string_x(board_left, board_width, tone.string_index)
        y = note_center_y(fret_y, tone.fret)
        fill = fill_color_for_tone(tone.role, colors)
        text_fill = text_color_for_tone(tone.role, fill, colors)
        outline_fill = outline_color_for_tone(tone.role, colors)
        label = label_for_tone(tone)

        c.setFillColor(HexColor(colors["background"]))
        c.circle(tx(x), ty(y), note_radius + 1.0, fill=1, stroke=0)

        c.setFillColor(HexColor(fill))
        c.setStrokeColor(HexColor(outline_fill))
        c.setLineWidth(1.15 if tone.role == "seventh" else 1.0)
        c.circle(tx(x), ty(y), note_radius, fill=1, stroke=1)

        c.saveState()
        c.translate(tx(x), ty(y))
        c.rotate(-90)
        c.setFillColor(HexColor(text_fill))
        c.setFont("Helvetica-Bold", font_size_for_label(label))

        if "/" in label:
            c.drawCentredString(0.08, -2, label)
            c.drawCentredString(-0.08, -2, label)

        c.drawCentredString(0, -2, label)
        c.restoreState()