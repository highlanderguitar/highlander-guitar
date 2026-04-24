from pathlib import Path

import svgwrite

from .config import (
    BOARD_LABEL_GAP,
    DEFAULT_THEME,
    EVENT_LABEL_HEIGHT,
    HEADER_HEIGHT,
    HEIGHT,
    MARGIN_BOTTOM,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP,
    NUM_FRETS,
    NUM_STRINGS,
    SCALE_LENGTH,
    SVG_FONT_FAMILY,
    THEMES,
    TITLE_Y,
    TUNING_BOTTOM_TO_TOP,
    WIDTH,
    get_theme,
)


def board_left() -> float:
    return MARGIN_LEFT + 64


def board_right() -> float:
    return WIDTH - MARGIN_RIGHT


def board_top() -> float:
    return MARGIN_TOP + HEADER_HEIGHT + EVENT_LABEL_HEIGHT + BOARD_LABEL_GAP


def board_bottom() -> float:
    return HEIGHT - MARGIN_BOTTOM - 36


def board_height() -> float:
    return board_bottom() - board_top()


def string_spacing() -> float:
    return board_height() / (NUM_STRINGS - 1)


def string_y(string_index: int) -> float:
    """
    string_index:
        0 = bottom string on page
        5 = top string on page
    """
    return board_bottom() - string_index * string_spacing()


def fret_distance_from_nut(fret_number: int) -> float:
    if fret_number <= 0:
        return 0.0
    return SCALE_LENGTH - (SCALE_LENGTH / (2 ** (fret_number / 12)))


def all_fret_positions() -> list[float]:
    raw = [fret_distance_from_nut(f) for f in range(NUM_FRETS + 1)]
    max_raw = raw[-1]
    usable_width = board_right() - board_left()
    return [board_left() + (x / max_raw) * usable_width for x in raw]


FRET_X = all_fret_positions()


def fret_line_x(fret_number: int) -> float:
    return FRET_X[fret_number]


def note_center_x(fret_number: int) -> float:
    if fret_number == 0:
        open_gap = max(24.0, (FRET_X[1] - FRET_X[0]) * 0.55)
        return board_left() - open_gap
    left_x = FRET_X[fret_number - 1]
    right_x = FRET_X[fret_number]
    return (left_x + right_x) / 2.0


def span_start_x(start_fret: int) -> float:
    if start_fret <= 0:
        return board_left()
    return fret_line_x(start_fret - 1)


def span_end_x(end_fret: int) -> float:
    return fret_line_x(end_fret)


def get_color(theme: dict[str, str], role: str) -> str:
    return theme.get(role, theme["default"])


def get_guardrail_color(theme: dict[str, str], color_name: str) -> str:
    defaults = {
        "red": "#ff5a5a",
        "blue": "#4da3ff",
        "pink": "#ff66b3",
        "teal": "#33c7b5",
    }
    return theme.get(f"guardrail_{color_name}", defaults.get(color_name, theme["default"]))


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


def draw_guardrail_spans(
    dwg: svgwrite.Drawing,
    theme: dict[str, str],
    guardrail_spans: dict[int, list[tuple[str, int, int]]],
) -> None:
    if not guardrail_spans:
        return

    stroke_width = max(6.0, string_spacing() * 0.34)
    x_pad = 3.0

    for string_index, spans in guardrail_spans.items():
        y = string_y(string_index)

        for color_name, fret_a, fret_b in spans:
            x1 = span_start_x(fret_a) + x_pad
            x2 = span_end_x(fret_b) - x_pad

            if x2 <= x1:
                continue

            dwg.add(
                dwg.line(
                    start=(x1, y),
                    end=(x2, y),
                    stroke=get_guardrail_color(theme, color_name),
                    stroke_width=stroke_width,
                    stroke_linecap="round",
                    opacity=0.82,
                )
            )


