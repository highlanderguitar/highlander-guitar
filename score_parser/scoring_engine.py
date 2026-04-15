import os
import json
import csv
from typing import Dict, List

BASE_DIR = os.path.dirname(__file__)
INPUT_PDF_DIR = os.path.join(BASE_DIR, "input")
ANALYSIS_DIR = os.path.join(BASE_DIR, "analysis")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

SEED_CSV = os.path.join(OUTPUT_DIR, "spacegrass_tune_inventory_seed.csv")
SPLIT_MANIFEST_CSV = os.path.join(OUTPUT_DIR, "spacegrass_split_manifest.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv_rows(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: str, fieldnames: List[str], rows: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def safe_int(value, default=0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def classify_title_signals(title: str) -> Dict[str, float]:
    """
    Title-only heuristics.
    Crude on purpose. These are placeholders until deeper parsing exists.
    """
    t = title.lower()

    pink_bonus = 0.0
    teal_bonus = 0.0
    complexity_bonus = 0.0

    if "waltz" in t:
        pink_bonus += 0.5
        complexity_bonus -= 0.25

    if "breakdown" in t:
        teal_bonus += 0.75
        complexity_bonus += 1.0

    if "swing" in t:
        teal_bonus += 1.25
        complexity_bonus += 2.0

    if "tetra" in t:
        teal_bonus += 0.75
        complexity_bonus += 1.0

    if "gasology" in t:
        teal_bonus += 0.75
        complexity_bonus += 1.0

    if "so much" in t:
        pink_bonus += 0.25
        teal_bonus += 0.25
        complexity_bonus += 0.5

    if "manzanita" in t:
        pink_bonus += 0.75

    if "common ground" in t:
        pink_bonus += 0.5

    if "old gray coat" in t:
        pink_bonus += 0.5
        teal_bonus += 0.25

    if "port tobacco" in t:
        teal_bonus += 0.5
        complexity_bonus += 0.5

    return {
        "pink_bonus": pink_bonus,
        "teal_bonus": teal_bonus,
        "complexity_bonus": complexity_bonus,
    }


def normalize_page_count(page_count: int) -> float:
    """
    Low page count usually means easier first-pass entry.
    """
    if page_count <= 1:
        return 2.0
    if page_count == 2:
        return 1.5
    if page_count == 3:
        return 0.75
    return 0.0


def derive_scores(title: str, page_count: int) -> Dict:
    """
    Stable version 1 scoring.
    Avoids bogus measure-count data.
    """

    title_signals = classify_title_signals(title)
    entry_simplicity = normalize_page_count(page_count)

    pink_room_score = 5.0 + entry_simplicity + title_signals["pink_bonus"]
    teal_room_score = 5.0 + max(0.0, 1.5 - entry_simplicity) + title_signals["teal_bonus"]
    complexity_penalty = max(0.0, 3.0 - entry_simplicity) + title_signals["complexity_bonus"]

    # First-pass recommendation
    if complexity_penalty >= 4.0 and teal_room_score >= pink_room_score:
        recommended_treatment = "later_teal"
    elif pink_room_score > teal_room_score + 0.5:
        recommended_treatment = "pink"
    elif teal_room_score > pink_room_score + 0.5:
        recommended_treatment = "teal"
    else:
        recommended_treatment = "either"

    # Top-ranked placeholder effects
    effects = []

    if recommended_treatment in {"pink", "either"}:
        effects.extend([
            {"effect_family": "pink_panther", "score": round(pink_room_score, 2)},
            {"effect_family": "pent_guardrail_decoration", "score": round(pink_room_score - 0.5, 2)},
        ])

    if recommended_treatment in {"teal", "either", "later_teal"}:
        effects.extend([
            {"effect_family": "stacked_thirds", "score": round(teal_room_score, 2)},
            {"effect_family": "tertian_extension_climb", "score": round(teal_room_score - 0.5, 2)},
        ])

    effects = sorted(effects, key=lambda x: x["score"], reverse=True)

    return {
        "pink_room_score": round(pink_room_score, 2),
        "teal_room_score": round(teal_room_score, 2),
        "complexity_penalty": round(complexity_penalty, 2),
        "recommended_treatment": recommended_treatment,
        "top_ranked_effects": effects[:3],
    }


def build_manifest_lookup() -> Dict[str, Dict]:
    rows = load_csv_rows(SPLIT_MANIFEST_CSV)
    lookup = {}
    for row in rows:
        title_slug = os.path.splitext(row["file"])[0]
        lookup[title_slug] = row
    return lookup


def main() -> None:
    manifest_lookup = build_manifest_lookup()

    scored_rows = []
    scored_json = []

    for filename in sorted(os.listdir(ANALYSIS_DIR)):
        if not filename.endswith(".json"):
            continue
        if filename == "measure_summary.json":
            continue

        slug = os.path.splitext(filename)[0]
        analysis_path = os.path.join(ANALYSIS_DIR, filename)
        analysis = load_json(analysis_path)

        manifest_row = manifest_lookup.get(slug, {})
        title = analysis.get("title", slug)
        page_count = safe_int(analysis.get("page_count", manifest_row.get("page_count", 0)), 0)

        scores = derive_scores(title=title, page_count=page_count)

        row = {
            "title": title,
            "slug": slug,
            "page_count": page_count,
            "pink_room_score": scores["pink_room_score"],
            "teal_room_score": scores["teal_room_score"],
            "complexity_penalty": scores["complexity_penalty"],
            "recommended_treatment": scores["recommended_treatment"],
            "top_effect_1": scores["top_ranked_effects"][0]["effect_family"] if len(scores["top_ranked_effects"]) > 0 else "",
            "top_effect_1_score": scores["top_ranked_effects"][0]["score"] if len(scores["top_ranked_effects"]) > 0 else "",
            "top_effect_2": scores["top_ranked_effects"][1]["effect_family"] if len(scores["top_ranked_effects"]) > 1 else "",
            "top_effect_2_score": scores["top_ranked_effects"][1]["score"] if len(scores["top_ranked_effects"]) > 1 else "",
            "top_effect_3": scores["top_ranked_effects"][2]["effect_family"] if len(scores["top_ranked_effects"]) > 2 else "",
            "top_effect_3_score": scores["top_ranked_effects"][2]["score"] if len(scores["top_ranked_effects"]) > 2 else "",
        }

        scored_rows.append(row)
        scored_json.append({
            **row,
            "top_ranked_effects": scores["top_ranked_effects"],
        })

    # Sort by best first-pass usefulness:
    scored_rows.sort(key=lambda r: (-float(r["pink_room_score"]), float(r["complexity_penalty"])))
    scored_json.sort(key=lambda r: (-float(r["pink_room_score"]), float(r["complexity_penalty"])))

    csv_path = os.path.join(OUTPUT_DIR, "spacegrass_scored_inventory.csv")
    json_path = os.path.join(OUTPUT_DIR, "spacegrass_scored_inventory.json")

    fieldnames = [
        "title",
        "slug",
        "page_count",
        "pink_room_score",
        "teal_room_score",
        "complexity_penalty",
        "recommended_treatment",
        "top_effect_1",
        "top_effect_1_score",
        "top_effect_2",
        "top_effect_2_score",
        "top_effect_3",
        "top_effect_3_score",
    ]

    write_csv(csv_path, fieldnames, scored_rows)
    write_json(json_path, scored_json)

    print("\nScored inventory written to:")
    print(csv_path)
    print(json_path)

    print("\nTop first-pass candidates:")
    for row in scored_rows[:5]:
        print(
            f"{row['title']:<20} "
            f"pink={row['pink_room_score']:<4} "
            f"teal={row['teal_room_score']:<4} "
            f"complexity={row['complexity_penalty']:<4} "
            f"mode={row['recommended_treatment']}"
        )


if __name__ == "__main__":
    main()