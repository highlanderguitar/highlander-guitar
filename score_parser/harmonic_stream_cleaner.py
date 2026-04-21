import os
import json
from typing import Any, Dict, List, Tuple

print("RUNNING HARMONIC_STREAM_CLEANER v2")

BASE_DIR = os.path.dirname(__file__)
INPUT_DIR = os.path.join(BASE_DIR, "analysis", "chord_repairs")
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis", "harmonic_streams")

os.makedirs(OUTPUT_DIR, exist_ok=True)

ALLOW_SINGLETON_ROOTS = True
VALID_ROOTS = {"A", "B", "C", "D", "E", "F", "G"}


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def is_singleton_root(token: str) -> bool:
    return token in VALID_ROOTS


def dedupe_adjacent(chords: List[str]) -> List[str]:
    if not chords:
        return []
    out = [chords[0]]
    for ch in chords[1:]:
        if ch != out[-1]:
            out.append(ch)
    return out


def build_harmonic_cells(chords: List[str]) -> List[Dict[str, Any]]:
    cells: List[Dict[str, Any]] = []

    for size in [2, 3, 4]:
        seen: Dict[Tuple[str, ...], List[int]] = {}

        for i in range(len(chords) - size + 1):
            cell = tuple(chords[i:i + size])
            seen.setdefault(cell, []).append(i)

        for cell, starts in seen.items():
            if len(starts) >= 2:
                cells.append({
                    "cell": list(cell),
                    "count": len(starts),
                    "start_indexes": starts
                })

    cells.sort(key=lambda x: (-x["count"], -len(x["cell"]), x["start_indexes"][0]))
    return cells


def process_file(path: str) -> Dict[str, Any]:
    data = load_json(path)

    accepted_records: List[Dict[str, Any]] = []
    review_records: List[Dict[str, Any]] = []
    rejected_records: List[Dict[str, Any]] = []

    for record in data.get("repaired_records", []):
        token = record.get("normalized_token", "")
        repair_status = record.get("repair_status", "")

        if not token:
            new_record = {
                **record,
                "cleaner_status": "rejected_empty",
                "cleaner_reason": "empty normalized token"
            }
            rejected_records.append(new_record)
            continue

        if repair_status in {"discarded_noise", "discarded_unrecognized"}:
            new_record = {
                **record,
                "cleaner_status": "rejected_discarded",
                "cleaner_reason": "repair layer already discarded token"
            }
            rejected_records.append(new_record)
            continue

        if is_singleton_root(token):
            if ALLOW_SINGLETON_ROOTS:
                new_record = {
                    **record,
                    "cleaner_status": "accepted_singleton_root",
                    "cleaner_reason": "singleton root accepted as likely chord symbol"
                }
                accepted_records.append(new_record)
            else:
                new_record = {
                    **record,
                    "cleaner_status": "review_singleton_root",
                    "cleaner_reason": "singleton root may be true chord or OCR/title contamination"
                }
                review_records.append(new_record)
            continue

        new_record = {
            **record,
            "cleaner_status": "accepted_qualified_symbol",
            "cleaner_reason": "qualified chord symbol accepted"
        }
        accepted_records.append(new_record)

    harmonic_stream_raw = [r["normalized_token"] for r in accepted_records]
    harmonic_stream = dedupe_adjacent(harmonic_stream_raw)
    unique_chords = list(dict.fromkeys(harmonic_stream))
    harmonic_cells = build_harmonic_cells(harmonic_stream)

    result = {
        "title": data.get("title"),
        "harmonic_stream": harmonic_stream,
        "unique_chords": unique_chords,
        "harmonic_cells": harmonic_cells,
        "accepted_records": accepted_records,
        "review_records": review_records,
        "rejected_records": rejected_records,
    }

    return result


def main() -> None:
    combined = []

    for filename in sorted(os.listdir(INPUT_DIR)):
        if not filename.endswith("_repaired.json"):
            continue

        path = os.path.join(INPUT_DIR, filename)
        result = process_file(path)
        combined.append(result)

        out_name = filename.replace("_repaired.json", "_harmonic_stream.json")
        out_path = os.path.join(OUTPUT_DIR, out_name)
        save_json(out_path, result)

    combined_path = os.path.join(OUTPUT_DIR, "all_harmonic_streams.json")
    save_json(combined_path, combined)

    print("\nSaved harmonic stream files to:")
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()