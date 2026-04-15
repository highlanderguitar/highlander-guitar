import os
import json
from typing import Dict, List, Any

BASE_DIR = os.path.dirname(__file__)
CHORD_ANALYSIS_DIR = os.path.join(BASE_DIR, "analysis", "chord_symbols")
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis", "chord_repairs")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------
# MANUAL REPAIR MEMORY
# --------------------------------
# This is the beginning of your teachable correction bank.
# Add to this over time.
#
# Key = raw harvested token
# Value = repaired chord symbol
# --------------------------------

REPAIR_MAP: Dict[str, str] = {
    # Birdland Breakdown examples
    "B\ue2606/9": "Bb6/9",
    "B\ue2607": "Bb7",
    "E\ue8707": "Edim7",
    "G\ue8707": "Gdim7",

    # Common Ground examples
    "E\ue2605": "Eb5",
    "E\ue260513": "Eb5add13",
    "E\ue26057": "Eb57",
    "C\ue262m7": "C#m7",
    "F\ue262m7": "F#m7",
    "C\ue8739": "C#9",
    "Badd9/D\ue262": "Badd9/D#",
    "Aadd9/C\ue262": "Aadd9/C#",
}

# Tokens that should never survive as standalone chord symbols
NOISE_TOKENS = {
    "Ardans", "Griffin", "Birdland", "Breakdown", "Common", "Ground",
    "Gasology", "Manzanita", "Neon", "Tetra", "Port", "Tobacco",
    "Swing", "Waltz", "Indira", "Mar", "East", "West", "Old", "Gray", "Coat",
    "Is", "That", "So", "SoMuch", "John", "Reischman"
}

# Standalone suffix fragments are not valid chord symbols by themselves
ORPHAN_SUFFIXES = {"7", "9", "11", "13", "m7", "maj7", "6/9"}

# --------------------------------
# HELPERS
# --------------------------------

def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def is_noise_token(token: str) -> bool:
    if token in NOISE_TOKENS:
        return True
    if token in ORPHAN_SUFFIXES:
        return True
    return False

def apply_repair(token: str) -> Dict[str, Any]:
    if token in REPAIR_MAP:
        return {
            "normalized_token": REPAIR_MAP[token],
            "repair_status": "repaired_from_memory",
            "needs_review": False,
        }

    if is_noise_token(token):
        return {
            "normalized_token": "",
            "repair_status": "discarded_noise",
            "needs_review": False,
        }

    # Keep ambiguous tokens for human review
    return {
        "normalized_token": token,
        "repair_status": "needs_manual_review",
        "needs_review": True,
    }

def process_file(path: str) -> Dict[str, Any]:
    data = load_json(path)

    repaired_records = []
    unresolved = []

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

    # Keep only usable repaired tokens for harmonic stream
    usable_chords = [
        r["normalized_token"]
        for r in repaired_records
        if r["normalized_token"]
        and r["repair_status"] != "discarded_noise"
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