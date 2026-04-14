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
from .models import EventRenderCell, VerticalDiagramPage


SHAPE_FILL_SEQUENCE = [
    "#39C3FF",  # cyan
    "#C76BFF",  # violet
    "#FF7A59",  # coral
    "#FFD24D",  # gold
    "#58E07E",  # lime
]

SHAPE_STROKE_SEQUENCE = [
    "#A9E9FF",
    "#E2B6FF",
    "#FFB59F",
    "#FFE694",
    "#A9F3BE",
]


def build_vertical_fret_positions(top_y: float, board_height: float) -> list[float]:
    step = board_height / NUM_FRETS
    return [top_y + (step * f) for f in range(NUM_FRETS + 1)]


def string_x(left_x: float, board_width: float, string_index: int) -> float:
    spacing = board_width / (NUM_STRINGS - 1)
    return left_x + string_index * spacing


def note_center_y(fret_y: list[float], fret_number: int) -> float:
    if fret_number == 0:
        return fret_y[0] + 1.0
    return (fret_y[fret_number - 1] + fret_y[fret_number]) / 2.0


def label_for_tone(note) -> str:
    return note.chord_interval if note.source == "super" else note.note_name


def font_size_for_label(label: str) -> int:
    if len(label) >= 6:
        return 7
    if len(label) >= 4:
        return 8
    return 10


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


def text_color_for_tone(role: str, fill_hex: str, colors: dict[str, str]) -> str:
    if role in {"super_tone", "third"}:
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
    return 0.6 if "/" in label else 0.0


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
        "board_left_pad": 38,
        "board_right_pad": 16,
        "board_top_pad": HEADER_HEIGHT + 64,
        "board_bottom_pad": 46,
    }


def _section_total_height(cells: list[EventRenderCell]) -> float:
    return _row_height()


def _shape_groups_for_cell(cell: EventRenderCell) -> list[list]:
    """
    Group tones by pentatonic shape_id
    """
    groups = {}

    for t in cell.tones:
        if t.source != "super" or t.shape_id is None:
            continue

        groups.setdefault(t.shape_id, []).append(t)

    return list(groups.values())

    frets = sorted(set(t.fret for t in cell.tones))
    if not frets:
        return []

    windows: list[list[int]] = []
    current = [frets[0]]
    start = frets[0]

    for fret in frets[1:]:
        if fret <= start + 4:
            current.append(fret)
        else:
            windows.append(current)
            current = [fret]
            start = fret
    windows.append(current)

    groups: list[list] = []
    for window in windows:
        window_set = set(window)
        group = [t for t in cell.tones if t.fret in window_set]
        if group:
            groups.append(group)

    return groups


def _shape_bounds(
    tones: list,
    board_left: float,
    board_width: float,
    fret_y: list[float],
    note_radius: float,
) -> tuple[float, float, float, float]:
    xs = [string_x(board_left, board_width, t.string_index) for t in tones]
    ys = [note_center_y(fret_y, t.fret) for t in tones]

    left = min(xs) - (note_radius + 8)
    right = max(xs) + (note_radius + 8)
    top = min(ys) - (note_radius + 8)
    bottom = max(ys) + (note_radius + 8)

    return left, top, right, bottom


def _shape_fill_alpha(colors: dict[str, str]) -> float:
    return 0.26 if colors["background"].lower() != "#ffffff" else 0.14


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

    note_radius = min(11, (board_width / (NUM_STRINGS - 1)) * 0.24)

    # shape overlays first
    for idx, group in enumerate(_shape_groups_for_cell(cell)):
        shape_fill = SHAPE_FILL_SEQUENCE[idx % len(SHAPE_FILL_SEQUENCE)]
        shape_stroke = SHAPE_STROKE_SEQUENCE[idx % len(SHAPE_STROKE_SEQUENCE)]
        sl, st, sr, sb = _shape_bounds(group, board_left, board_width, fret_y, note_radius)
        points = []

for t in group:
    x = string_x(board_left, board_width, t.string_index)
    y = note_center_y(fret_y, t.fret)
    points.append((x, y))

