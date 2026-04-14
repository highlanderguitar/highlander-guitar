import os
import re
import csv
import json
import fitz  # PyMuPDF

# ----------------------------
# CONFIG
# ----------------------------

PROJECT_ROOT = r"C:\Users\highl\prism-archive\projects\_bootstrap\highlander_migration\highlander_render"
INPUT_DIR = os.path.join(PROJECT_ROOT, "score_parser", "input_pdf")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "score_parser", "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------
# UTIL
# ----------------------------

def list_pdfs(input_dir):
    return [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]

def save_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ----------------------------
# NORMALIZATION
# ----------------------------

GLYPH_MAP = {
    "": "b",   # flat
    "": "#",   # sharp (variant)
    "": "#",   # sharp (variant)
    "": "#",   # sharp (common in your sample)
    "": "",    # notation junk
    "": "",
    "": "",
    "": "",
    "": "",
    "": "",
}

def normalize_text(raw: str) -> str:
    out = raw
    for k, v in GLYPH_MAP.items():
        out = out.replace(k, v)

    # collapse duplicate chord tokens like "Dm Dm" → "Dm"
    out = re.sub(r"\b([A-G][#b]?(?:m|maj|min|dim|aug|sus)?\d*(?:\/\d+)?)\s+\1\b", r"\1", out)

    # clean excessive spaces
    out = re.sub(r"[ \t]+", " ", out)

    return out

# ----------------------------
# CONTENTS EXTRACTION
# ----------------------------

def normalize_lines(text):
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]

def extract_inventory_from_contents(text):
    lines = normalize_lines(text)

    rows = []
    i = 0
    while i < len(lines) - 1:
        title = lines[i]
        nxt = lines[i + 1]

        if re.fullmatch(r"\d+", nxt):
            rows.append({
                "title": title,
                "start_page": int(nxt)
            })
            i += 2
        else:
            i += 1

    return rows

def save_inventory_csv(path, rows):
    fieldnames = [
        "title",
        "start_page",
        "pink_room_score",
        "teal_room_score",
        "complexity_penalty",
        "recommended_treatment",
        "notes"
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in rows:
            writer.writerow({
                "title": r["title"],
                "start_page": r["start_page"],
                "pink_room_score": "",
                "teal_room_score": "",
                "complexity_penalty": "",
                "recommended_treatment": "",
                "notes": ""
            })

# ----------------------------
# MAIN PIPELINE
# ----------------------------

def process_pdf(pdf_path):
    base = os.path.splitext(os.path.basename(pdf_path))[0]

    doc = fitz.open(pdf_path)

    raw_pages = []
    norm_pages = []

    for i, page in enumerate(doc):
        raw = page.get_text()
        norm = normalize_text(raw)

        raw_pages.append({
            "page_index": i,
            "text": raw
        })

        norm_pages.append({
            "page_index": i,
            "text": norm
        })

        # Save per-page files (debuggable)
        raw_path = os.path.join(OUTPUT_DIR, f"{base}_page_{i+1:03d}_raw.txt")
        norm_path = os.path.join(OUTPUT_DIR, f"{base}_page_{i+1:03d}_norm.txt")

        save_text(raw_path, raw)
        save_text(norm_path, norm)

    # Save combined files
    save_text(os.path.join(OUTPUT_DIR, f"{base}_all_raw.txt"),
              "\n\n".join(p["text"] for p in raw_pages))

    save_text(os.path.join(OUTPUT_DIR, f"{base}_all_norm.txt"),
              "\n\n".join(p["text"] for p in norm_pages))

    save_json(os.path.join(OUTPUT_DIR, f"{base}_pages_raw.json"), raw_pages)
    save_json(os.path.join(OUTPUT_DIR, f"{base}_pages_norm.json"), norm_pages)

    # ----------------------------
    # CONTENTS PAGE (assume page 4 → index 3)
    # ----------------------------

    contents_index = 3
    contents_raw = raw_pages[contents_index]["text"]
    contents_norm = norm_pages[contents_index]["text"]

    save_text(os.path.join(OUTPUT_DIR, f"{base}_contents_raw.txt"), contents_raw)
    save_text(os.path.join(OUTPUT_DIR, f"{base}_contents_norm.txt"), contents_norm)

    rows = extract_inventory_from_contents(contents_norm)

    csv_path = os.path.join(OUTPUT_DIR, f"{base}_tune_inventory_seed.csv")
    save_inventory_csv(csv_path, rows)

    doc.close()

    return rows, csv_path

# ----------------------------
# ENTRY POINT
# ----------------------------

def main():
    pdfs = list_pdfs(INPUT_DIR)

    if not pdfs:
        raise FileNotFoundError(f"No PDFs found in: {INPUT_DIR}")

    pdf_path = os.path.join(INPUT_DIR, pdfs[0])

    print(f"\nProcessing PDF:\n{pdf_path}\n")

    rows, csv_path = process_pdf(pdf_path)

    print("Saved outputs to:")
    print(OUTPUT_DIR)
    print("\nExtracted tunes:\n")

    for r in rows:
        print(f"{r['start_page']:>3}  {r['title']}")

    print(f"\nCSV:\n{csv_path}\n")

if __name__ == "__main__":
    main()