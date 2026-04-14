from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from highlander_render.config import PDF_PATH, SVG_PATH, TUNING_BOTTOM_TO_TOP
from highlander_render.harmony_engine import (
    build_effect_family,
    build_instance_name,
    build_superimposition_tone_map,
    note_to_index,
)
from highlander_render.pdf_builder import build_pdf
from highlander_render.svg_renderer import render_diagram_svg


# --------------------------------------------------
# EDIT THESE TO GENERATE DIFFERENT DIAGRAMS
# --------------------------------------------------

CHORD_ROOT = "G"
CHORD_QUALITY = "maj7"
SUPER_ROOT = "B"
SPELLING = "sharps"

# --------------------------------------------------


def build_fretboard_notes(
    chord_root: str,
    chord_quality: str,
    super_root: str,
    spelling: str,
) -> list[dict]:
    """
    Plot ONLY the scale tones.
    If a plotted scale tone is also a chord tone, it keeps chord-tone color.
    """

    classified_tones = build_superimposition_tone_map(
        chord_root=chord_root,
        chord_quality=chord_quality,
        super_root=super_root,
        spelling=spelling,
    )

    results: list[dict] = []

    for string_index, open_note in enumerate(TUNING_BOTTOM_TO_TOP):
        open_idx = note_to_index(open_note)

        for fret in range(0, 31):  # include fret 30
            pitch_idx = (open_idx + fret) % 12

            for tone in classified_tones:
                if tone.semitone == pitch_idx:
                    results.append(
                        {
                            "string_index": string_index,
                            "fret": fret,
                            "note_name": tone.note_name,
                            "role": tone.role,
                            "chord_interval": tone.chord_interval,
                            "source": tone.source,
                        }
                    )

    return results


def main() -> None:
    effect_family = build_effect_family(CHORD_ROOT, CHORD_QUALITY, SUPER_ROOT)
    instance_name = build_instance_name(CHORD_ROOT, CHORD_QUALITY, SUPER_ROOT)

    title = f"{instance_name} — {effect_family}"

    notes = build_fretboard_notes(
        chord_root=CHORD_ROOT,
        chord_quality=CHORD_QUALITY,
        super_root=SUPER_ROOT,
        spelling=SPELLING,
    )

    print("Generating SVG...")
    render_diagram_svg(notes=notes, title=title, svg_path=SVG_PATH)

    print("Building PDF...")
    build_pdf(notes=notes, title=title, pdf_path=PDF_PATH)

    print("Done.")
    print(f"SVG: {SVG_PATH}")
    print(f"PDF: {PDF_PATH}")


if __name__ == "__main__":
    main()