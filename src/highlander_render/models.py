from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


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
class GuardrailEdge:
    """
    A render-ready connection between two classified fretboard nodes.

    color_role:
      rectangle | stack

    side:
      top | bottom

    is_warp:
      True only for the G->B tuning-warp diagonal
    """
    shape_id: int
    color_role: str
    side: str
    is_warp: bool
    start_string_index: int
    start_fret: int
    end_string_index: int
    end_fret: int


@dataclass(frozen=True)
class GuardrailTone:
    """
    A fretboard position classified for the rectangle/stack system.
    This is intentionally separate from DiagramTone so we can build
    scale libraries and guardrail generators without disturbing the
    working progression renderer.
    """
    string_index: int
    fret: int
    note_name: str
    degree_label: str
    memberships: list[GuardrailMembership] = field(default_factory=list)


@dataclass(frozen=True)
class GuardrailEdge:
    """
    A render-ready connection between two classified fretboard nodes.
    color_role:
      rectangle | stack
    """
    shape_id: int
    color_role: str
    start_string_index: int
    start_fret: int
    end_string_index: int
    end_fret: int


@dataclass(frozen=True)
class GuardrailShapeWindow:
    """
    A single shape window in the 5-shape system.
    """
    shape_id: int
    fret_min: int
    fret_max: int
    tones: list[GuardrailTone] = field(default_factory=list)
    edges: list[GuardrailEdge] = field(default_factory=list)


@dataclass(frozen=True)
class ScaleGuardrailDiagram:
    """
    Standalone guardrail-library artifact for one scale/key/system.
    """
    title: str
    key_name: str
    scale_name: str
    root: str
    tones: list[GuardrailTone]
    shape_windows: list[GuardrailShapeWindow] = field(default_factory=list)


class HarmonicEvent:
    """
    Flexible event model so harmony_engine can evolve without constantly
    breaking models.py when new metadata fields are added.

    guardrail_spans:
        Runtime-ready on-string overlay segments:
        {
            string_index: [("red"|"blue", fret_a, fret_b), ...]
        }
    """

    def __init__(
        self,
        symbol: str,
        root: str,
        quality: str,
        beats: int,
        display_label: str,
        section_name: str,
        beat_offset_in_bar: int = 0,
        super_root: Optional[str] = None,
        guardrail_spans: Optional[dict[int, list[tuple[str, int, int]]]] = None,
        **extra_fields: Any,
    ) -> None:
        self.symbol = symbol
        self.root = root
        self.quality = quality
        self.beats = beats
        self.display_label = display_label
        self.section_name = section_name
        self.beat_offset_in_bar = beat_offset_in_bar
        self.super_root = super_root
        self.guardrail_spans = guardrail_spans or {}

        for key, value in extra_fields.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        core = (
            f"symbol={self.symbol!r}, "
            f"root={self.root!r}, "
            f"quality={self.quality!r}, "
            f"beats={self.beats!r}, "
            f"display_label={self.display_label!r}, "
            f"section_name={self.section_name!r}, "
            f"beat_offset_in_bar={self.beat_offset_in_bar!r}, "
            f"super_root={self.super_root!r}, "
            f"guardrail_spans={self.guardrail_spans!r}"
        )
        extras = [
            f"{k}={v!r}"
            for k, v in self.__dict__.items()
            if k
            not in {
                "symbol",
                "root",
                "quality",
                "beats",
                "display_label",
                "section_name",
                "beat_offset_in_bar",
                "super_root",
                "guardrail_spans",
            }
        ]
        if extras:
            return f"HarmonicEvent({core}, {', '.join(extras)})"
        return f"HarmonicEvent({core})"


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