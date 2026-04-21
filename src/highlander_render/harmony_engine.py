from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .models import (
    DiagramTone,
    GuardrailEdge,
    GuardrailMembership,
    GuardrailShapeWindow,
    GuardrailTone,
    HarmonicEvent,
    ProgressionChart,
    ScaleGuardrailDiagram,
)

NoteSpelling = Literal["sharps", "flats"]

CHROMATIC_SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
CHROMATIC_FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

INTERVAL_TO_SEMITONES = {
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

CHORD_QUALITY_INTERVALS = {
    "maj7": ["1", "3", "5", "7"],
    "min7": ["1", "b3", "5", "b7"],
    "dom7": ["1", "3", "5", "b7"],
}

TUNING_PITCHES = {
    "E": 4,
    "A": 9,
    "D": 2,
    "G": 7,
    "B": 11,
}

TUNING_BOTTOM_TO_TOP = ["E", "A", "D", "G", "B", "E"]

PINK_SYSTEM_BY_QUALITY = {
    "min7": "2",
    "maj7": "3",
    "dom7": "5",
}

EFFECT_FAMILY_MAP = {
    ("maj7", 4): "three_minor_pent_over_major",
    ("maj7", 11): "seven_minor_pent_over_major",
    ("min7", 0): "one_minor_pent_over_minor",
    ("min7", 7): "five_minor_pent_over_minor",
    ("min7", 2): "two_minor_pent_over_minor",
    ("min7", 10): "flat_seven_minor_pent_over_minor",
    ("dom7", 7): "five_minor_pent_over_dominant",
    ("dom7", 3): "flat_three_minor_pent_over_dominant",
}

EFFECT_METADATA = {
    "three_minor_pent_over_major": {
        "musical_color": "inside_major",
        "teaching_name": "Inside Major Sound",
        "priority_rank": 1,
    },
    "seven_minor_pent_over_major": {
        "musical_color": "lydian_bright",
        "teaching_name": 'Bright "Lydian" Sound',
        "priority_rank": 2,
    },
    "one_minor_pent_over_minor": {
        "musical_color": "minor_home",
        "teaching_name": "Home Minor Sound",
        "priority_rank": 1,
    },
    "five_minor_pent_over_minor": {
        "musical_color": "minor_open",
        "teaching_name": "Open Minor Sound",
        "priority_rank": 1,
    },
    "two_minor_pent_over_minor": {
        "musical_color": "dorian_bright",
        "teaching_name": 'Bright "Dorian" Sound',
        "priority_rank": 2,
    },
    "flat_seven_minor_pent_over_minor": {
        "musical_color": "phrygian_dark",
        "teaching_name": 'Dark "Phrygian" Sound',
        "priority_rank": 3,
    },
    "five_minor_pent_over_dominant": {
        "musical_color": "mixolydian_inside",
        "teaching_name": "Inside Dominant Sound",
        "priority_rank": 1,
    },
    "flat_three_minor_pent_over_dominant": {
        "musical_color": "altered_tension",
        "teaching_name": "Altered Dominant Sound",
        "priority_rank": 2,
    },
}

MINOR_PENT_INTERVALS = ["1", "b3", "4", "5", "b7"]

# 5-shape windows for now.
# These are retrieval / masking windows, not the doctrine itself.
SHAPE_WINDOWS = {
    1: (0, 2),
    2: (3, 5),
    3: (6, 8),
    4: (9, 11),
    5: (12, 15),
}


@dataclass(frozen=True)
class ClassifiedTone:
    note_name: str
    role: str
    chord_interval: str
    source: str
    semitone: int


@dataclass(frozen=True)
class EffectProfile:
    effect_family: str
    musical_color: str
    teaching_name: str
    priority_rank: int


def normalize_note_name(note: str) -> str:
    note = note.strip().replace("♭", "b").replace("♯", "#")
    if not note:
        raise ValueError("Empty note name")
    if len(note) == 1:
        return note.upper()
    return note[0].upper() + note[1:]


def chromatic_for_spelling(spelling: NoteSpelling) -> list[str]:
    return CHROMATIC_FLATS if spelling == "flats" else CHROMATIC_SHARPS


def note_to_index(note: str) -> int:
    note = normalize_note_name(note)
    if note in CHROMATIC_SHARPS:
        return CHROMATIC_SHARPS.index(note)
    if note in CHROMATIC_FLATS:
        return CHROMATIC_FLATS.index(note)
    raise ValueError(f"Unsupported note: {note}")


def index_to_note(index: int, spelling: NoteSpelling = "sharps") -> str:
    return chromatic_for_spelling(spelling)[index % 12]


def semitone_to_chord_interval(semitone_distance: int) -> str:
    mapping = {
        0: "1",
        1: "b2/b9",
        2: "2/9",
        3: "#2/#9",
        4: "3",
        5: "4/11",
        6: "#4/#11",
        7: "5",
        8: "b6/b13",
        9: "6/13",
        10: "b7",
        11: "7",
    }
    return mapping[semitone_distance % 12]


def classify_chord_role(interval_label: str) -> str:
    if interval_label == "1":
        return "root"
    if interval_label in {"b3", "3"}:
        return "third"
    if interval_label in {"b5", "5", "#5"}:
        return "fifth"
    if interval_label in {"bb7", "b7", "7"}:
        return "seventh"
    return "extension"


def build_tones_from_intervals(
    root: str,
    intervals: list[str],
    spelling: NoteSpelling = "sharps",
) -> list[tuple[str, str, int]]:
    root_idx = note_to_index(root)
    tones: list[tuple[str, str, int]] = []
    for interval_label in intervals:
        semitones = INTERVAL_TO_SEMITONES[interval_label]
        note_name = index_to_note(root_idx + semitones, spelling)
        tones.append((note_name, interval_label, (root_idx + semitones) % 12))
    return tones


def get_chord_tones(
    root: str,
    quality: str,
    spelling: NoteSpelling = "sharps",
) -> list[ClassifiedTone]:
    raw = build_tones_from_intervals(root, CHORD_QUALITY_INTERVALS[quality], spelling)
    return [
        ClassifiedTone(
            note_name=note_name,
            role=classify_chord_role(interval_label),
            chord_interval=interval_label,
            source="chord",
            semitone=semitone,
        )
        for note_name, interval_label, semitone in raw
    ]


def get_minor_pent_tones(
    super_root: str,
    chord_root: str,
    spelling: NoteSpelling = "sharps",
) -> list[ClassifiedTone]:
    raw = build_tones_from_intervals(super_root, MINOR_PENT_INTERVALS, spelling)
    chord_root_idx = note_to_index(chord_root)

    tones: list[ClassifiedTone] = []
    for note_name, _, semitone in raw:
        dist = (semitone - chord_root_idx) % 12
        tones.append(
            ClassifiedTone(
                note_name=note_name,
                role="super_tone",
                chord_interval=semitone_to_chord_interval(dist),
                source="super",
                semitone=semitone,
            )
        )
    return tones


def combine_chord_and_super_tones(
    chord_root: str,
    chord_quality: str,
    super_root: str,
    spelling: NoteSpelling = "sharps",
) -> list[ClassifiedTone]:
    """
    Pink Panther mode:
    - start from pentatonic tones only
    - if a pent tone is also a chord tone, keep the chord-tone role/color
    - do NOT include extra chord-only tones
    """
    chord_tones = get_chord_tones(chord_root, chord_quality, spelling)
    super_tones = get_minor_pent_tones(super_root, chord_root, spelling)

    chord_map = {t.semitone: t for t in chord_tones}

    result: list[ClassifiedTone] = []
    for t in super_tones:
        if t.semitone in chord_map:
            result.append(chord_map[t.semitone])
        else:
            result.append(t)
    return result


def build_minor_pent_cycle(root: str, spelling: NoteSpelling = "sharps") -> list[str]:
    return [
        index_to_note(note_to_index(root) + INTERVAL_TO_SEMITONES[i], spelling)
        for i in MINOR_PENT_INTERVALS
    ]


def build_pent_index_map(root: str, spelling: NoteSpelling = "sharps") -> dict[str, int]:
    cycle = build_minor_pent_cycle(root, spelling)
    return {note: i for i, note in enumerate(cycle)}


def parse_root(symbol: str) -> str:
    m = re.match(r"^([A-Ga-g](?:#|b)?)", symbol.strip())
    if not m:
        raise ValueError(f"Could not parse root from chord symbol: {symbol}")
    return normalize_note_name(m.group(1))


def chord_symbol_to_quality(
    symbol: str,
    quality_overrides: dict[str, str] | None = None,
) -> tuple[str, str, str]:
    symbol = symbol.strip()

    if quality_overrides and symbol in quality_overrides:
        root = parse_root(symbol)
        quality = quality_overrides[symbol]
        return symbol, root, quality

    m = re.match(r"^([A-Ga-g](?:#|b)?)(.*)$", symbol)
    if not m:
        raise ValueError(f"Could not parse chord symbol: {symbol}")

    root = normalize_note_name(m.group(1))
    suffix = m.group(2).strip()

    if suffix in {"", "maj7"}:
        quality = "maj7"
    elif suffix in {"m", "m7", "min", "min7", "-7"}:
        quality = "min7"
    elif suffix in {"7", "dom7"}:
        quality = "dom7"
    else:
        raise ValueError(
            f'Unsupported chord suffix "{suffix}" for symbol "{symbol}". '
            "Use explicit maj7, m7, or 7, or provide a quality override."
        )

    return symbol, root, quality


def interval_above(
    root: str,
    interval: str,
    spelling: NoteSpelling = "sharps",
) -> str:
    return index_to_note(note_to_index(root) + INTERVAL_TO_SEMITONES[interval], spelling)


def default_super_root(
    chord_root: str,
    chord_quality: str,
    spelling: NoteSpelling = "sharps",
) -> str:
    return interval_above(chord_root, PINK_SYSTEM_BY_QUALITY[chord_quality], spelling)


def build_effect_family(
    chord_root: str,
    chord_quality: str,
    super_root: str,
) -> str:
    chord_idx = note_to_index(chord_root)
    super_idx = note_to_index(super_root)
    offset = (super_idx - chord_idx) % 12
    return EFFECT_FAMILY_MAP.get((chord_quality, offset), "unmapped")


def build_instance_name(
    chord_root: str,
    chord_quality: str,
    super_root: str,
) -> str:
    return f"{super_root}m_pent_over_{chord_root}{chord_quality}"


def get_effect_metadata(effect_family: str) -> EffectProfile:
    data = EFFECT_METADATA.get(
        effect_family,
        {
            "musical_color": "unknown",
            "teaching_name": "Unknown",
            "priority_rank": 99,
        },
    )
    return EffectProfile(
        effect_family=effect_family,
        musical_color=data["musical_color"],
        teaching_name=data["teaching_name"],
        priority_rank=data["priority_rank"],
    )


def build_effect_profile(
    chord_root: str,
    chord_quality: str,
    super_root: str,
) -> EffectProfile:
    effect_family = build_effect_family(chord_root, chord_quality, super_root)
    return get_effect_metadata(effect_family)


def parse_bar(bar_text: str) -> list[tuple[str, int]]:
    bar_text = bar_text.strip()
    if not bar_text:
        return []

    pattern = re.compile(r"([A-Ga-g](?:#|b)?(?:\([^)]*\)|[^-|\s])*)(-*)")
    events: list[tuple[str, int]] = []

    pos = 0
    while pos < len(bar_text):
        if bar_text[pos].isspace():
            pos += 1
            continue

        match = pattern.match(bar_text, pos)
        if not match:
            raise ValueError(f"Invalid bar fragment: {bar_text}")

        symbol = match.group(1).strip()
        dashes = match.group(2)
        beats = 1 + len(dashes)
        events.append((symbol, beats))
        pos = match.end()

    total_beats = sum(beats for _, beats in events)
    if total_beats != 4:
        raise ValueError(f"Bar must total 4 beats, got {total_beats}: {bar_text}")

    return events


def expand_chart_to_events(chart: ProgressionChart) -> list[HarmonicEvent]:
    all_events: list[HarmonicEvent] = []

    for section in chart.sections:
        for bar in section.bars:
            beat_offset = 0
            for symbol, beats in parse_bar(bar):
                display_symbol, root, quality = chord_symbol_to_quality(
                    symbol,
                    chart.quality_overrides,
                )
                super_root = default_super_root(root, quality, chart.spelling)
                effect_profile = build_effect_profile(root, quality, super_root)

                all_events.append(
                    HarmonicEvent(
                        symbol=display_symbol,
                        root=root,
                        quality=quality,
                        beats=beats,
                        display_label=display_symbol,
                        section_name=section.name,
                        beat_offset_in_bar=beat_offset,
                        super_root=super_root,
                        effect_family=effect_profile.effect_family,
                        musical_color=effect_profile.musical_color,
                        teaching_name=effect_profile.teaching_name,
                        priority_rank=effect_profile.priority_rank,
                    )
                )
                beat_offset += beats

    return all_events


def iter_fretboard_positions_for_pitch_class(
    semitone: int,
    max_fret: int = 15,
) -> list[tuple[int, int]]:
    positions: list[tuple[int, int]] = []
    for string_index, open_name in enumerate(TUNING_BOTTOM_TO_TOP):
        open_pitch = TUNING_PITCHES[open_name]
        for fret in range(0, max_fret + 1):
            if (open_pitch + fret) % 12 == semitone:
                positions.append((string_index, fret))
    return positions


def assign_pentatonic_shape(fret: int) -> int:
    for shape_id, (fret_min, fret_max) in SHAPE_WINDOWS.items():
        if fret_min <= fret <= fret_max:
            return shape_id
    return 5


def build_diagram_tones_for_event(
    event: HarmonicEvent,
    include_pink: bool,
    spelling: NoteSpelling = "sharps",
    max_fret: int = 15,
) -> list[DiagramTone]:
    classified = (
        combine_chord_and_super_tones(
            event.root,
            event.quality,
            event.super_root or default_super_root(event.root, event.quality, spelling),
            spelling,
        )
        if include_pink
        else get_chord_tones(event.root, event.quality, spelling)
    )

    tones: list[DiagramTone] = []
    for tone in classified:
        for string_index, fret in iter_fretboard_positions_for_pitch_class(
            tone.semitone,
            max_fret=max_fret,
        ):
            tones.append(
                DiagramTone(
                    string_index=string_index,
                    fret=fret,
                    role=tone.role,
                    note_name=tone.note_name,
                    chord_interval=tone.chord_interval,
                    source=tone.source,
                    shape_id=assign_pentatonic_shape(fret) if include_pink else None,
                )
            )

    return tones


# ============================================================
# Guardrail library generation
# ============================================================

def degree_label_in_minor_pent(root: str, note_name: str, spelling: NoteSpelling = "sharps") -> str:
    root_idx = note_to_index(root)
    note_idx = note_to_index(note_name)
    return semitone_to_chord_interval((note_idx - root_idx) % 12)


def build_minor_pent_position_map(
    root: str,
    spelling: NoteSpelling = "sharps",
    max_fret: int = 15,
) -> list[tuple[int, int, str, str]]:
    """
    Returns all fretboard positions for the scale:
      (string_index, fret, note_name, degree_label)
    """
    result: list[tuple[int, int, str, str]] = []
    cycle = build_minor_pent_cycle(root, spelling)
    for note_name in cycle:
        degree_label = degree_label_in_minor_pent(root, note_name, spelling)
        for string_index, fret in iter_fretboard_positions_for_pitch_class(
            note_to_index(note_name),
            max_fret=max_fret,
        ):
            result.append((string_index, fret, note_name, degree_label))
    result.sort(key=lambda x: (x[1], x[0], x[2]))
    return result


def _first_two_frets_for_string_in_shape(
    positions: list[tuple[int, int, str, str]],
    string_index: int,
    shape_id: int,
) -> list[tuple[int, int, str, str]]:
    fret_min, fret_max = SHAPE_WINDOWS[shape_id]
    matches = [
        p for p in positions
        if p[0] == string_index and fret_min <= p[1] <= fret_max
    ]
    # unique frets only, preserve order
    seen: set[int] = set()
    filtered: list[tuple[int, int, str, str]] = []
    for p in matches:
        if p[1] in seen:
            continue
        seen.add(p[1])
        filtered.append(p)
    return filtered[:2]


def _membership_label(family: str, shape_id: int) -> str:
    return f"{family}{shape_id}"


def build_minor_pent_guardrail_tones(
    root: str,
    spelling: NoteSpelling = "sharps",
    max_fret: int = 15,
) -> list[GuardrailTone]:
    """
    First-pass classification layer:
    - rectangle = odd string-pairs inside each shape window
    - stack     = even string-pairs inside each shape window

    This gives us machine-usable memberships like:
      rectangle1, stack1, both1, rectangle2, ...
    without touching the progression renderer yet.
    """
    positions = build_minor_pent_position_map(root, spelling, max_fret=max_fret)

    membership_map: dict[tuple[int, int], list[GuardrailMembership]] = {}
    note_meta: dict[tuple[int, int], tuple[str, str]] = {}

    for string_index, fret, note_name, degree_label in positions:
        note_meta[(string_index, fret)] = (note_name, degree_label)

    for shape_id in sorted(SHAPE_WINDOWS.keys()):
        per_string = {
            s: _first_two_frets_for_string_in_shape(positions, s, shape_id)
            for s in range(6)
        }

        # Rectangle families: 3x2, using string pairs (0,1), (2,3), (4,5)
        for s1, s2 in ((0, 1), (2, 3), (4, 5)):
            if len(per_string[s1]) >= 2 and len(per_string[s2]) >= 2:
                for ordinal, tone in enumerate(per_string[s1][:2], start=1):
                    key = (tone[0], tone[1])
                    membership_map.setdefault(key, []).append(
                        GuardrailMembership(
                            shape_id=shape_id,
                            family="rectangle",
                            label=_membership_label("rectangle", shape_id),
                            ordinal_on_string=ordinal,
                        )
                    )
                for ordinal, tone in enumerate(per_string[s2][:2], start=1):
                    key = (tone[0], tone[1])
                    membership_map.setdefault(key, []).append(
                        GuardrailMembership(
                            shape_id=shape_id,
                            family="rectangle",
                            label=_membership_label("rectangle", shape_id),
                            ordinal_on_string=ordinal,
                        )
                    )

        # Stack families: 2x3, using overlapping string pairs
        for s1, s2 in ((1, 2), (2, 3), (3, 4), (4, 5), (0, 1)):
            if len(per_string[s1]) >= 2 and len(per_string[s2]) >= 2:
                for ordinal, tone in enumerate(per_string[s1][:2], start=1):
                    key = (tone[0], tone[1])
                    membership_map.setdefault(key, []).append(
                        GuardrailMembership(
                            shape_id=shape_id,
                            family="stack",
                            label=_membership_label("stack", shape_id),
                            ordinal_on_string=ordinal,
                        )
                    )
                for ordinal, tone in enumerate(per_string[s2][:2], start=1):
                    key = (tone[0], tone[1])
                    membership_map.setdefault(key, []).append(
                        GuardrailMembership(
                            shape_id=shape_id,
                            family="stack",
                            label=_membership_label("stack", shape_id),
                            ordinal_on_string=ordinal,
                        )
                    )

    guardrail_tones: list[GuardrailTone] = []
    for (string_index, fret), memberships in sorted(membership_map.items(), key=lambda x: (x[0][1], x[0][0])):
        note_name, degree_label = note_meta[(string_index, fret)]

        families = {m.family for m in memberships}
        final_memberships: list[GuardrailMembership] = []

        # Preserve the detailed memberships
        final_memberships.extend(memberships)

        # Add "both{shape}" when both rectangle and stack occur in same shape
        for shape_id in sorted({m.shape_id for m in memberships}):
            shape_families = {m.family for m in memberships if m.shape_id == shape_id}
            if "rectangle" in shape_families and "stack" in shape_families:
                final_memberships.append(
                    GuardrailMembership(
                        shape_id=shape_id,
                        family="both",
                        label=_membership_label("both", shape_id),
                        ordinal_on_string=0,
                    )
                )

        guardrail_tones.append(
            GuardrailTone(
                string_index=string_index,
                fret=fret,
                note_name=note_name,
                degree_label=degree_label,
                memberships=sorted(
                    final_memberships,
                    key=lambda m: (m.shape_id, m.family, m.ordinal_on_string),
                ),
            )
        )

    return guardrail_tones


def build_minor_pent_guardrail_edges(
    tones: list[GuardrailTone],
) -> list[GuardrailEdge]:
    """
    First-pass render edges:
    - rectangle edges connect same-family notes across adjacent strings
    - stack edges connect same-family notes up the string pair ladder

    This is intentionally simple and diagnostic.
    """
    by_shape_family: dict[tuple[int, str], list[GuardrailTone]] = {}
    for tone in tones:
        for membership in tone.memberships:
            if membership.family not in {"rectangle", "stack"}:
                continue
            by_shape_family.setdefault((membership.shape_id, membership.family), []).append(tone)

    edges: list[GuardrailEdge] = []

    for (shape_id, family), members in by_shape_family.items():
        members = sorted(members, key=lambda t: (t.string_index, t.fret))

        # connect nearest same-ordinal neighbors across adjacent strings
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                if abs(a.string_index - b.string_index) != 1:
                    continue
                if abs(a.fret - b.fret) > 3:
                    continue

                edges.append(
                    GuardrailEdge(
                        shape_id=shape_id,
                        color_role=family,
                        start_string_index=a.string_index,
                        start_fret=a.fret,
                        end_string_index=b.string_index,
                        end_fret=b.fret,
                    )
                )

    # de-dupe
    seen: set[tuple[int, str, int, int, int, int]] = set()
    deduped: list[GuardrailEdge] = []
    for e in edges:
        key = (
            e.shape_id,
            e.color_role,
            min(e.start_string_index, e.end_string_index),
            min(e.start_fret, e.end_fret),
            max(e.start_string_index, e.end_string_index),
            max(e.start_fret, e.end_fret),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(e)

    return deduped


def build_minor_pent_guardrail_windows(
    root: str,
    spelling: NoteSpelling = "sharps",
    max_fret: int = 15,
) -> list[GuardrailShapeWindow]:
    tones = build_minor_pent_guardrail_tones(root, spelling=spelling, max_fret=max_fret)
    edges = build_minor_pent_guardrail_edges(tones)

    windows: list[GuardrailShapeWindow] = []
    for shape_id, (fret_min, fret_max) in SHAPE_WINDOWS.items():
        window_tones = [
            t for t in tones
            if any(m.shape_id == shape_id for m in t.memberships)
        ]
        window_edges = [e for e in edges if e.shape_id == shape_id]
        windows.append(
            GuardrailShapeWindow(
                shape_id=shape_id,
                fret_min=fret_min,
                fret_max=fret_max,
                tones=window_tones,
                edges=window_edges,
            )
        )
    return windows


def build_minor_pent_guardrail_diagram(
    root: str,
    spelling: NoteSpelling = "sharps",
    max_fret: int = 15,
) -> ScaleGuardrailDiagram:
    tones = build_minor_pent_guardrail_tones(root, spelling=spelling, max_fret=max_fret)
    windows = build_minor_pent_guardrail_windows(root, spelling=spelling, max_fret=max_fret)
    return ScaleGuardrailDiagram(
        title=f"{root} Minor Pentatonic Guardrails",
        key_name=root,
        scale_name="minor_pent",
        root=root,
        tones=tones,
        shape_windows=windows,
    )