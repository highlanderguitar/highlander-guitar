from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DiagramToneSpec:
    string_index: int
    fret: int
    note_name: str
    degree_label: str
    sequence_index: int
    node_kind: str
    is_structural: bool = False


@dataclass(frozen=True)
class DiagramEdgeSpec:
    start_string_index: int
    start_fret: int
    end_string_index: int
    end_fret: int
    color_role: str
    side: str = "horizontal"
    is_warp: bool = False


@dataclass(frozen=True)
class DiagramShapeWindowSpec:
    shape_id: int
    fret_min: int
    fret_max: int
    low_string_index: int
    high_string_index: int
    low_left_fret: int
    low_right_fret: int
    high_left_fret: int
    high_right_fret: int
    tones: list[DiagramToneSpec] = field(default_factory=list)
    edges: list[DiagramEdgeSpec] = field(default_factory=list)


@dataclass(frozen=True)
class DiagramSpec:
    diagram_id: str
    title: str
    diagram_type: str

    super_root: str
    chord_root: str
    chord_quality: str

    tones: list[DiagramToneSpec]
    shape_windows: list[DiagramShapeWindowSpec]

    metadata: dict[str, Any] = field(default_factory=dict)