if len(points) >= 3:
    shape = dwg.polygon(
        points=points,
        fill=shape_fill,
        stroke=shape_stroke,
        stroke_width=1.2,
    )
    shape["fill-opacity"] = _shape_fill_alpha(colors)
    shape["stroke-opacity"] = 0.6
    dwg.add(shape)

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
                stroke_width=2.2 if s in (0, 5) else 1.4,
            )
        )

    for f in range(NUM_FRETS + 1):
        y = fret_y[f]
        dwg.add(
            dwg.line(
                start=(board_left, y),
                end=(board_left + board_width, y),
                stroke=colors["nut_line"] if f == 0 else colors["fret_line"],
                stroke_width=2.0 if f == 0 else 1.0,
            )
        )

    for f in range(1, NUM_FRETS + 1):
        y = note_center_y(fret_y, f)
        dwg.add(
            dwg.text(
                str(f),
                insert=(board_left + board_width + BOARD_LABEL_GAP, y + 4),
                text_anchor="middle",
                font_size=13,
                font_weight="bold",
                font_family=SVG_FONT_FAMILY,
                fill=colors["label"],
            )
        )

    for s, name in enumerate(TUNING_BOTTOM_TO_TOP):
        x = string_x(board_left, board_width, s)
        dwg.add(
            dwg.text(
                name,
                insert=(x, board_top - 14),
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
            for frac in (0.32, 0.68):
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

    for tone in cell.tones:
        x = string_x(board_left, board_width, tone.string_index)
        y = note_center_y(fret_y, tone.fret)
        label = label_for_tone(tone)
        fill = colors.get(tone.role, colors["default"])
        text_fill = text_color_for_tone(tone.role, fill, colors)
        outline_fill = outline_color_for_tone(tone.role, colors)

        dwg.add(
            dwg.circle(
                center=(x, y),
                r=note_radius + 1.6,
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

    note_radius = min(11, (board_width / (NUM_STRINGS - 1)) * 0.24)

    # shape overlays first
    for idx, group in enumerate(_shape_groups_for_cell(cell)):
        shape_fill = SHAPE_FILL_SEQUENCE[idx % len(SHAPE_FILL_SEQUENCE)]
        shape_stroke = SHAPE_STROKE_SEQUENCE[idx % len(SHAPE_STROKE_SEQUENCE)]
        sl, st, sr, sb = _shape_bounds(group, board_left, board_width, fret_y, note_radius)

        c.saveState()
        c.setFillColor(HexColor(shape_fill))
        c.setStrokeColor(HexColor(shape_stroke))
        try:
            c.setFillAlpha(_shape_fill_alpha(colors))
            c.setStrokeAlpha(0.55)
        except Exception:
            pass
        c.setLineWidth(1.25)
        c.roundRect(tx(sl), ty(sb), tx(sr - sl), tx(sb - st), 16, fill=1, stroke=1)
        c.restoreState()

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
        c.setLineWidth(1.8 if s in (0, 5) else 1.1)
        c.line(tx(x), ty(board_top), tx(x), ty(board_top + board_height))

    for f in range(NUM_FRETS + 1):
        y = fret_y[f]
        c.setStrokeColor(HexColor(colors["nut_line"] if f == 0 else colors["fret_line"]))
        c.setLineWidth(2.0 if f == 0 else 0.8)
        c.line(tx(board_left), ty(y), tx(board_left + board_width), ty(y))

    c.setFillColor(HexColor(colors["label"]))
    c.setFont("Helvetica-Bold", 13)
    for f in range(1, NUM_FRETS + 1):
        y = note_center_y(fret_y, f)
        c.drawCentredString(tx(board_left + board_width + BOARD_LABEL_GAP), ty(y) - 4, str(f))

    c.setFont("Helvetica-Bold", 10)
    for s, name in enumerate(TUNING_BOTTOM_TO_TOP):
        x = string_x(board_left, board_width, s)
        c.drawCentredString(tx(x), ty(board_top - 14) - 1, name)

    marker_frets = [3, 5, 7, 9, 12, 15]
    for fret in marker_frets:
        if fret > NUM_FRETS:
            continue
        y = note_center_y(fret_y, fret)
        if fret == 12:
            c.setFillColor(HexColor(colors["marker_dot"]))
            for frac in (0.32, 0.68):
                c.circle(tx(board_left + board_width * frac), ty(y), 2.8, fill=1, stroke=0)
        else:
            c.setFillColor(HexColor(colors["marker_dot_subtle"]))
            c.circle(tx(board_left + board_width * 0.5), ty(y), 2.8, fill=1, stroke=0)

    for tone in cell.tones:
        x = string_x(board_left, board_width, tone.string_index)
        y = note_center_y(fret_y, tone.fret)
        fill = colors.get(tone.role, colors["default"])
        text_fill = text_color_for_tone(tone.role, fill, colors)
        outline_fill = outline_color_for_tone(tone.role, colors)
        label = label_for_tone(tone)

        c.setFillColor(HexColor(colors["background"]))
        c.circle(tx(x), ty(y), note_radius + 1.4, fill=1, stroke=0)

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
            c.drawCentredString(0.18, -2, label)
            c.drawCentredString(-0.18, -2, label)

        c.drawCentredString(0, -2, label)
        c.restoreState()