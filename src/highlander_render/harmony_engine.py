from __future__ import annotations
from types import SimpleNamespace

import re
from dataclasses import dataclass
from typing import Literal

from .models import DiagramTone, HarmonicEvent, ProgressionChart

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

MINOR_PENT_INTERVALS = ["1", "b3", "4", "5", "b7"]
MAJOR_PENT_INTERVALS = ["1", "2", "3", "5", "6"]


@dataclass(frozen=True)
class ClassifiedTone:
    note_name: str
    role: str
    chord_interval: str
    source: str
    semitone: int


@dataclass(frozen=True)
class GuardrailNode:
    string_index: int
    fret: int
    note_name: str
    degree_label: str
    sequence_index: int
    node_kind: str
    is_structural: bool = False


@dataclass(frozen=True)
class RectangleWindow:
    low_string_index: int
    high_string_index: int
    low_left_fret: int
    low_right_fret: int
    high_left_fret: int
    high_right_fret: int


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
    chord_tones = get_chord_tones(chord_root, chord_quality, spelling)
    super_tones = get_minor_pent_tones(super_root, chord_root, spelling)
    chord_map = {t.semitone: t for t in chord_tones}

    result: list[ClassifiedTone] = []
    for t in super_tones:
        result.append(chord_map[t.semitone] if t.semitone in chord_map else t)
    return result


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
    if 5 <= fret <= 8:
        return 1
    if 8 <= fret <= 10:
        return 2
    if 10 <= fret <= 13:
        return 3
    if 13 <= fret <= 15:
        return 4
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


def build_minor_pent_cycle(
    root: str,
    spelling: NoteSpelling = "sharps",
) -> list[tuple[str, str, int]]:
    root_idx = note_to_index(root)
    out: list[tuple[str, str, int]] = []
    for degree_label in MINOR_PENT_INTERVALS:
        semitones = INTERVAL_TO_SEMITONES[degree_label]
        note_name = index_to_note(root_idx + semitones, spelling)
        out.append((degree_label, note_name, (root_idx + semitones) % 12))
    return out


def build_minor_pent_nodes_for_event(
    chord_root: str,
    chord_quality: str,
    super_root: str,
    spelling: NoteSpelling = "sharps",
    max_fret: int = 15,
) -> list[GuardrailNode]:
    cycle = build_minor_pent_cycle(super_root, spelling)
    chord_pitch_classes = {t.semitone for t in get_chord_tones(chord_root, chord_quality, spelling)}

    nodes: list[GuardrailNode] = []

    for sequence_index, (degree_label, note_name, pitch_class) in enumerate(cycle):
        node_kind = "chord" if pitch_class in chord_pitch_classes else "pink"

        for string_index, fret in iter_fretboard_positions_for_pitch_class(pitch_class, max_fret=max_fret):
            nodes.append(
                GuardrailNode(
                    string_index=string_index,
                    fret=fret,
                    note_name=note_name,
                    degree_label=degree_label,
                    sequence_index=sequence_index,
                    node_kind=node_kind,
                    is_structural=False,
                )
            )

    nodes.sort(key=lambda n: (n.fret, n.string_index, n.sequence_index))
    return nodes


def _minor_pent_positions_by_string(
    super_root: str,
    spelling: NoteSpelling = "sharps",
    max_fret: int = 15,
) -> dict[int, list[int]]:
    cycle = build_minor_pent_cycle(super_root, spelling)
    positions: dict[int, set[int]] = {s: set() for s in range(6)}

    for _, _, pitch_class in cycle:
        for string_index, fret in iter_fretboard_positions_for_pitch_class(pitch_class, max_fret=max_fret):
            positions[string_index].add(fret)

    return {s: sorted(positions[s]) for s in range(6)}


def _three_fret_gaps_by_string(
    super_root: str,
    spelling: NoteSpelling = "sharps",
    max_fret: int = 15,
) -> dict[int, list[tuple[int, int]]]:
    by_string = _minor_pent_positions_by_string(super_root, spelling, max_fret=max_fret)
    out: dict[int, list[tuple[int, int]]] = {s: [] for s in range(6)}

    for string_index, frets in by_string.items():
        for a, b in zip(frets, frets[1:]):
            if b - a == 3:
                out[string_index].append((a, b))

    return out


