from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PACKAGE_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

WIDTH = 2200
HEIGHT = 980

MARGIN_LEFT = 120
MARGIN_RIGHT = 70
MARGIN_TOP = 95
MARGIN_BOTTOM = 85

NUM_STRINGS = 6
NUM_FRETS = 15
SCALE_LENGTH = 1000.0

# bottom -> top on page
TUNING_BOTTOM_TO_TOP = ["E", "A", "D", "G", "B", "E"]

BOARD_LABEL_GAP = 22
TITLE_Y = 42
SECTION_TITLE_GAP = 34
ROW_GAP = 62
HEADER_HEIGHT = 28
EVENT_LABEL_HEIGHT = 18

SVG_FONT_FAMILY = "Arial, Helvetica, sans-serif"

THEMES = {
    "dark": {
        "background": "#202123",
        "panel_background": "#1B1C1F",
        "title": "#ECECF1",
        "subtitle": "#C5C5D2",
        "label": "#C5C5D2",
        "fretboard_border": "#A9A9B5",
        "fret_line": "#7A7A87",
        "nut_line": "#E8E8ED",
        "string_line": "#D6D6DD",
        "marker_dot": "#7D7D89",
        "marker_dot_subtle": "#54545D",
        "note_text_light": "#F7F7F7",
        "note_text_dark": "#111111",
        "event_divider": "#5E5E69",
        "note_outline": "#F8F8FC",
        "root": "#6FBF73",
        "third": "#FF3B3B",
        "fifth": "#64B5F6",
        "seventh": "#A9712C",
        "seventh_outline": "#D6A85C",
        "extension": "#E7C66A",
        "super_tone": "#FF2BD6",
        "default": "#F8F8FC",
    },
    "print": {
        "background": "#FFFFFF",
        "panel_background": "#FFFFFF",
        "title": "#111111",
        "subtitle": "#444444",
        "label": "#333333",
        "fretboard_border": "#EAEAEA",
        "fret_line": "#C8C8C8",
        "nut_line": "#8A8A8A",
        "string_line": "#1F1F1F",
        "marker_dot": "#B8B8B8",
        "marker_dot_subtle": "#D4D4D4",
        "note_text_light": "#F7F7F7",
        "note_text_dark": "#111111",
        "event_divider": "#D8D8D8",
        "note_outline": "#FFFFFF",
        "root": "#6FBF73",
        "third": "#FF3B3B",
        "fifth": "#64B5F6",
        "seventh": "#A9712C",
        "seventh_outline": "#D6A85C",
        "extension": "#E7C66A",
        "super_tone": "#FF2BD6",
        "default": "#111111",
    },
}

DEFAULT_THEME = "dark"


def get_theme(theme_name: str = DEFAULT_THEME) -> dict[str, str]:
    if theme_name not in THEMES:
        raise ValueError(
            f"Unknown theme '{theme_name}'. Supported themes: {', '.join(THEMES)}"
        )
    return THEMES[theme_name]