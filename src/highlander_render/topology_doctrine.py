from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .harmony_engine import INTERVAL_TO_SEMITONES, TUNING_BOTTOM_TO_TOP, TUNING_PITCHES, note_to_index


DEFAULT_DOCTRINE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "minor_pent_guardrail_doctrine.yaml"


@dataclass(frozen=True)
class Doctrine:
    data: dict[str, Any]

    @property
    def degree_semitones(self) -> dict[str, int]:
        return {degree: int(semitone) for degree, semitone in self.data["degree_semitones"].items()}

    @property
    def corridors_by_id(self) -> dict[str, dict[str, Any]]:
        return {corridor["id"]: corridor for corridor in self.data["corridors"]}

    @property
    def corridors_by_degrees(self) -> dict[tuple[str, str], dict[str, Any]]:
        return {
            (corridor["from_degree"], corridor["to_degree"]): corridor
            for corridor in self.data["corridors"]
        }

    @property
    def shared_degree_pairs(self) -> dict[tuple[str, str], dict[str, Any]]:
        return {
            degree_pair_key(edge["degree_pair"]): edge
            for edge in self.data.get("shared_edges", [])
        }

    @property
    def allowed_non_scale_segments(self) -> list[dict[str, Any]]:
        return list(self.data.get("allowed_non_scale_segments", []))


def load_doctrine(path: Path = DEFAULT_DOCTRINE_PATH) -> Doctrine:
    """
    Load the doctrine fixture.

    The fixture uses a YAML-compatible JSON subset so validation stays stdlib-only.
    """
    return Doctrine(json.loads(path.read_text(encoding="utf-8")))


def degree_pair_key(degrees: list[str] | tuple[str, str]) -> tuple[str, str]:
    return tuple(sorted((degrees[0], degrees[1])))


def pitch_class_to_degree_map(root: str, doctrine: Doctrine) -> dict[int, str]:
    root_pc = note_to_index(root)
    return {
        (root_pc + semitone) % 12: degree
        for degree, semitone in doctrine.degree_semitones.items()
    }


def pitch_class_for_position(string_index: int, fret: int) -> int:
    open_name = TUNING_BOTTOM_TO_TOP[string_index]
    return (TUNING_PITCHES[open_name] + fret) % 12


def degree_for_position(
    string_index: int,
    fret: int,
    pc_to_degree: dict[int, str],
) -> str:
    return pc_to_degree.get(pitch_class_for_position(string_index, fret), "non_scale")


def corridor_id_for_degrees(from_degree: str, to_degree: str) -> str:
    return f"minor_pent:{from_degree}->{to_degree}"


def expected_minor_pent_corridor_sequence(doctrine: Doctrine) -> list[tuple[str, str]]:
    degrees = list(doctrine.data["degrees"])
    return list(zip(degrees, [*degrees[1:], degrees[0]]))


def expected_pitch_class_for_degree(root: str, degree: str) -> int:
    return (note_to_index(root) + INTERVAL_TO_SEMITONES[degree]) % 12