def build_rectangle_windows_for_minor_pent(
    super_root: str,
    spelling: NoteSpelling = "sharps",
    max_fret: int = 15,
) -> list[RectangleWindow]:
    gaps = _three_fret_gaps_by_string(super_root, spelling, max_fret=max_fret)
    windows: list[RectangleWindow] = []
    seen: set[tuple[int, int, int, int, int, int]] = set()

    for low_string_index, high_string_index in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5)):
        low_gaps = gaps.get(low_string_index, [])
        high_gaps = gaps.get(high_string_index, [])
        warp = (low_string_index, high_string_index) == (3, 4)

        for low_left, low_right in low_gaps:
            for high_left, high_right in high_gaps:
                if warp:
                    same_left = high_left == low_left + 1
                    same_right = high_right == low_right + 1
                else:
                    same_left = high_left == low_left
                    same_right = high_right == low_right

                if not (same_left and same_right):
                    continue

                key = (
                    low_string_index,
                    high_string_index,
                    low_left,
                    low_right,
                    high_left,
                    high_right,
                )
                if key in seen:
                    continue
                seen.add(key)

                windows.append(
                    RectangleWindow(
                        low_string_index=low_string_index,
                        high_string_index=high_string_index,
                        low_left_fret=low_left,
                        low_right_fret=low_right,
                        high_left_fret=high_left,
                        high_right_fret=high_right,
                    )
                )

    windows.sort(
        key=lambda w: (
            min(w.low_left_fret, w.high_left_fret),
            w.low_string_index,
            w.high_string_index,
        )
    )
    return windows


def mark_structural_rectangle_nodes(
    nodes: list[GuardrailNode],
    rectangles: list[RectangleWindow],
) -> list[GuardrailNode]:
    structural_positions: set[tuple[int, int]] = set()

    for rect in rectangles:
        structural_positions.update(
            {
                (rect.low_string_index, rect.low_left_fret),
                (rect.low_string_index, rect.low_right_fret),
                (rect.high_string_index, rect.high_left_fret),
                (rect.high_string_index, rect.high_right_fret),
            }
        )

    out: list[GuardrailNode] = []
    for node in nodes:
        out.append(
            GuardrailNode(
                string_index=node.string_index,
                fret=node.fret,
                note_name=node.note_name,
                degree_label=node.degree_label,
                sequence_index=node.sequence_index,
                node_kind=node.node_kind,
                is_structural=(node.string_index, node.fret) in structural_positions,
            )
        )
    return out


def build_minor_pent_guardrail_diagram(
    super_root: str,
    chord_root: str | None = None,
    chord_quality: str = "min7",
    event=None,
):
    if chord_root is None:
        chord_root = super_root

    raw_nodes = build_minor_pent_nodes_for_event(chord_root, chord_quality, super_root)
    rectangles = build_rectangle_windows_for_minor_pent(super_root)
    nodes = mark_structural_rectangle_nodes(raw_nodes, rectangles)

    shape_windows = []
    for i, rect in enumerate(rectangles, start=1):
        fret_min = min(rect.low_left_fret, rect.high_left_fret)
        fret_max = max(rect.low_right_fret, rect.high_right_fret)

        edges = [
            SimpleNamespace(
                start_string_index=rect.low_string_index,
                end_string_index=rect.low_string_index,
                start_fret=rect.low_left_fret,
                end_fret=rect.low_right_fret,
                color_role="rectangle",
            ),
            SimpleNamespace(
                start_string_index=rect.high_string_index,
                end_string_index=rect.high_string_index,
                start_fret=rect.high_left_fret,
                end_fret=rect.high_right_fret,
                color_role="rectangle",
            ),
        ]

        tones = [
            node
            for node in nodes
            if (
                (node.string_index == rect.low_string_index and rect.low_left_fret <= node.fret <= rect.low_right_fret)
                or
                (node.string_index == rect.high_string_index and rect.high_left_fret <= node.fret <= rect.high_right_fret)
            )
        ]

        shape_windows.append(
            SimpleNamespace(
                shape_id=i,
                fret_min=fret_min,
                fret_max=fret_max,
                edges=edges,
                tones=tones,
                low_string_index=rect.low_string_index,
                high_string_index=rect.high_string_index,
                low_left_fret=rect.low_left_fret,
                low_right_fret=rect.low_right_fret,
                high_left_fret=rect.high_left_fret,
                high_right_fret=rect.high_right_fret,
                rectangle=rect,
            )
        )

    return SimpleNamespace(
        guardrails=nodes,
        nodes=nodes,
        rectangles=rectangles,
        shape_windows=shape_windows,
        event=event,
        super_root=super_root,
        chord_root=chord_root,
        chord_quality=chord_quality,
    )


def _distance_color(distance: int) -> str | None:
    if distance == 3:
        return "red"
    if distance == 2:
        return "blue"
    return None


def _is_minor_pent_stack_center_span(
    super_root: str,
    pitch_a: int,
    pitch_b: int,
) -> bool:
    """
    Highlander stack rule:

    The blue b7 -> 1 whole-step span is the CENTER line of the stack.
    Do not draw it.

    Example in B minor pent:
        A -> B

    Keep the other blue whole-step spans:
        b3 -> 4
        4 -> 5
    """
    root_pc = note_to_index(super_root)
    flat7_pc = (root_pc + INTERVAL_TO_SEMITONES["b7"]) % 12

    return pitch_a == flat7_pc and pitch_b == root_pc


