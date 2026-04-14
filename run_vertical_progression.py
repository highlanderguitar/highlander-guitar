from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from highlander_render.config import OUTPUT_DIR, NUM_FRETS
from highlander_render.harmony_engine import (
    build_diagram_tones_for_event,
    expand_chart_to_events,
)
from highlander_render.models import (
    EventRenderCell,
    ProgressionChart,
    SectionProgression,
    VerticalDiagramPage,
)
from highlander_render.vertical_renderer import build_pdf, render_page_svg


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "untitled"


def build_chart_from_text(path: Path) -> ProgressionChart:
    title = path.stem
    key = "C"
    spelling = "sharps"
    quality_overrides: dict[str, str] = {}
    sections: list[SectionProgression] = []

    current_name: str | None = None
    current_bars: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if ":" in line and line.split(":", 1)[0].lower() in {"title", "key", "spelling"}:
            k, v = [part.strip() for part in line.split(":", 1)]
            if k.lower() == "title":
                title = v
            elif k.lower() == "key":
                key = v
            elif k.lower() == "spelling":
                spelling = v
            continue

        if line.lower().startswith("quality "):
            payload = line[len("quality ") :]
            for item in payload.split():
                symbol, quality = item.split("=")
                q = quality.strip()
                if q == "7":
                    q = "dom7"
                elif q in {"m7", "min7"}:
                    q = "min7"
                elif q == "maj7":
                    q = "maj7"
                else:
                    raise ValueError(f"Unsupported quality override: {quality}")
                quality_overrides[symbol.strip()] = q
            continue

        if line.lower().endswith("section") or (len(line) == 1 and line.isalpha()):
            if current_name is not None:
                sections.append(SectionProgression(name=current_name, bars=current_bars))
            current_name = line
            current_bars = []
            continue

        if current_name is None:
            raise ValueError(f"Section header missing before progression line: {line}")

        bars = [part.strip() for part in line.split("|") if part.strip()]
        current_bars.extend(bars)

    if current_name is not None:
        sections.append(SectionProgression(name=current_name, bars=current_bars))

    if not sections:
        raise ValueError("No sections found in progression file.")

    return ProgressionChart(
        title=title,
        key=key,
        sections=sections,
        spelling=spelling,
        quality_overrides=quality_overrides,
    )


def build_page(chart: ProgressionChart, include_pink: bool) -> VerticalDiagramPage:
    events = expand_chart_to_events(chart)

    rendered_sections: list[tuple[str, list[EventRenderCell]]] = []
    for section in chart.sections:
        section_events = [event for event in events if event.section_name == section.name]
        cells = [
            EventRenderCell(
                event=event,
                tones=build_diagram_tones_for_event(
                    event,
                    include_pink=include_pink,
                    spelling=chart.spelling,
                    max_fret=NUM_FRETS,
                ),
            )
            for event in section_events
        ]
        rendered_sections.append((section.name, cells))

    subtitle = (
        "Pink Panther treatment: m7 -> 2m pent, maj7 -> 3m pent, dom7 -> 5m pent"
        if include_pink
        else "Chord tones only: 1, 3, 5, 7"
    )
    suffix = "pink_panther_vertical_progression" if include_pink else "chord_tone_vertical_progression"

    return VerticalDiagramPage(
        title=f"{chart.title} — {'Pink Panther Vertical Progression' if include_pink else 'Chord-Tone Vertical Progression'}",
        subtitle=subtitle,
        sections=rendered_sections,
    )


def render_theme_set(
    chart_slug: str,
    chord_page: VerticalDiagramPage,
    pink_page: VerticalDiagramPage,
    theme: str,
) -> list[Path]:
    chord_svg = OUTPUT_DIR / f"{chart_slug}_chord_tones_{theme}.svg"
    chord_pdf = OUTPUT_DIR / f"{chart_slug}_chord_tones_{theme}.pdf"
    pink_svg = OUTPUT_DIR / f"{chart_slug}_pink_panther_{theme}.svg"
    pink_pdf = OUTPUT_DIR / f"{chart_slug}_pink_panther_{theme}.pdf"

    render_page_svg(chord_page, chord_svg, theme=theme)
    build_pdf(chord_page, chord_pdf, theme=theme)

    render_page_svg(pink_page, pink_svg, theme=theme)
    build_pdf(pink_page, pink_pdf, theme=theme)

    return [chord_svg, chord_pdf, pink_svg, pink_pdf]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate vertical fretboard progression diagrams."
    )
    parser.add_argument(
        "progression_file",
        type=Path,
        help="Path to progression text file.",
    )
    args = parser.parse_args()

    if not args.progression_file.exists():
        raise FileNotFoundError(f"Progression file not found: {args.progression_file}")

    chart = build_chart_from_text(args.progression_file)
    chart_slug = slugify(chart.title)

    chord_page = build_page(chart, include_pink=False)
    pink_page = build_page(chart, include_pink=True)

    written_files: list[Path] = []
    for theme in ("dark", "print"):
        written_files.extend(render_theme_set(chart_slug, chord_page, pink_page, theme))

    print("Wrote:")
    for path in written_files:
        print(path)


if __name__ == "__main__":
    main()