import os
import json
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(__file__)
CHORD_ANALYSIS_DIR = os.path.join(BASE_DIR, "analysis", "chord_symbols")
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis", "chord_repairs")

os.makedirs(OUTPUT_DIR, exist_ok=True)

VALID_ROOTS = {"A", "B", "C", "D", "E", "F", "G"}
VALID_QUALIFIERS = {
    "", "m", "7", "m7", "maj7", "dim", "dim7",
    "aug", "9", "11", "13", "6", "6/9",
    "m9", "m11", "m13",
    "sus", "sus2", "sus4"
}

REPAIR_MAP: Dict[str, str] = {
    "B\ue2606/9": "Bb6/9",
    "B\ue2607": "Bb7",
    "E\ue8707": "Edim7",
    "G\ue8707": "Gdim7",
}

NOISE_TOKENS = {
    "Dew", "As", "By", "Capo", "Mountain",
    "Performed", "Standard", "Tuning", "Fret",
    "sl", "P", "H"
}

ORPHAN_SUFFIXES = {"7", "9", "11", "13", "m7", "maj7", "6/9"}


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def is_valid_chord_symbol(token: str) -> bool:
    if not token:
        return False

    if token in NOISE_TOKENS:
        return False

    if token in ORPHAN_SUFFIXES:
        return False

    if token.isdigit():
        return False

    root = token[0]
    if root not in VALID_ROOTS:
        return False

    rest = token[1:]

    if rest.startswith("#") or rest.startswith("b"):
        rest = rest[1:]

    if "/" in rest:
        parts = rest.split("/")
        if len(parts) != 2:
            return False
        rest = parts[0]

    return rest in VALID_QUALIFIERS


def apply_repair(token: str) -> Dict[str, Any]:
    if token in REPAIR_MAP:
        return {
            "normalized_token": REPAIR_MAP[token],
            "repair_status": "repaired_from_memory",
            "needs_review": False,
        }

    if token in NOISE_TOKENS or token in ORPHAN_SUFFIXES or token.isdigit():
        return {
            "normalized_token": "",
            "repair_status": "discarded_noise",
            "needs_review": False,
        }

    if is_valid_chord_symbol(token):
        return {
            "normalized_token": token,
            "repair_status": "accepted_valid_symbol",
            "needs_review": False,
        }

    return {
        "normalized_token": "",
        "repair_status": "discarded_unrecognized",
        "needs_review": False,
    }


def process_file(path: str) -> Dict[str, Any]:
    data = load_json(path)

    repaired_records: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []

    for record in data.get("all_records", []):
        raw = record["raw_token"]
        repaired = apply_repair(raw)

        new_record = {
            **record,
            "normalized_token": repaired["normalized_token"],
            "repair_status": repaired["repair_status"],
            "needs_review": repaired["needs_review"],
        }

        repaired_records.append(new_record)

        if repaired["needs_review"]:
            unresolved.append({
                "raw_token": raw,
                "page_index": record["page_index"],
                "sequence_index": record["sequence_index"],
                "ambiguity_classes": record.get("ambiguity_classes", []),
            })

    usable_chords = [
        r["normalized_token"]
        for r in repaired_records
        if r["normalized_token"]
        and r["repair_status"] not in {"discarded_noise", "discarded_unrecognized"}
    ]

    result = {
        "title": data.get("title"),
        "page_count": data.get("page_count"),
        "usable_chords": usable_chords,
        "repaired_records": repaired_records,
        "unresolved_tokens": unresolved,
    }

    return result


def main() -> None:
    combined = []

    for filename in sorted(os.listdir(CHORD_ANALYSIS_DIR)):
        if not filename.endswith("_chords.json"):
            continue

        path = os.path.join(CHORD_ANALYSIS_DIR, filename)
        result = process_file(path)
        combined.append(result)

        out_name = filename.replace("_chords.json", "_repaired.json")
        out_path = os.path.join(OUTPUT_DIR, out_name)
        save_json(out_path, result)

    combined_path = os.path.join(OUTPUT_DIR, "all_symbol_repairs.json")
    save_json(combined_path, combined)

    print("\nSaved repaired chord-symbol files to:")
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()