import os
import json
import csv
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

print("RUNNING TREATMENT_SCORER v1")

BASE_DIR = os.path.dirname(__file__)
INPUT_DIR = os.path.join(BASE_DIR, "analysis", "harmonic_streams")
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis", "treatment_scores")

os.makedirs(OUTPUT_DIR, exist_ok=True)

NOTE_TO_PC = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "F": 5, "E#": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}

PC_TO_SHARP = {
    0: "C", 1: "C#", 2: "D", 3: "Eb", 4: "E", 5: "F",
    6: "F#", 7: "G", 8: "Ab", 9: "A", 10: "Bb", 11: "B"
}

MAJOR_DEGREE_TO_PC_OFFSET = {
    "I": 0,
    "bII": 1,
    "II": 2,
    "bIII": 3,
    "III": 4,
    "IV": 5,
    "#IV": 6,
    "bV": 6,
    "V": 7,
    "bVI": 8,
    "VI": 9,
    "bVII": 10,
    "VII": 11,
}

COMMON_MAJOR_DEGREES = ["I", "ii", "iii", "IV", "V", "vi", "vii°"]


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def parse_chord(chord: str) -> Dict[str, str]:
    """
    Very lightweight chord parser.
    Examples:
      G -> root G, quality ""
      Am7 -> root A, quality m7
      Bb6/9 -> root Bb, quality 6/9
      F/G -> root F, quality /G
      Dm9 -> root D, quality m9
    """
    chord = chord.strip()
    if not chord:
        return {"root": "", "quality": ""}

    root = chord[0]
    rest = chord[1:]

    if rest.startswith("#") or rest.startswith("b"):
        root += rest[0]
        rest = rest[1:]

    return {"root": root, "quality": rest}


def root_to_pc(root: str) -> Optional[int]:
    return NOTE_TO_PC.get(root)


def chord_root_pc(chord: str) -> Optional[int]:
    parsed = parse_chord(chord)
    return root_to_pc(parsed["root"])


def is_minor_quality(quality: str) -> bool:
    return quality.startswith("m") and not quality.startswith("maj")


def is_dominant_quality(quality: str) -> bool:
    return quality.startswith("7") or quality.startswith("9") or quality.startswith("11") or quality.startswith("13")


def is_dim_quality(quality: str) -> bool:
    return "dim" in quality or "°" in quality


def infer_major_key(stream: List[str]) -> Dict[str, Any]:
    """
    Heuristic major-key inference:
    test all 12 tonics and reward:
    - frequent I, IV, V roots
    - repeated V->I motion
    - tonic prevalence
    """
    if not stream:
        return {
            "key_root": None,
            "key_name": None,
            "confidence": 0.0,
            "scores": []
        }

    root_pcs = [chord_root_pc(ch) for ch in stream]
    root_pcs = [pc for pc in root_pcs if pc is not None]

    if not root_pcs:
        return {
            "key_root": None,
            "key_name": None,
            "confidence": 0.0,
            "scores": []
        }

    candidate_scores = []

    for tonic_pc in range(12):
        tonic_count = 0
        subdom_count = 0
        dom_count = 0
        cadential_count = 0
        vi_count = 0

        for i, pc in enumerate(root_pcs):
            degree_offset = (pc - tonic_pc) % 12

            if degree_offset == 0:
                tonic_count += 1
            elif degree_offset == 5:
                subdom_count += 1
            elif degree_offset == 7:
                dom_count += 1
            elif degree_offset == 9:
                vi_count += 1

            if i < len(root_pcs) - 1:
                nxt = root_pcs[i + 1]
                if degree_offset == 7 and ((nxt - tonic_pc) % 12) == 0:
                    cadential_count += 1

        score = (
            tonic_count * 3.0 +
            subdom_count * 1.8 +
            dom_count * 2.2 +
            cadential_count * 4.5 +
            vi_count * 0.8
        )

        candidate_scores.append({
            "tonic_pc": tonic_pc,
            "key_name": PC_TO_SHARP[tonic_pc],
            "score": score,
            "tonic_count": tonic_count,
            "subdom_count": subdom_count,
            "dom_count": dom_count,
            "cadential_count": cadential_count,
            "vi_count": vi_count,
        })

    candidate_scores.sort(key=lambda x: x["score"], reverse=True)
    best = candidate_scores[0]
    second = candidate_scores[1] if len(candidate_scores) > 1 else {"score": 0.0}

    confidence = 0.0
    if best["score"] > 0:
        confidence = round((best["score"] - second["score"]) / best["score"], 3)

    return {
        "key_root": best["tonic_pc"],
        "key_name": best["key_name"],
        "confidence": confidence,
        "scores": candidate_scores[:5],
    }


