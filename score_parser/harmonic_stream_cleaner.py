import os
import re
import json
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(__file__)
INPUT_DIR = os.path.join(BASE_DIR, "analysis", "chord_repairs")
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis", "harmonic_streams")

os.makedirs(OUTPUT_DIR, exist_ok=True)


VALID_CHORD_RE = re.compile(
    r"""
    ^
    [A-G]                              # root
    (?:[#b])?                          # accidental
    (?:
        maj7|maj9|maj11|maj13|
        m7b5|mMaj7|mMaj9|
        dim7|dim|aug|
        m11|m9|m7|m6|m|
        sus2|sus4|sus|
        add9|add11|add13|
        13|11|9|7|6/9|6|5
    )?
    (?:/[A-G](?:[#b])?)?               # slash bass
    $
    """,
    re.VERBOSE,
)


TITLE_WORDS_BY_TUNE = {
    "birdland_breakdown": {"Birdland", "Breakdown"},
    "common_ground": {"Common", "Ground", "Ground7"},
    "gasology": {"Gasology", "Gasology7"},
    "is_that_so": {"Is", "That", "So"},
    "manzanita": {"Manzanita"},
    "mar_east": {"Mar", "East"},
    "mar_west": {"Mar", "West"},
    "neon_tetra": {"Neon", "Tetra"},
    "old_gray_coat": {"Old", "Gray", "Coat"},
    "port_tobacco": {"Port", "Tobacco"},
    "so_much": {"So", "Much"},
    "swing_51": {"Swing"},
    "waltz_for_indira": {"Waltz", "Indira"},
}


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def is_valid_chord_symbol(token: str) -> bool:
    return bool(VALID_CHORD_RE.match(token))


def is_suspicious_singleton_root(token: str) -> bool:
    return token in {"A", "B", "C", "D", "E", "F", "G"}


def normalize_records(title: str, repaired_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    title_noise = TITLE_WORDS_BY_TUNE.get(title, set())

    harmonic_stream: List[str] = []
    unique_chords: List[str] = []
    unique_seen = set()

    accepted_records: List[Dict[str, Any]] = []
    rejected_records: List[Dict[str, Any]] = []
    review_records: List[Dict[str, Any]] = []

    for rec in repaired_records:
        raw = rec.get("raw_token", "")
        normalized = rec.get("normalized_token", "")
        page_index = rec.get("page_index")
        seq_index = rec.get("sequence_index")

        # Skip discarded noise from earlier stage
        if rec.get("repair_status") == "discarded_noise":
            rejected_records.append({
                **rec,
                "cleaner_status": "discarded_noise",
                "cleaner_reason": "discarded by repair memory",
            })
            continue

        # Drop title contamination even if it slipped through
        if raw in title_noise or normalized in title_noise:
            rejected_records.append({
                **rec,
                "cleaner_status": "discarded_title_noise",
                "cleaner_reason": "matched tune-title contamination",
            })
            continue

        # Empty normalized token means unusable
        if not normalized:
            rejected_records.append({
                **rec,
                "cleaner_status": "discarded_empty",
                "cleaner_reason": "empty normalized token",
            })
            continue

        # Strong accept: known-valid chord symbol
        if is_valid_chord_symbol(normalized):
            # But keep suspicious singleton roots reviewable
            if is_suspicious_singleton_root(normalized):
                review_records.append({
                    **rec,
                    "cleaner_status": "review_singleton_root",
                    "cleaner_reason": "singleton root may be true chord or OCR/title contamination",
                })
            else:
                accepted_records.append({
                    **rec,
                    "cleaner_status": "accepted_valid_symbol",
                    "cleaner_reason": "matched valid chord symbol pattern",
                })
                harmonic_stream.append(normalized)
                if normalized not in unique_seen:
                    unique_seen.add(normalized)
                    unique_chords.append(normalized)
            continue

        # Anything else goes to review
        review_records.append({
            **rec,
            "cleaner_status": "needs_context_review",
            "cleaner_reason": "did not match valid chord symbol pattern",
        })

    # Build repeated cells from accepted harmonic stream
    harmonic_cells = detect_harmonic_cells(harmonic_stream)

    return {
        "title": title,
        "harmonic_stream": harmonic_stream,
        "unique_chords": unique_chords,
        "harmonic_cells": harmonic_cells,
        "accepted_records": accepted_records,
        "review_records": review_records,
        "rejected_records": rejected_records,
    }


def detect_harmonic_cells(stream: List[str], min_len: int = 2, max_len: int = 6, min_occurrences: int = 2) -> List[Dict[str, Any]]:
    """
    Find repeated chord subsequences.
    This is intentionally simple but useful.
    """
    cell_counts: Dict[tuple, Dict[str, Any]] = {}

    n = len(stream)
    for size in range(min_len, max_len + 1):
        if size > n:
            continue

        for i in range(n - size + 1):
            cell = tuple(stream[i:i + size])

            # ignore exact same repeated chord blobs
            if len(set(cell)) == 1:
                continue

            if cell not in cell_counts:
                cell_counts[cell] = {
                    "cell": list(cell),
                    "count": 0,
                    "start_indexes": [],
                }

            cell_counts[cell]["count"] += 1
            cell_counts[cell]["start_indexes"].append(i)

    # keep only repeated cells
    repeated = [
        v for v in cell_counts.values()
        if v["count"] >= min_occurrences
    ]

    # prefer more substantial cells
    repeated.sort(
        key=lambda x: (
            -len(x["cell"]),
            -x["count"],
            x["start_indexes"][0],
        )
    )

    # lightly dedupe contained/less useful cells
    filtered: List[Dict[str, Any]] = []
    seen_signatures = set()

    for item in repeated:
        sig = tuple(item["cell"])
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)
        filtered.append(item)

    return filtered[:20]


def main() -> None:
    combined = []

    for filename in sorted(os.listdir(INPUT_DIR)):
        if not filename.endswith("_repaired.json"):
            continue

        path = os.path.join(INPUT_DIR, filename)
        data = load_json(path)

        title = data.get("title", os.path.splitext(filename)[0].replace("_repaired", ""))
        repaired_records = data.get("repaired_records", [])

        cleaned = normalize_records(title=title, repaired_records=repaired_records)
        combined.append(cleaned)

        out_name = filename.replace("_repaired.json", "_harmonic_stream.json")
        out_path = os.path.join(OUTPUT_DIR, out_name)
        save_json(out_path, cleaned)

    combined_path = os.path.join(OUTPUT_DIR, "all_harmonic_streams.json")
    save_json(combined_path, combined)

    print("\nSaved harmonic stream files to:")
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()