def render_diagram_svg(
    notes: list[dict],
    title: str,
    svg_path: Path,
    guardrail_spans: dict[int, list[tuple[str, int, int]]] | None = None,
    theme_name: str = DEFAULT_THEME,
) -> None:
    theme = get_theme(theme_name)
    dwg = svgwrite.Drawing(str(svg_path), size=(WIDTH, HEIGHT))

    left = board_left()
    right = board_right()
    top = board_top()
    bottom = board_bottom()
    height = board_height()

    # Background
    dwg.add(
        dwg.rect(
            insert=(0, 0),
            size=("100%", "100%"),
            fill=theme["background"],
        )
    )

    # Title
    dwg.add(
        dwg.text(
            title,
            insert=(MARGIN_LEFT, TITLE_Y),
            font_size=20,
            font_weight="bold",
            font_family=SVG_FONT_FAMILY,
            fill=theme["title"],
        )
    )

    # Board outline
    dwg.add(
        dwg.rect(
            insert=(left, top),
            size=(right - left, height),
            fill="none",
            stroke=theme["fretboard_border"],
            stroke_width=1.5,
        )
    )

    # Strings
    for s in range(NUM_STRINGS):
        y = string_y(s)
        stroke_width = 3 if s in (0, 5) else 2
        dwg.add(
            dwg.line(
                start=(left, y),
                end=(right, y),
                stroke=theme["string_line"],
                stroke_width=stroke_width,
            )
        )

    # Frets
    for f in range(NUM_FRETS + 1):
        x = fret_line_x(f)
        dwg.add(
            dwg.line(
                start=(x, top),
                end=(x, bottom),
                stroke=theme["nut_line"] if f == 0 else theme["fret_line"],
                stroke_width=4 if f == 0 else 1.2,
            )
        )

    # Fret labels
    for f in range(1, NUM_FRETS + 1):
        x = note_center_x(f)
        dwg.add(
            dwg.text(
                str(f),
                insert=(x, bottom + 26),
                text_anchor="middle",
                font_size=11,
                font_family=SVG_FONT_FAMILY,
                fill=theme["label"],
            )
        )

    # String labels
    for s, name in enumerate(TUNING_BOTTOM_TO_TOP):
        y = string_y(s)
        dwg.add(
            dwg.text(
                name,
                insert=(left - 30, y + 4),
                text_anchor="middle",
                font_size=13,
                font_weight="bold",
                font_family=SVG_FONT_FAMILY,
                fill=theme["label"],
            )
        )

    # Marker dots
    marker_frets = [3, 5, 7, 9, 12, 15]
    for fret in marker_frets:
        x = note_center_x(fret)
        if fret == 12:
            dwg.add(
                dwg.circle(
                    center=(x, top + height * 0.32),
                    r=6,
                    fill=theme["marker_dot"],
                )
            )
            dwg.add(
                dwg.circle(
                    center=(x, top + height * 0.68),
                    r=6,
                    fill=theme["marker_dot"],
                )
            )
        else:
            dwg.add(
                dwg.circle(
                    center=(x, top + height * 0.5),
                    r=6,
                    fill=theme["marker_dot_subtle"],
                )
            )

    # Guardrail spans: same canonical board geometry, painted before note bubbles.
    draw_guardrail_spans(dwg, theme, guardrail_spans or {})

    # Notes
    note_radius = min(13, string_spacing() * 0.29)

    for note in notes:
        x = note_center_x(note["fret"])
        y = string_y(note["string_index"])
        fill = get_color(theme, note["role"])
        label = label_for_note(note)

        dwg.add(
            dwg.circle(
                center=(x, y),
                r=note_radius + 2,
                fill=theme["background"],
                stroke="none",
            )
        )

        outline_color = theme.get("seventh_outline", theme["note_outline"]) if note["role"] == "seventh" else theme["note_outline"]
        text_color = theme["note_text_dark"] if note["role"] in {"extension", "super_tone"} else theme["note_text_light"]

        dwg.add(
            dwg.circle(
                center=(x, y),
                r=note_radius,
                fill=fill,
                stroke=outline_color,
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
                font_family=SVG_FONT_FAMILY,
                fill=text_color,
            )
        )

    dwg.save()