def classify_degree_major(chord: str, tonic_pc: Optional[int]) -> Dict[str, Any]:
    if tonic_pc is None:
        return {
            "degree": None,
            "functional_bucket": "unknown",
            "root": parse_chord(chord)["root"],
            "quality": parse_chord(chord)["quality"],
        }

    parsed = parse_chord(chord)
    pc = root_to_pc(parsed["root"])
    if pc is None:
        return {
            "degree": None,
            "functional_bucket": "unknown",
            "root": parsed["root"],
            "quality": parsed["quality"],
        }

    offset = (pc - tonic_pc) % 12

    degree_lookup = {
        0: "I",
        1: "bII",
        2: "II",
        3: "bIII",
        4: "III",
        5: "IV",
        6: "#IV/bV",
        7: "V",
        8: "bVI",
        9: "VI",
        10: "bVII",
        11: "VII",
    }
    degree = degree_lookup[offset]

    if degree == "I":
        bucket = "tonic"
    elif degree == "IV":
        bucket = "subdominant"
    elif degree == "V":
        bucket = "dominant"
    else:
        bucket = "color_or_other"

    return {
        "degree": degree,
        "functional_bucket": bucket,
        "root": parsed["root"],
        "quality": parsed["quality"],
    }


def build_moment_annotations(stream: List[str], key_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    tonic_pc = key_info["key_root"]
    annotations = []

    for i, chord in enumerate(stream):
        info = classify_degree_major(chord, tonic_pc)
        degree = info["degree"]
        bucket = info["functional_bucket"]

        prev_chord = stream[i - 1] if i > 0 else None
        next_chord = stream[i + 1] if i < len(stream) - 1 else None

        prev_info = classify_degree_major(prev_chord, tonic_pc) if prev_chord else None
        next_info = classify_degree_major(next_chord, tonic_pc) if next_chord else None

        treatment = "neutral"
        rationale = []
        confidence = 0.5

        # Dominant -> tonic arrival is a pink setup
        if degree == "V":
            treatment = "pink"
            rationale.append("dominant chord invites tension / superimposed color")
            confidence = 0.88

            if next_info and next_info["degree"] == "I":
                rationale.append("direct V→I cadence makes pink tension especially useful")
                confidence = 0.94

        # IV in simple I-IV-V space often gives nice teal extension room
        elif degree == "IV":
            treatment = "teal"
            rationale.append("subdominant plateau leaves room for extension climbing")
            confidence = 0.78

            if next_info and next_info["degree"] in {"I", "V"}:
                rationale.append("IV moving back into the home loop favors shape-based teal phrasing")
                confidence = 0.83

        # I is a strong teal home base
        elif degree == "I":
            treatment = "teal"
            rationale.append("tonic stability supports teal extension framing and melodic climbing")
            confidence = 0.86

            if prev_info and prev_info["degree"] == "V":
                rationale.append("post-cadential tonic is a strong teal arrival zone")
                confidence = 0.92

        else:
            treatment = "hybrid"
            rationale.append("non-core function may support mixed color depending on phrase target")
            confidence = 0.62

        annotations.append({
            "moment_index": i,
            "chord": chord,
            "degree": degree,
            "functional_bucket": bucket,
            "recommended_treatment": treatment,
            "confidence": round(confidence, 3),
            "rationale": rationale,
        })

    return annotations


def score_treatments(stream: List[str], key_info: Dict[str, Any], harmonic_cells: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not stream:
        return {
            "pink_score": 0,
            "teal_score": 0,
            "hybrid_score": 0,
            "recommended_primary_treatment": "unknown",
            "reasoning": [],
        }

    unique_count = len(set(stream))
    total_count = len(stream)

    degrees = [classify_degree_major(ch, key_info["key_root"])["degree"] for ch in stream]
    tonic_count = sum(1 for d in degrees if d == "I")
    subdom_count = sum(1 for d in degrees if d == "IV")
    dom_count = sum(1 for d in degrees if d == "V")

    cadence_count = 0
    for i in range(len(degrees) - 1):
        if degrees[i] == "V" and degrees[i + 1] == "I":
            cadence_count += 1

    repeated_cell_strength = 0
    for cell in harmonic_cells:
        repeated_cell_strength += max(0, cell["count"] - 1)

    reasoning = []

    # TEAL
    teal = 0.0
    if unique_count <= 3:
        teal += 4.0
        reasoning.append("few unique chords increases teal room")
    elif unique_count <= 5:
        teal += 2.5
        reasoning.append("moderately limited harmonic palette supports teal")
    else:
        teal += 0.5

    teal += min(3.0, tonic_count * 0.35)
    teal += min(2.0, subdom_count * 0.25)
    teal += min(2.0, repeated_cell_strength * 0.2)

    if cadence_count >= 2:
        teal += 1.2
        reasoning.append("stable repeating cadence loop supports teal extension frameworks")

    # PINK
    pink = 0.0
    pink += min(3.0, dom_count * 0.5)
    pink += min(3.0, cadence_count * 0.9)

    if unique_count <= 4:
        pink += 1.6
        reasoning.append("simple harmony leaves room for pink superimposition without harmonic overload")

    if repeated_cell_strength >= 3:
        pink += 1.4
        reasoning.append("repeating cells create repeatable pink insertion windows")

    # HYBRID
    hybrid = min(pink, teal) + 1.0 if pink > 0 and teal > 0 else 0.0

    pink_score = round(min(10.0, pink), 2)
    teal_score = round(min(10.0, teal), 2)
    hybrid_score = round(min(10.0, hybrid), 2)

    if teal_score >= pink_score + 1.25:
        primary = "teal"
    elif pink_score >= teal_score + 1.25:
        primary = "pink"
    else:
        primary = "hybrid"

    return {
        "pink_score": pink_score,
        "teal_score": teal_score,
        "hybrid_score": hybrid_score,
        "recommended_primary_treatment": primary,
        "reasoning": reasoning,
        "stats": {
            "unique_count": unique_count,
            "total_count": total_count,
            "tonic_count": tonic_count,
            "subdominant_count": subdom_count,
            "dominant_count": dom_count,
            "cadence_count": cadence_count,
            "repeated_cell_strength": repeated_cell_strength,
        }
    }


def build_lead_sheet_annotation_plan(moment_annotations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    This is the bridge to later lead-sheet stamping.
    For now it emits a compact per-moment tag list.
    """
    tags = []

    for m in moment_annotations:
        treatment = m["recommended_treatment"]

        if treatment == "pink":
            short_tag = "PINK"
        elif treatment == "teal":
            short_tag = "TEAL"
        else:
            short_tag = "HYBRID"

        tags.append({
            "moment_index": m["moment_index"],
            "chord": m["chord"],
            "tag": short_tag,
            "confidence": m["confidence"],
        })

    return {
        "annotation_tags": tags
    }


def process_file(path: str) -> Dict[str, Any]:
    data = load_json(path)

    title = data.get("title")
    stream = data.get("harmonic_stream", [])
    harmonic_cells = data.get("harmonic_cells", [])

    key_info = infer_major_key(stream)
    moment_annotations = build_moment_annotations(stream, key_info)
    treatment_scores = score_treatments(stream, key_info, harmonic_cells)
    lead_sheet_plan = build_lead_sheet_annotation_plan(moment_annotations)

    return {
        "title": title,
        "key_inference": key_info,
        "harmonic_stream": stream,
        "unique_chords": data.get("unique_chords", []),
        "harmonic_cells": harmonic_cells,
        "treatment_scores": treatment_scores,
        "moment_annotations": moment_annotations,
        "lead_sheet_annotation_plan": lead_sheet_plan,
    }


def write_summary_csv(results: List[Dict[str, Any]], path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title",
                "key_name",
                "key_confidence",
                "pink_score",
                "teal_score",
                "hybrid_score",
                "recommended_primary_treatment",
            ]
        )
        writer.writeheader()

        for r in results:
            writer.writerow({
                "title": r["title"],
                "key_name": r["key_inference"]["key_name"],
                "key_confidence": r["key_inference"]["confidence"],
                "pink_score": r["treatment_scores"]["pink_score"],
                "teal_score": r["treatment_scores"]["teal_score"],
                "hybrid_score": r["treatment_scores"]["hybrid_score"],
                "recommended_primary_treatment": r["treatment_scores"]["recommended_primary_treatment"],
            })


def main() -> None:
    results = []

    for filename in sorted(os.listdir(INPUT_DIR)):
        if not filename.endswith("_harmonic_stream.json"):
            continue
        if filename == "all_harmonic_streams.json":
            continue

        path = os.path.join(INPUT_DIR, filename)
        result = process_file(path)
        results.append(result)

        out_name = filename.replace("_harmonic_stream.json", "_treatment_score.json")
        out_path = os.path.join(OUTPUT_DIR, out_name)
        save_json(out_path, result)

    all_path = os.path.join(OUTPUT_DIR, "all_treatment_scores.json")
    save_json(all_path, results)

    summary_csv_path = os.path.join(OUTPUT_DIR, "treatment_score_summary.csv")
    write_summary_csv(results, summary_csv_path)

    print("\nSaved treatment score files to:")
    print(OUTPUT_DIR)
    print("\nSummary CSV:")
    print(summary_csv_path)


if __name__ == "__main__":
    main()