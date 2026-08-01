from __future__ import annotations

from dataclasses import dataclass

from .config import NUM_STRINGS, TUNING_BOTTOM_TO_TOP
from .scale_library import ScaleRecipe, get_scale_recipe, recipe_to_semitones


CHROMATIC_SHARPS = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
CHROMATIC_FLATS = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")

TUNING_PITCH_CLASSES = {
    "E": 4,
    "A": 9,
    "D": 2,
    "G": 7,
    "B": 11,
}


@dataclass(frozen=True)
class ScaleTone:
    interval: str
    note_name: str
    pitch_class: int
    sequence_index: int


@dataclass(frozen=True)
class FretboardHit:
    string_index: int
    fret: int
    interval: str
    note_name: str
    pitch_class: int
    sequence_index: int


@dataclass(frozen=True)
class StringSpan:
    string_index: int
    fret_a: int
    fret_b: int
    pitch_a: int
    pitch_b: int
    interval_a: str
    interval_b: str
    distance: int


def normalize_note_name(note: str) -> str:
    note = note.strip().replace("♭", "b").replace("♯", "#")

    if not note:
        raise ValueError("Empty note name")

    if len(note) == 1:
        return note.upper()

    return note[0].upper() + note[1:]


def note_to_pitch_class(note: str) -> int:
    note = normalize_note_name(note)

    if note in CHROMATIC_SHARPS:
        return CHROMATIC_SHARPS.index(note)

    if note in CHROMATIC_FLATS:
        return CHROMATIC_FLATS.index(note)

    raise ValueError(f"Unsupported note name: {note}")


def pitch_class_to_note(pitch_class: int, spelling: str = "sharps") -> str:
    names = CHROMATIC_FLATS if spelling == "flats" else CHROMATIC_SHARPS
    return names[pitch_class % 12]


def build_scale_tones(
    root: str,
    recipe: ScaleRecipe | str,
    spelling: str = "sharps",
) -> list[ScaleTone]:
    if isinstance(recipe, str):
        recipe = get_scale_recipe(recipe)

    root_pc = note_to_pitch_class(root)
    semitones = recipe_to_semitones(recipe)

    tones: list[ScaleTone] = []
    for sequence_index, (interval, semitone) in enumerate(
        zip(recipe.intervals, semitones)
    ):
        pitch_class = (root_pc + semitone) % 12
        tones.append(
            ScaleTone(
                interval=interval,
                note_name=pitch_class_to_note(pitch_class, spelling),
                pitch_class=pitch_class,
                sequence_index=sequence_index,
            )
        )

    return tones


def iter_fretboard_hits_for_pitch_class(
    pitch_class: int,
    max_fret: int,
) -> list[tuple[int, int]]:
    hits: list[tuple[int, int]] = []

    for string_index, open_name in enumerate(TUNING_BOTTOM_TO_TOP):
        open_pc = TUNING_PITCH_CLASSES[open_name]

        for fret in range(max_fret + 1):
            if (open_pc + fret) % 12 == pitch_class:
                hits.append((string_index, fret))

    return hits


def build_scale_fretboard_hits(
    root: str,
    recipe: ScaleRecipe | str,
    spelling: str = "sharps",
    max_fret: int = 15,
) -> list[FretboardHit]:
    tones = build_scale_tones(root, recipe, spelling=spelling)
    hits: list[FretboardHit] = []

    for tone in tones:
        for string_index, fret in iter_fretboard_hits_for_pitch_class(
            tone.pitch_class,
            max_fret=max_fret,
        ):
            hits.append(
                FretboardHit(
                    string_index=string_index,
                    fret=fret,
                    interval=tone.interval,
                    note_name=tone.note_name,
                    pitch_class=tone.pitch_class,
                    sequence_index=tone.sequence_index,
                )
            )

    hits.sort(key=lambda hit: (hit.string_index, hit.fret, hit.sequence_index))
    return hits


def build_scale_positions_by_string(
    root: str,
    recipe: ScaleRecipe | str,
    spelling: str = "sharps",
    max_fret: int = 15,
) -> dict[int, list[FretboardHit]]:
    by_string: dict[int, list[FretboardHit]] = {s: [] for s in range(NUM_STRINGS)}

    for hit in build_scale_fretboard_hits(
        root=root,
        recipe=recipe,
        spelling=spelling,
        max_fret=max_fret,
    ):
        by_string[hit.string_index].append(hit)

    for string_index in by_string:
        by_string[string_index].sort(key=lambda hit: hit.fret)

    return by_string


def build_adjacent_string_spans(
    root: str,
    recipe: ScaleRecipe | str,
    spelling: str = "sharps",
    max_fret: int = 15,
) -> dict[int, list[StringSpan]]:
    """
    Consecutive scale-note spans on each string.

    For minor pentatonic, distance usually classifies:
        3 frets = rectangle/red
        2 frets = stack/blue
        4 frets = omitted center stack gap / no rail
    """
    by_string = build_scale_positions_by_string(
        root=root,
        recipe=recipe,
        spelling=spelling,
        max_fret=max_fret,
    )

    spans: dict[int, list[StringSpan]] = {s: [] for s in range(NUM_STRINGS)}

    for string_index, hits in by_string.items():
        for left, right in zip(hits, hits[1:]):
            spans[string_index].append(
                StringSpan(
                    string_index=string_index,
                    fret_a=left.fret,
                    fret_b=right.fret,
                    pitch_a=left.pitch_class,
                    pitch_b=right.pitch_class,
                    interval_a=left.interval,
                    interval_b=right.interval,
                    distance=right.fret - left.fret,
                )
            )

    return spans