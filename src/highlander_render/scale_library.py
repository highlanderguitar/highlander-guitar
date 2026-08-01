from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


IntervalName = Literal[
    "1",
    "b2",
    "2",
    "#2",
    "b3",
    "3",
    "4",
    "#4",
    "b5",
    "5",
    "#5",
    "b6",
    "6",
    "bb7",
    "b7",
    "7",
]


INTERVAL_TO_SEMITONES: dict[str, int] = {
    "1": 0,
    "b2": 1,
    "2": 2,
    "#2": 3,
    "b3": 3,
    "3": 4,
    "4": 5,
    "#4": 6,
    "b5": 6,
    "5": 7,
    "#5": 8,
    "b6": 8,
    "6": 9,
    "bb7": 9,
    "b7": 10,
    "7": 11,
}


@dataclass(frozen=True)
class ScaleRecipe:
    name: str
    short_name: str
    intervals: tuple[str, ...]
    family: str = "general"


SCALE_LIBRARY: dict[str, ScaleRecipe] = {
    "minor_pentatonic": ScaleRecipe(
        name="Minor Pentatonic",
        short_name="min pent",
        intervals=("1", "b3", "4", "5", "b7"),
        family="pentatonic",
    ),
    "major_pentatonic": ScaleRecipe(
        name="Major Pentatonic",
        short_name="maj pent",
        intervals=("1", "2", "3", "5", "6"),
        family="pentatonic",
    ),
    "major": ScaleRecipe(
        name="Major Scale / Ionian",
        short_name="major",
        intervals=("1", "2", "3", "4", "5", "6", "7"),
        family="major_modes",
    ),
    "ionian": ScaleRecipe(
        name="Ionian",
        short_name="ionian",
        intervals=("1", "2", "3", "4", "5", "6", "7"),
        family="major_modes",
    ),
    "dorian": ScaleRecipe(
        name="Dorian",
        short_name="dorian",
        intervals=("1", "2", "b3", "4", "5", "6", "b7"),
        family="major_modes",
    ),
    "phrygian": ScaleRecipe(
        name="Phrygian",
        short_name="phrygian",
        intervals=("1", "b2", "b3", "4", "5", "b6", "b7"),
        family="major_modes",
    ),
    "lydian": ScaleRecipe(
        name="Lydian",
        short_name="lydian",
        intervals=("1", "2", "3", "#4", "5", "6", "7"),
        family="major_modes",
    ),
    "mixolydian": ScaleRecipe(
        name="Mixolydian",
        short_name="mixolydian",
        intervals=("1", "2", "3", "4", "5", "6", "b7"),
        family="major_modes",
    ),
    "aeolian": ScaleRecipe(
        name="Aeolian / Natural Minor",
        short_name="aeolian",
        intervals=("1", "2", "b3", "4", "5", "b6", "b7"),
        family="major_modes",
    ),
    "natural_minor": ScaleRecipe(
        name="Natural Minor / Aeolian",
        short_name="nat minor",
        intervals=("1", "2", "b3", "4", "5", "b6", "b7"),
        family="major_modes",
    ),
    "locrian": ScaleRecipe(
        name="Locrian",
        short_name="locrian",
        intervals=("1", "b2", "b3", "4", "b5", "b6", "b7"),
        family="major_modes",
    ),
    "whole_tone": ScaleRecipe(
        name="Whole Tone",
        short_name="whole tone",
        intervals=("1", "2", "3", "#4", "#5", "b7"),
        family="symmetric",
    ),
    "altered": ScaleRecipe(
        name="Altered / Super Locrian",
        short_name="altered",
        intervals=("1", "b2", "#2", "3", "b5", "#5", "b7"),
        family="melodic_minor_modes",
    ),
}


ALIASES: dict[str, str] = {
    "min_pent": "minor_pentatonic",
    "minor_pent": "minor_pentatonic",
    "minor pentatonic": "minor_pentatonic",
    "minor pent": "minor_pentatonic",
    "maj_pent": "major_pentatonic",
    "major_pent": "major_pentatonic",
    "major pentatonic": "major_pentatonic",
    "major pent": "major_pentatonic",
    "ionian_mode": "ionian",
    "major_scale": "major",
    "natural minor": "natural_minor",
    "nat_minor": "natural_minor",
    "super_locrian": "altered",
    "super locrian": "altered",
}


def normalize_scale_key(scale_name: str) -> str:
    key = scale_name.strip().lower().replace("-", "_").replace(" ", "_")
    alias_key = scale_name.strip().lower()
    return ALIASES.get(alias_key, ALIASES.get(key, key))


def get_scale_recipe(scale_name: str) -> ScaleRecipe:
    key = normalize_scale_key(scale_name)

    if key not in SCALE_LIBRARY:
        supported = ", ".join(sorted(SCALE_LIBRARY))
        raise ValueError(f"Unknown scale recipe '{scale_name}'. Supported: {supported}")

    return SCALE_LIBRARY[key]


def interval_to_semitones(interval: str) -> int:
    if interval not in INTERVAL_TO_SEMITONES:
        raise ValueError(f"Unsupported interval: {interval}")
    return INTERVAL_TO_SEMITONES[interval]


def recipe_to_semitones(recipe: ScaleRecipe) -> tuple[int, ...]:
    return tuple(interval_to_semitones(interval) for interval in recipe.intervals)