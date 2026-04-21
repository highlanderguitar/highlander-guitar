import os
import json
import csv
from typing import Any, Dict, List

print("RUNNING LEAD_SHEET_TREATMENT_EXPORTER v1")

BASE_DIR = os.path.dirname(__file__)
INPUT_DIR = os.path.join(BASE_DIR, "analysis", "treatment_scores")
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis", "lead_sheet_exports")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def compact_rationale(moment: Dict[str, Any]) -> str:
    rationale = moment.get("rationale", [])
    if not rationale:
        return ""
    return " | ".join(rationale)


def build_export_rows(score_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    title = score_data.get("title", "")
    key_name = score_data.get("key_inference", {}).get("key_name", "")
    primary_treatment = score_data.get("treatment_scores", {}).get(
        "recommended_primary_treatment", ""
    )

    moment_annotations = score_data.get("moment_annotations", [])
    rows: List[Dict[str, Any]] = []

    for moment in moment_annotations:
        row = {
            "title": title,
            "key_name": key_name,
            "primary_treatment": primary_treatment,
            "moment_index": moment.get("moment_index"),
            "chord": moment.get("chord"),
            "degree": moment.get("degree"),
            "functional_bucket": moment.get("functional_bucket"),
            "recommended_treatment": moment.get("recommended_treatment"),
            "confidence": moment.get("confidence"),
            "rationale": compact_rationale(moment),
        }
        rows.append(row)

    return rows


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "title",
        "key_name",
        "primary_treatment",
        "moment_index",
        "chord",
        "degree",
        "functional_bucket",
        "recommended_treatment",
        "confidence",
        "rationale",
    ]

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_compact_annotation_sheet(score_data: Dict[str, Any]) -> Dict[str, Any]:
    title = score_data.get("title", "")
    key_info = score_data.get("key_inference", {})
    treatment_scores = score_data.get("treatment_scores", {})
    tags = score_data.get("lead_sheet_annotation_plan", {}).get("annotation_tags", [])

    compact = {
        "title": title,
        "key_name": key_info.get("key_name"),
        "key_confidence": key_info.get("confidence"),
        "pink_score": treatment_scores.get("pink_score"),
        "teal_score": treatment_scores.get("teal_score"),
        "hybrid_score": treatment_scores.get("hybrid_score"),
        "recommended_primary_treatment": treatment_scores.get("recommended_primary_treatment"),
        "annotation_tags": tags,
    }
    return compact


def process_file(path: str) -> Dict[str, Any]:
    score_data = load_json(path)
    rows = build_export_rows(score_data)
    compact = build_compact_annotation_sheet(score_data)

    title = score_data.get("title", "untitled")

    csv_path = os.path.join(OUTPUT_DIR, f"{title}_lead_sheet_treatment_map.csv")
    json_path = os.path.join(OUTPUT_DIR, f"{title}_lead_sheet_treatment_map.json")

    write_csv(csv_path, rows)
    save_json(json_path, compact)

    return {
        "title": title,
        "csv_path": csv_path,
        "json_path": json_path,
        "row_count": len(rows),
    }


def main() -> None:
    manifest: List[Dict[str, Any]] = []

    for filename in sorted(os.listdir(INPUT_DIR)):
        if not filename.endswith("_treatment_score.json"):
            continue
        if filename == "all_treatment_scores.json":
            continue

        path = os.path.join(INPUT_DIR, filename)
        result = process_file(path)
        manifest.append(result)

    manifest_path = os.path.join(OUTPUT_DIR, "lead_sheet_treatment_export_manifest.json")
    save_json(manifest_path, manifest)

    print("\nSaved lead-sheet treatment exports to:")
    print(OUTPUT_DIR)
    print("\nManifest:")
    print(manifest_path)


if __name__ == "__main__":
    main()