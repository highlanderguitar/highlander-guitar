from pathlib import Path
import svgwrite

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
    """
    string_index:
        0 = bottom string on page
        5 = top string on page
    """
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


def font_size_for_label(label: str) -> int:
    if len(label) >= 6:
        return 7
    if len(label) >= 4:
        return 8
    return 10


def render_diagram_svg(notes: list[dict], title: str, svg_path: Path) -> None:
    dwg = svgwrite.Drawing(str(svg_path), size=(WIDTH, HEIGHT))

    # Background
    dwg.add(
        dwg.rect(
            insert=(0, 0),
            size=("100%", "100%"),
            fill=COLORS["background"],
        )
    )

    # Title
    dwg.add(
        dwg.text(
            title,
            insert=(MARGIN_LEFT, 32),
            font_size=20,
            font_weight="bold",
            fill=COLORS["title"],
        )
    )

    # Board outline
    dwg.add(
        dwg.rect(
            insert=(BOARD_LEFT, BOARD_TOP),
            size=(BOARD_RIGHT - BOARD_LEFT, BOARD_HEIGHT),
            fill="none",
            stroke=COLORS["fretboard_border"],
            stroke_width=1.5,
        )
    )

    # Strings
    for s in range(NUM_STRINGS):
        y = string_y(s)
        stroke_width = 3 if s in (0, 5) else 2
        dwg.add(
            dwg.line(
                start=(BOARD_LEFT, y),
                end=(BOARD_RIGHT, y),
                stroke=COLORS["string_line"],
                stroke_width=stroke_width,
            )
        )

    # Frets
    for f in range(NUM_FRETS + 1):
        x = fret_line_x(f)
        dwg.add(
            dwg.line(
                start=(x, BOARD_TOP),
                end=(x, BOARD_BOTTOM),
                stroke=COLORS["fret_line"],
                stroke_width=4 if f == 0 else 1.2,
            )
        )

    # Fret labels
    for f in range(1, NUM_FRETS + 1):
        x = note_center_x(f)
        dwg.add(
            dwg.text(
                str(f),
                insert=(x, BOARD_BOTTOM + 26),
                text_anchor="middle",
                font_size=11,
                fill=COLORS["label"],
            )
        )

    # String labels
    for s, name in enumerate(TUNING_BOTTOM_TO_TOP):
        y = string_y(s)
        dwg.add(
            dwg.text(
                name,
                insert=(BOARD_LEFT - 30, y + 4),
                text_anchor="middle",
                font_size=13,
                font_weight="bold",
                fill=COLORS["label"],
            )
        )

    # Marker dots
    marker_frets = [3, 5, 7, 9, 12, 15, 17, 19, 21, 24, 27, 29]
    for fret in marker_frets:
        x = note_center_x(fret)
        if fret in (12, 24):
            dwg.add(
                dwg.circle(
                    center=(x, BOARD_TOP + BOARD_HEIGHT * 0.32),
                    r=6,
                    fill=COLORS["marker_dot"],
                )
            )
            dwg.add(
                dwg.circle(
                    center=(x, BOARD_TOP + BOARD_HEIGHT * 0.68),
                    r=6,
                    fill=COLORS["marker_dot"],
                )
            )
        else:
            dwg.add(
                dwg.circle(
                    center=(x, BOARD_TOP + BOARD_HEIGHT * 0.5),
                    r=6,
                    fill=COLORS["marker_dot_subtle"],
                )
            )

    # Notes
    note_radius = min(13, STRING_SPACING * 0.29)

    for note in notes:
        x = note_center_x(note["fret"])
        y = string_y(note["string_index"])
        fill = get_color(note["role"])
        label = label_for_note(note)

        dwg.add(
            dwg.circle(
                center=(x, y),
                r=note_radius + 2,
                fill=COLORS["background"],
                stroke="none",
            )
        )

        dwg.add(
            dwg.circle(
                center=(x, y),
                r=note_radius,
                fill=fill,
                stroke="#FFFFFF",
                stroke_width=1,
            )
        )

        dwg.add(
            dwg.text(
                label,
                insert=(x, y + 3),
                text_anchor="middle",
                font_size=font_size_for_label(label),
                font_weight="bold",
                fill=COLORS["note_text"],
            )
        )

    dwg.save()