def _raw_string_spans_for_minor_pent(
    super_root: str,
    max_fret: int = 15,
) -> dict[int, list[tuple[str, int, int]]]:
    spans: dict[int, list[tuple[str, int, int]]] = {
        s: [] for s in range(len(TUNING_BOTTOM_TO_TOP))
    }

    cycle_pitch_classes = {
        pitch_class
        for _, _, pitch_class in build_minor_pent_cycle(super_root, "sharps")
    }

    for string_index, open_name in enumerate(TUNING_BOTTOM_TO_TOP):
        open_pc = TUNING_PITCHES[open_name]
        hits: list[tuple[int, int]] = []

        for fret in range(0, max_fret + 1):
            pitch_class = (open_pc + fret) % 12
            if pitch_class in cycle_pitch_classes:
                hits.append((fret, pitch_class))

        for (a, pitch_a), (b, pitch_b) in zip(hits, hits[1:]):
            color = _distance_color(b - a)

            if color == "blue" and _is_minor_pent_stack_center_span(
                super_root,
                pitch_a,
                pitch_b,
            ):
                continue

            if color:
                spans[string_index].append((color, a, b))

        if normalize_note_name(super_root) == "B" and string_index == 3 and max_fret >= 2:
            fret2_pc = (open_pc + 2) % 12
            a_pc = note_to_index("A")
            if fret2_pc == a_pc:
                spans[string_index] = [
                    item for item in spans[string_index]
                    if not (item[1] == 0 and item[2] == 2)
                ]
                spans[string_index].insert(0, ("red", 0, 2))

        spans[string_index].sort(key=lambda t: (t[1], t[2], t[0]))

    return spans


def _normalize_string_spans(
    spans: list[tuple[str, int, int]]
) -> list[tuple[str, int, int]]:
    if not spans:
        return []

    ordered = sorted(spans, key=lambda t: (t[1], t[2], t[0]))
    merged: list[list[object]] = []

    for color, a, b in ordered:
        if color == "blue":
            merged.append([color, a, b])
            continue

        if not merged:
            merged.append([color, a, b])
            continue

        last_color, _, last_b = merged[-1]
        if color == "red" and last_color == "red" and a == last_b:
            merged[-1][2] = b
        else:
            merged.append([color, a, b])

    return [(color, int(a), int(b)) for color, a, b in merged]


def build_minor_pent_string_spans(
    root: str,
    spelling: NoteSpelling = "sharps",
    max_fret: int = 15,
) -> dict[int, list[tuple[str, int, int]]]:
    raw = _raw_string_spans_for_minor_pent(root, max_fret=max_fret)
    return {
        string_index: _normalize_string_spans(items)
        for string_index, items in raw.items()
    }

def build_string_span_overlay_for_event(
    event: HarmonicEvent,
    spelling: NoteSpelling = "sharps",
    max_fret: int = 15,
) -> dict[int, list[tuple[str, int, int]]]:
    super_root = getattr(event, "super_root", None)
    if not super_root:
        return {}
    return build_minor_pent_string_spans(super_root, spelling=spelling, max_fret=max_fret)


def debug_print_guardrail_summary(events: list[HarmonicEvent]) -> None:
    print("\nGUARDRAIL SUMMARY")
    for i, event in enumerate(events, start=1):
        spans = getattr(event, "guardrail_spans", {}) or {}
        total_spans = sum(len(items) for items in spans.values())
        print(
            f"{i:02d}. "
            f"label={event.display_label:<10} "
            f"root={event.root:<3} "
            f"quality={event.quality:<5} "
            f"super_root={str(getattr(event, 'super_root', None)):<3} "
            f"span_count={total_spans}"
        )
        for string_index in sorted(spans):
            if spans[string_index]:
                print(f"    string {string_index}: {spans[string_index]}")


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

                event = HarmonicEvent(
                    symbol=display_symbol,
                    root=root,
                    quality=quality,
                    beats=beats,
                    display_label=display_symbol,
                    section_name=section.name,
                    beat_offset_in_bar=beat_offset,
                    super_root=super_root,
                )

                event.guardrail_spans = build_string_span_overlay_for_event(
                    event,
                    spelling=chart.spelling,
                    max_fret=15,
                )

                raw_nodes = build_minor_pent_nodes_for_event(
                    chord_root=root,
                    chord_quality=quality,
                    super_root=super_root,
                    spelling=chart.spelling,
                    max_fret=15,
                )
                rectangles = build_rectangle_windows_for_minor_pent(
                    super_root=super_root,
                    spelling=chart.spelling,
                    max_fret=15,
                )
                event.guardrail_nodes = mark_structural_rectangle_nodes(raw_nodes, rectangles)
                event.rectangle_windows = rectangles

                all_events.append(event)
                beat_offset += beats

    return all_events