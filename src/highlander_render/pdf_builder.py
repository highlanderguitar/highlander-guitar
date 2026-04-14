from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .config import (
    BOARD_BOTTOM,
    BOARD_HEIGHT,
    BOARD_LEFT,
    BOARD_RIGHT,
    BOARD_TOP,
    COLORS,
    HEIGHT,
    MARGIN_LEFT,
    NUM_FRETS,
    NUM_STRINGS,
    STRING_SPACING,
    TUNING_BOTTOM_TO_TOP,
    WIDTH,
)


SCALE_LENGTH = 1000.0


def string_y(string_index: int) -> float:
    return BOARD_BOTTOM - string_index * STRING_SPACING


def fret_distance_from_nut(fret_number: int) -> float:
    if fret_number <= 0:
        return 0.0
    return SCALE_LENGTH - (SCALE_LENGTH / (2 ** (fret_number / 12)))


def all_fret_positions() -> list[float]:
    raw = [fret_distance_from_nut(f) for f in range(NUM_FRETS + 1)]
    max_raw = raw[-1]
    usable_width = BOARD_RIGHT - BOARD_LEFT
    return [BOARD_LEFT + (x / max_raw) * usable_width for x in raw]


FRET_X = all_fret_positions()


def fret_line_x(fret_number: int) -> float:
    return FRET_X[fret_number]


def note_center_x(fret_number: int) -> float:
    if fret_number == 0:
        open_gap = max(24.0, (FRET_X[1] - FRET_X[0]) * 0.55)
        return BOARD_LEFT - open_gap
    left_x = FRET_X[fret_number - 1]
    right_x = FRET_X[fret_number]
    return (left_x + right_x) / 2.0


def get_color(role: str) -> str:
    return COLORS.get(role, COLORS["default"])


def label_for_note(note: dict) -> str:
    if note["source"] == "super":
        return note["chord_interval"]
    return note["note_name"]


def font_size_for_label(label: str, scale: float) -> int:
    if len(label) >= 6:
        return max(5, int(7 * scale))
    if len(label) >= 4:
        return max(6, int(8 * scale))
    return max(7, int(10 * scale))


def build_pdf(notes: list[dict], title: str, pdf_path: Path) -> None:
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    _, page_h = letter

    target_width = 520
    scale = target_width / WIDTH
    diagram_height = HEIGHT * scale

    origin_x = 50
    origin_y = page_h - 100 - diagram_height

    def tx(x: float) -> float:
        return origin_x + x * scale

    def ty(y: float) -> float:
        return origin_y + diagram_height - (y * scale)

    # Background
    c.setFillColor(HexColor(COLORS["background"]))
    c.rect(origin_x, origin_y, target_width, diagram_height, fill=1, stroke=0)

    # Title
    c.setFillColor(HexColor(COLORS["title"]))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, page_h - 50, title)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(tx(MARGIN_LEFT), ty(32), title)

    # Board outline
    c.setStrokeColor(HexColor(COLORS["fretboard_border"]))
    c.setLineWidth(1.5)
    c.rect(
        tx(BOARD_LEFT),
        ty(BOARD_BOTTOM),
        (BOARD_RIGHT - BOARD_LEFT) * scale,
        BOARD_HEIGHT * scale,
        fill=0,
        stroke=1,
    )

    # Strings
    for s in range(NUM_STRINGS):
        y = string_y(s)
        c.setStrokeColor(HexColor(COLORS["string_line"]))
        c.setLineWidth(3 if s in (0, 5) else 2)
        c.line(tx(BOARD_LEFT), ty(y), tx(BOARD_RIGHT), ty(y))

    # Frets
    for f in range(NUM_FRETS + 1):
        x = fret_line_x(f)
        c.setStrokeColor(HexColor(COLORS["fret_line"]))
        c.setLineWidth(4 if f == 0 else 1.2)
        c.line(tx(x), ty(BOARD_TOP), tx(x), ty(BOARD_BOTTOM))

    # Fret labels
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor(COLORS["label"]))
    for f in range(1, NUM_FRETS + 1):
        x = note_center_x(f)
        c.drawCentredString(tx(x), ty(BOARD_BOTTOM + 26) - 3, str(f))

    # String labels
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(HexColor(COLORS["label"]))
    for s, name in enumerate(TUNING_BOTTOM_TO_TOP):
        y = string_y(s)
        c.drawCentredString(tx(BOARD_LEFT - 30), ty(y) - 3, name)

    # Marker dots
    marker_frets = [3, 5, 7, 9, 12, 15, 17, 19, 21, 24, 27, 29]
    for fret in marker_frets:
        x = note_center_x(fret)
        fill = COLORS["marker_dot"] if fret in (12, 24) else COLORS["marker_dot_subtle"]
        c.setFillColor(HexColor(fill))
        if fret in (12, 24):
            c.circle(tx(x), ty(BOARD_TOP + BOARD_HEIGHT * 0.32), 6 * scale, fill=1, stroke=0)
            c.circle(tx(x), ty(BOARD_TOP + BOARD_HEIGHT * 0.68), 6 * scale, fill=1, stroke=0)
        else:
            c.circle(tx(x), ty(BOARD_TOP + BOARD_HEIGHT * 0.5), 6 * scale, fill=1, stroke=0)

    # Notes
    note_radius = min(13, STRING_SPACING * 0.29)

    for note in notes:
        x = note_center_x(note["fret"])
        y = string_y(note["string_index"])

        outer_r = (note_radius + 2) * scale
        inner_r = note_radius * scale
        label = label_for_note(note)

        c.setFillColor(HexColor(COLORS["background"]))
        c.circle(tx(x), ty(y), outer_r, fill=1, stroke=0)

        c.setFillColor(HexColor(get_color(note["role"])))
        c.setStrokeColor(HexColor("#FFFFFF"))
        c.setLineWidth(1)
        c.circle(tx(x), ty(y), inner_r, fill=1, stroke=1)

        c.setFillColor(HexColor(COLORS["note_text"]))
        c.setFont("Helvetica-Bold", font_size_for_label(label, scale))
        c.drawCentredString(tx(x), ty(y) - (3 * scale), label)

    c.save()