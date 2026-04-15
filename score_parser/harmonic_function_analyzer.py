import os
import json
import re
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(__file__)
INPUT_DIR = os.path.join(BASE_DIR, "analysis", "harmonic_streams")
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis", "harmonic_functions")

os.makedirs(OUTPUT_DIR, exist_ok=True)

NOTE_TO_PC = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
}

CHORD_RE = re.compile(
    r"""
    ^
    (?P<root>[A-G](?:\#|b)?)
    (?P<quality>
        maj13|maj11|maj9|maj7|
        mMaj9|mMaj7|
        m7b5|
        dim7|dim|aug|
        m13|m11|m9|m7|m6|m|
        sus2|sus4|sus|
        add13|add11|add9|
        13|11|9|7|6/9|6|5
    )?
    (?:/(?P<bass>[A-G](?:\#|b)?))?
    $
    """,
    re.VERBOSE,
)


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def parse_chord_symbol(symbol: str) -> Dict[str, Any]:
    m = CHORD_RE.match(symbol)
    if not m:
        return {
            "symbol": symbol,
            "root": None,
            "bass": None,
            "quality_raw": None,
            "quality_family": "unknown",
            "is_dominant": False,
            "is_minor": False,
            "is_major": False,
            "is_diminished": False,
            "is_augmented": False,
            "is_half_diminished": False,
            "extensions": [],
            "parse_ok": False,
        }

    root = m.group("root")
    bass = m.group("bass")
    quality_raw = m.group("quality") or ""

    quality_family = classify_quality_family(quality_raw)
    extensions = extract_extensions(quality_raw)

    return {
        "symbol": symbol,
        "root": root,
        "bass": bass,
        "quality_raw": quality_raw,
        "quality_family": quality_family,
        "is_dominant": quality_family == "dominant",
        "is_minor": quality_family == "minor",
        "is_major": quality_family == "major",
        "is_diminished": quality_family == "diminished",
        "is_augmented": quality_family == "augmented",
        "is_half_diminished": quality_family == "half_diminished",
        "extensions": extensions,
        "parse_ok": True,
    }


def classify_quality_family(q: str) -> str:
    if q == "":
        return "major"
    if q in {"7", "9", "11", "13"}:
        return "dominant"
    if q in {"maj7", "maj9", "maj11", "maj13", "6", "6/9", "add9", "add11", "add13", "5", "sus2", "sus4", "sus"}:
        return "major"
    if q in {"m", "m6", "m7", "m9", "m11", "m13", "mMaj7", "mMaj9"}:
        return "minor"
    if q == "m7b5":
        return "half_diminished"
    if q in {"dim", "dim7"}:
        return "diminished"
    if q == "aug":
        return "augmented"
    return "unknown"


def extract_extensions(q: str) -> List[str]:
    found = []
    for token in ["6", "6/9", "7", "9", "11", "13", "add9", "add11", "add13", "maj7", "maj9", "maj11", "maj13"]:
        if token in q:
            found.append(token)
    return found


def root_pc(root: Optional[str]) -> Optional[int]:
    if root is None:
        return None
    return NOTE_TO_PC.get(root)


def upward_interval(pc1: int, pc2: int) -> int:
    return (pc2 - pc1) % 12


def signed_smallest_interval(pc1: int, pc2: int) -> int:
    raw = (pc2 - pc1) % 12
    if raw > 6:
        raw -= 12
    return raw


def classify_root_motion(prev_root: Optional[str], curr_root: Optional[str]) -> Dict[str, Any]:
    if prev_root is None or curr_root is None:
        return {
            "interval_up": None,
            "interval_signed": None,
            "motion_class": "unknown",
        }

    pc1 = root_pc(prev_root)
    pc2 = root_pc(curr_root)

    if pc1 is None or pc2 is None:
        return {
            "interval_up": None,
            "interval_signed": None,
            "motion_class": "unknown",
        }

    up = upward_interval(pc1, pc2)
    signed = signed_smallest_interval(pc1, pc2)

    motion_class = "other"

    if up == 5:
        motion_class = "cycle_of_fourths"
    elif up == 7:
        motion_class = "cycle_of_fifths"
    elif up in {1, 11}:
        motion_class = "chromatic"
    elif up in {2, 10}:
        motion_class = "seconds_motion"
    elif up in {3, 9}:
        motion_class = "thirds_or_sixths_motion_minor"
    elif up in {4, 8}:
        motion_class = "thirds_or_sixths_motion_major"
    elif up == 6:
        motion_class = "tritone_motion"

    return {
        "interval_up": up,
        "interval_signed": signed,
        "motion_class": motion_class,
    }


