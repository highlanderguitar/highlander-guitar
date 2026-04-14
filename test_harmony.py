from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from highlander_render.harmony_engine import (
    build_effect_family,
    build_instance_name,
    build_superimposition_tone_map,
)


def print_case(
    chord_root: str,
    chord_quality: str,
    super_root: str,
    spelling: str = "sharps",
) -> None:
    print("=" * 72)
    print(f"CHORD: {chord_root}{chord_quality}")
    print(f"SUPER: {super_root} minor_pent")
    print(f"SPELLING: {spelling}")
    print(f"EFFECT FAMILY: {build_effect_family(chord_root, chord_quality, super_root)}")
    print(f"INSTANCE NAME: {build_instance_name(chord_root, chord_quality, super_root)}")
    print()

    tones = build_superimposition_tone_map(
        chord_root=chord_root,
        chord_quality=chord_quality,
        super_root=super_root,
        super_scale_type="minor_pent",
        spelling=spelling,
        include_only_super_tones_and_common_tones=True,
    )

    for tone in tones:
        print(
            f"{tone.note_name:>3} | "
            f"role={tone.role:<10} | "
            f"chord_interval={tone.chord_interval:<4} | "
            f"source={tone.source}"
        )
    print()


def main() -> None:
    # maj7
    print_case("G", "maj7", "B", "sharps")
    print_case("G", "maj7", "F#", "sharps")

    # min7
    print_case("A", "min7", "A", "sharps")
    print_case("A", "min7", "E", "sharps")
    print_case("A", "min7", "B", "sharps")
    print_case("A", "min7", "G", "sharps")

    # dom7
    print_case("D", "dom7", "A", "sharps")
    print_case("D", "dom7", "F", "sharps")


if __name__ == "__main__":
    main()