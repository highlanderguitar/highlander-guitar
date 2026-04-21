from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from highlander_render.config import OUTPUT_DIR, NUM_FRETS
from highlander_render.harmony_engine import (
    build_diagram_tones_for_event,
    chord_symbol_to_quality,
)
from highlander_render.models import (
    EventRenderCell,
    ProgressionChart,
    SectionProgression,
    VerticalDiagramPage,
)
from highlander_render.vertical_renderer import build_pdf, render_page_svg


TITLE_RE = re.compile(r"^Title:\s*(.+)$", re.IGNORECASE)
KEY_RE = re.compile(r"^Key:\s*(.+)$", re.IGNORECASE)
SPELLING_RE = re.compile(r"^Spelling:\s*(.+)$", re.IGNORECASE)
QUALITY_RE = re.compile(r"^quality\s+(.+)$", re.IGNORECASE)


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "progression"


def parse_quality_overrides(line: str) -> dict[str, str]:
    payload = QUALITY_RE.match(line)
    if not payload:
        return {}

    overrides: dict[str, str] = {}
    for part in payload.group(1).split():
        if "=" not in part:
            continue
        symbol, quality = part.split("=", 1)
        quality = quality.strip()

        if quality == "m7":
            quality = "min7"
        elif quality == "7":
            quality = "dom7"
        elif quality == "maj7":
            quality = "maj7"

        overrides[symbol.strip()] = quality

    return overrides


def parse_progression_file(path: Path) -> ProgressionChart:
    if not path.exists():
        raise FileNotFoundError(f"Progression file not found: {path}")

    lines = [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()]

    title = path.stem.replace("_", " ").title()
    key = "C"
    spelling = "sharps"
    quality_overrides: dict[str, str] = {}
    sections: list[SectionProgression] = []

    current_section_name: str | None = None
    current_bars: list[str] = []

    def flush_section() -> None:
        nonlocal current_section_name, current_bars
        if current_section_name and current_bars:
            sections.append(SectionProgression(name=current_section_name, bars=current_bars[:]))
        current_section_name = None
        current_bars = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        m = TITLE_RE.match(line)
        if m:
            title = m.group(1).strip()
            continue

        m = KEY_RE.match(line)
        if m:
            key = m.group(1).strip()
            continue

        m = SPELLING_RE.match(line)
        if m:
            spelling = m.group(1).strip().lower()
            continue

        if QUALITY_RE.match(line):
            quality_overrides.update(parse_quality_overrides(line))
            continue

        if line.lower().endswith("section"):
            flush_section()
            current_section_name = line
            continue

        if "|" in line:
            if current_section_name is None:
                current_section_name = "Section"
            bars = [bar.strip() for bar in line.split("|") if bar.strip()]
            current_bars.extend(bars)
            continue

    flush_section()

    if not sections:
        raise ValueError(f"No sections found in progression file: {path}")

    return ProgressionChart(
        title=title,
        key=key,
        sections=sections,
        spelling=spelling,
        quality_overrides=quality_overrides,
    )


def build_subtitle(include_pink: bool) -> str:
    if include_pink:
        return "Pink Panther treatment: m7 -> 2m pent, maj7 -> 3m pent, dom7 -> 5m pent"
    return "Chord tones only: 1, 3, 5, 7"


def build_page(chart: ProgressionChart, include_pink: bool) -> VerticalDiagramPage:
    sections_out: list[tuple[str, list[EventRenderCell]]] = []

    for section in chart.sections:
        cells: list[EventRenderCell] = []

        for bar in section.bars:
            fragments = [frag.strip() for frag in bar.split() if frag.strip()]
            if not fragments:
                fragments = [bar]

            for fragment in fragments:
                expanded: list[tuple[str, int]] = []
                matches = list(re.finditer(r"([A-Ga-g][#b]?(?:\([^)]*\))?)(-*)", fragment))
                beat_total = 0
                for m in matches:
                    symbol = m.group(1)
                    beats = 1 + len(m.group(2))
                    expanded.append((symbol, beats))
                    beat_total += beats

                if expanded and beat_total == 4:
                    pieces = expanded
                else:
                    pieces = [(fragment, 4)]

                for symbol, beats in pieces:
                    display_symbol, root, quality = chord_symbol_to_quality(
                        symbol,
                        chart.quality_overrides,
                    )

                    class EventObj:
                        pass

                    event = EventObj()
                    event.symbol = display_symbol
                    event.root = root
                    event.quality = quality
                    event.beats = beats
                    event.display_label = display_symbol
                    event.section_name = section.name
                    event.beat_offset_in_bar = 0
                    event.super_root = None

                    tones = build_diagram_tones_for_event(
                        event,
                        include_pink=include_pink,
                        spelling=chart.spelling,
                        max_fret=NUM_FRETS,
                    )
                    cells.append(EventRenderCell(event=event, tones=tones))

        sections_out.append((section.name, cells))

    title_suffix = "Pink Panther Vertical Progression" if include_pink else "Chord-Tone Vertical Progression"

    return VerticalDiagramPage(
        title=f"{chart.title} — {title_suffix}",
        subtitle=build_subtitle(include_pink),
        sections=sections_out,
    )


def write_outputs(chart: ProgressionChart, include_pink: bool) -> list[Path]:
    page = build_page(chart, include_pink=include_pink)
    stem = slugify(chart.title)
    kind = "pink_panther" if include_pink else "chord_tones"

    outputs: list[Path] = []
    for theme in ("dark", "print"):
        svg_path = OUTPUT_DIR / f"{stem}_{kind}_{theme}.svg"
        pdf_path = OUTPUT_DIR / f"{stem}_{kind}_{theme}.pdf"
        render_page_svg(page, svg_path, theme=theme)
        build_pdf(page, pdf_path, theme=theme)
        outputs.extend([svg_path, pdf_path])

    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("progression_file", help="Path to progression text file")
    args = parser.parse_args()

    chart = parse_progression_file(Path(args.progression_file))

    written = []
    written.extend(write_outputs(chart, include_pink=False))
    written.extend(write_outputs(chart, include_pink=True))

    print("Wrote:")
    for path in written:
        print(path)


if __name__ == "__main__":
    main()