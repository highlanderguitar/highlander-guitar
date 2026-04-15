import os
import json
import fitz  # PyMuPDF
import re

INPUT_DIR = os.path.join(os.path.dirname(__file__), "input")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "analysis")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def detect_staff_lines(page_text):
    """
    Rough heuristic:
    Count clusters of staff-like patterns (clefs, barlines, repeated symbols)
    """
    lines = page_text.split("\n")

    staff_candidates = []
    for line in lines:
        if len(line.strip()) < 3:
            continue

        # crude filters for notation density
        if any(sym in line for sym in ["|", "𝄞", "𝄢", "♩", "♪", "♭", "#"]):
            staff_candidates.append(line)

    return len(staff_candidates)


def estimate_measures_from_text(page_text):
    """
    Heuristic:
    Count barline-like symbols
    """
    barline_count = page_text.count("|")

    # fallback if PDF encoding is weird
    if barline_count == 0:
        barline_count = len(re.findall(r'\b\d+\b', page_text))

    return barline_count


def analyze_pdf(pdf_path):
    doc = fitz.open(pdf_path)

    total_measures = 0
    systems = 0
    bars_per_page = []

    for page in doc:
        text = page.get_text()

        staff_count = detect_staff_lines(text)
        systems += staff_count

        measure_est = estimate_measures_from_text(text)
        total_measures += measure_est

        bars_per_page.append(measure_est)

    doc.close()

    confidence = min(1.0, (systems * 0.1 + total_measures * 0.01))

    return {
        "page_count": len(bars_per_page),
        "estimated_measure_count": total_measures,
        "systems_detected": systems,
        "bars_per_page": bars_per_page,
        "confidence": round(confidence, 2)
    }


def main():
    results = []

    for filename in os.listdir(INPUT_DIR):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(INPUT_DIR, filename)
        title = os.path.splitext(filename)[0]

        print(f"Analyzing: {filename}")

        analysis = analyze_pdf(pdf_path)

        output_data = {
            "title": title,
            **analysis
        }

        results.append(output_data)

        # write per-file JSON
        out_path = os.path.join(OUTPUT_DIR, f"{title}.json")
        with open(out_path, "w") as f:
            json.dump(output_data, f, indent=4)

    # write summary JSON
    summary_path = os.path.join(OUTPUT_DIR, "measure_summary.json")
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=4)

    print("\nSaved analysis to:")
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()