from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DiagramNote:
    """
    string_index:
        0 = low E
        5 = high E

    fret:
        0 = open string
        1..30 = fretted note
    """
    string_index: int
    fret: int
    role: str
    label: str


@dataclass(frozen=True)
class FretboardDiagram:
    title: str
    notes: list[DiagramNote]


# -----------------------------
# Vertical progression generator
# -----------------------------

@dataclass(frozen=True)
class DiagramTone:
    string_index: int
    fret: int
    role: str
    note_name: str
    chord_interval: str
    source: str
    shape_id: int | None = None


@dataclass(frozen=True)
class HarmonicEvent:
    symbol: str
    root: str
    quality: str
    beats: int
    display_label: str
    section_name: str
    beat_offset_in_bar: int = 0
    super_root: Optional[str] = None


@dataclass(frozen=True)
class SectionProgression:
    name: str
    bars: list[str]


@dataclass(frozen=True)
class ProgressionChart:
    title: str
    key: str
    sections: list[SectionProgression]
    spelling: str = "sharps"
    quality_overrides: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EventRenderCell:
    event: HarmonicEvent
    tones: list[DiagramTone]


@dataclass(frozen=True)
class VerticalDiagramPage:
    title: str
    subtitle: str
    sections: list[tuple[str, list[EventRenderCell]]]