def detect_tonal_shift(prev_info: Dict[str, Any], curr_info: Dict[str, Any], motion_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not prev_info["parse_ok"] or not curr_info["parse_ok"]:
        return None

    prev_root = prev_info["root"]
    curr_root = curr_info["root"]
    if prev_root != curr_root:
        return None

    prev_family = prev_info["quality_family"]
    curr_family = curr_info["quality_family"]

    if prev_family == curr_family:
        return None

    pair = {prev_family, curr_family}
    if "major" in pair and "minor" in pair:
        return {
            "type": "parallel_major_minor_shift",
            "description": f"{prev_info['symbol']} -> {curr_info['symbol']}",
        }

    return {
        "type": "same_root_quality_shift",
        "description": f"{prev_info['symbol']} -> {curr_info['symbol']}",
    }


def detect_dominant_resolution(prev_info: Dict[str, Any], curr_info: Dict[str, Any], motion_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not prev_info["parse_ok"] or not curr_info["parse_ok"]:
        return None

    if not prev_info["is_dominant"]:
        return None

    if motion_info["interval_up"] == 5:
        return {
            "type": "dominant_resolution_by_fourth",
            "target": curr_info["symbol"],
            "strength": "high",
        }

    if motion_info["interval_up"] == 7:
        return {
            "type": "dominant_chain_by_fifth",
            "target": curr_info["symbol"],
            "strength": "high",
        }

    if curr_info["is_minor"] or curr_info["is_major"]:
        return {
            "type": "possible_dominant_resolution",
            "target": curr_info["symbol"],
            "strength": "medium",
        }

    return None


def detect_diminished_behavior(prev_info: Dict[str, Any], curr_info: Dict[str, Any], motion_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not prev_info["parse_ok"] or not curr_info["parse_ok"]:
        return None

    if prev_info["is_diminished"] or prev_info["is_half_diminished"]:
        return {
            "type": "diminished_connector",
            "target": curr_info["symbol"],
            "strength": "high" if motion_info["motion_class"] in {"chromatic", "seconds_motion"} else "medium",
        }

    return None


def detect_augmented_behavior(prev_info: Dict[str, Any], curr_info: Dict[str, Any], motion_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not prev_info["parse_ok"] or not curr_info["parse_ok"]:
        return None

    if prev_info["is_augmented"]:
        return {
            "type": "augmented_color_shift",
            "target": curr_info["symbol"],
            "strength": "medium",
        }

    return None


def detect_modal_scalar_descent(prev_info: Dict[str, Any], curr_info: Dict[str, Any], motion_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not prev_info["parse_ok"] or not curr_info["parse_ok"]:
        return None

    if motion_info["interval_signed"] not in {-1, -2}:
        return None

    if prev_info["quality_family"] in {"major", "minor"} and curr_info["quality_family"] in {"major", "minor"}:
        return {
            "type": "descending_scalar_or_modal_motion",
            "strength": "medium",
        }

    return None


def detect_cycle_pattern(window: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Detect common cycle chains like:
    ii-V-I
    vi-ii-V-I
    or generic repeated fourth/fifth cycles
    """
    if len(window) < 3:
        return None

    motions = []
    for i in range(1, len(window)):
        prev_info = window[i - 1]["parsed"]
        curr_info = window[i]["parsed"]
        motion = classify_root_motion(prev_info["root"], curr_info["root"])
        motions.append(motion["motion_class"])

    if all(m in {"cycle_of_fourths", "cycle_of_fifths"} for m in motions):
        return {
            "type": "cycle_chain",
            "length": len(window),
            "motions": motions,
        }

    return None


def infer_treatment(prev_info: Dict[str, Any], curr_info: Dict[str, Any], motion_info: Dict[str, Any],
                    dominant_event: Optional[Dict[str, Any]],
                    diminished_event: Optional[Dict[str, Any]],
                    augmented_event: Optional[Dict[str, Any]],
                    modal_event: Optional[Dict[str, Any]],
                    tonal_shift_event: Optional[Dict[str, Any]]) -> str:
    if diminished_event is not None or augmented_event is not None or tonal_shift_event is not None:
        return "hybrid"

    if dominant_event is not None:
        return "teal_candidate"

    if motion_info["motion_class"] in {"cycle_of_fourths", "cycle_of_fifths", "thirds_or_sixths_motion_major", "thirds_or_sixths_motion_minor"}:
        if prev_info["is_dominant"] or curr_info["is_dominant"]:
            return "teal_candidate"

    if modal_event is not None or motion_info["motion_class"] in {"seconds_motion", "chromatic"}:
        return "pink_candidate"

    if prev_info["is_major"] or prev_info["is_minor"]:
        return "neutral_or_contextual"

    return "neutral_or_contextual"


def analyze_stream(stream: List[str]) -> Dict[str, Any]:
    parsed_stream = [parse_chord_symbol(ch) for ch in stream]
    transition_records: List[Dict[str, Any]] = []

    treatment_counts = {
        "pink_candidate": 0,
        "teal_candidate": 0,
        "hybrid": 0,
        "neutral_or_contextual": 0,
    }

    for i in range(1, len(parsed_stream)):
        prev_info = parsed_stream[i - 1]
        curr_info = parsed_stream[i]

        motion_info = classify_root_motion(prev_info["root"], curr_info["root"])
        dominant_event = detect_dominant_resolution(prev_info, curr_info, motion_info)
        diminished_event = detect_diminished_behavior(prev_info, curr_info, motion_info)
        augmented_event = detect_augmented_behavior(prev_info, curr_info, motion_info)
        modal_event = detect_modal_scalar_descent(prev_info, curr_info, motion_info)
        tonal_shift_event = detect_tonal_shift(prev_info, curr_info, motion_info)

        treatment = infer_treatment(
            prev_info=prev_info,
            curr_info=curr_info,
            motion_info=motion_info,
            dominant_event=dominant_event,
            diminished_event=diminished_event,
            augmented_event=augmented_event,
            modal_event=modal_event,
            tonal_shift_event=tonal_shift_event,
        )

        treatment_counts[treatment] += 1

        transition_records.append({
            "index": i - 1,
            "from": prev_info["symbol"],
            "to": curr_info["symbol"],
            "from_parsed": prev_info,
            "to_parsed": curr_info,
            "motion": motion_info,
            "dominant_event": dominant_event,
            "diminished_event": diminished_event,
            "augmented_event": augmented_event,
            "modal_event": modal_event,
            "tonal_shift_event": tonal_shift_event,
            "treatment": treatment,
        })

    cycle_windows = []
    for size in [3, 4]:
        for i in range(len(parsed_stream) - size + 1):
            window = []
            for j in range(size):
                window.append({
                    "symbol": parsed_stream[i + j]["symbol"],
                    "parsed": parsed_stream[i + j],
                })
            cycle_info = detect_cycle_pattern(window)
            if cycle_info:
                cycle_windows.append({
                    "start_index": i,
                    "window": [w["symbol"] for w in window],
                    "cycle_info": cycle_info,
                })

    summary = summarize_functions(transition_records, cycle_windows)

    return {
        "parsed_stream": parsed_stream,
        "transition_records": transition_records,
        "cycle_windows": cycle_windows,
        "treatment_counts": treatment_counts,
        "function_summary": summary,
    }


def summarize_functions(transition_records: List[Dict[str, Any]], cycle_windows: List[Dict[str, Any]]) -> Dict[str, Any]:
    dominant_chains = []
    diminished_connectors = []
    augmented_events = []
    tonal_shifts = []
    modal_descents = []

    for rec in transition_records:
        if rec["dominant_event"] is not None:
            dominant_chains.append({
                "from": rec["from"],
                "to": rec["to"],
                "event": rec["dominant_event"],
            })
        if rec["diminished_event"] is not None:
            diminished_connectors.append({
                "from": rec["from"],
                "to": rec["to"],
                "event": rec["diminished_event"],
            })
        if rec["augmented_event"] is not None:
            augmented_events.append({
                "from": rec["from"],
                "to": rec["to"],
                "event": rec["augmented_event"],
            })
        if rec["tonal_shift_event"] is not None:
            tonal_shifts.append({
                "from": rec["from"],
                "to": rec["to"],
                "event": rec["tonal_shift_event"],
            })
        if rec["modal_event"] is not None:
            modal_descents.append({
                "from": rec["from"],
                "to": rec["to"],
                "event": rec["modal_event"],
            })

    return {
        "dominant_chain_count": len(dominant_chains),
        "diminished_connector_count": len(diminished_connectors),
        "augmented_event_count": len(augmented_events),
        "tonal_shift_count": len(tonal_shifts),
        "modal_descent_count": len(modal_descents),
        "cycle_window_count": len(cycle_windows),
        "dominant_chains": dominant_chains[:20],
        "diminished_connectors": diminished_connectors[:20],
        "augmented_events": augmented_events[:20],
        "tonal_shifts": tonal_shifts[:20],
        "modal_descents": modal_descents[:20],
        "cycle_windows": cycle_windows[:20],
    }


def main() -> None:
    combined = []

    for filename in sorted(os.listdir(INPUT_DIR)):
        if not filename.endswith("_harmonic_stream.json"):
            continue

        path = os.path.join(INPUT_DIR, filename)
        data = load_json(path)

        title = data.get("title")
        harmonic_stream = data.get("harmonic_stream", [])
        unique_chords = data.get("unique_chords", [])
        harmonic_cells = data.get("harmonic_cells", [])

        analysis = analyze_stream(harmonic_stream)

        result = {
            "title": title,
            "harmonic_stream": harmonic_stream,
            "unique_chords": unique_chords,
            "harmonic_cells": harmonic_cells,
            "parsed_stream": analysis["parsed_stream"],
            "transition_records": analysis["transition_records"],
            "cycle_windows": analysis["cycle_windows"],
            "treatment_counts": analysis["treatment_counts"],
            "function_summary": analysis["function_summary"],
        }

        combined.append(result)

        out_name = filename.replace("_harmonic_stream.json", "_functions.json")
        out_path = os.path.join(OUTPUT_DIR, out_name)
        save_json(out_path, result)

    combined_path = os.path.join(OUTPUT_DIR, "all_harmonic_functions.json")
    save_json(combined_path, combined)

    print("\nSaved harmonic function files to:")
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()