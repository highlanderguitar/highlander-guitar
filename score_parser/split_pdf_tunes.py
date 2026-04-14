import os
import re
import csv
import fitz  # PyMuPDF

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

PROJECT_ROOT = r"C:\Users\highl\prism-archive\projects\_bootstrap\highlander_migration\highlander_render"
PDF_PATH = os.path.join(PROJECT_ROOT, "score_parser", "input_pdf", "spacegrass.pdf")
CSV_PATH = os.path.join(PROJECT_ROOT, "score_parser", "output", "spacegrass_tune_inventory_seed.csv")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "score_parser", "input")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def slugify(title: str) -> str:
    s = title.strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def read_inventory(csv_path: str):
    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row["title"].strip()
            start_page = int(row["start_page"])
            rows.append({
                "title": title,
                "start_page": start_page,
            })
    return rows

def compute_page_ranges(rows, total_score_pages: int):
    """
    Contents page numbers are score-relative, starting at 1 for the first tune page.
    In this PDF, the first tune starts on document page index 4 (human page 5).
    So:
        score page 1 -> doc index 4
        score page N -> doc index 4 + (N - 1)
    """
    SCORE_OFFSET_DOC_INDEX = 4

    enriched = []
    for i, row in enumerate(rows):
        start_score_page = row["start_page"]
        start_doc_index = SCORE_OFFSET_DOC_INDEX + (start_score_page - 1)

        if i < len(rows) - 1:
            next_start_score_page = rows[i + 1]["start_page"]
            end_doc_index = SCORE_OFFSET_DOC_INDEX + (next_start_score_page - 1) - 1
        else:
            end_doc_index = SCORE_OFFSET_DOC_INDEX + total_score_pages - 1

        enriched.append({
            "title": row["title"],
            "slug": slugify(row["title"]),
            "start_score_page": start_score_page,
            "start_doc_index": start_doc_index,
            "end_doc_index": end_doc_index,
        })

    return enriched

def split_pdf(pdf_path: str, ranges, output_dir: str):
    src = fitz.open(pdf_path)
    written = []

    for item in ranges:
        out_doc = fitz.open()

        for page_index in range(item["start_doc_index"], item["end_doc_index"] + 1):
            out_doc.insert_pdf(src, from_page=page_index, to_page=page_index)

        out_name = f"{item['slug']}.pdf"
        out_path = os.path.join(output_dir, out_name)
        out_doc.save(out_path)
        out_doc.close()

        written.append({
            "title": item["title"],
            "file": out_name,
            "path": out_path,
            "start_doc_index": item["start_doc_index"],
            "end_doc_index": item["end_doc_index"],
            "page_count": item["end_doc_index"] - item["start_doc_index"] + 1,
        })

    src.close()
    return written

def save_manifest(path: str, written):
    fieldnames = ["title", "file", "path", "start_doc_index", "end_doc_index", "page_count"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in written:
            writer.writerow(row)

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    inventory_rows = read_inventory(CSV_PATH)

    if not inventory_rows:
        raise ValueError("No tune rows found in CSV.")

    # Open source PDF to determine final page range
    src = fitz.open(PDF_PATH)
    total_doc_pages = len(src)

    # Score begins at doc index 4, so total score pages:
    total_score_pages = total_doc_pages - 4
    src.close()

    ranges = compute_page_ranges(inventory_rows, total_score_pages)
    written = split_pdf(PDF_PATH, ranges, OUTPUT_DIR)

    manifest_path = os.path.join(PROJECT_ROOT, "score_parser", "output", "spacegrass_split_manifest.csv")
    save_manifest(manifest_path, written)

    print("\nCreated per-tune PDFs:\n")
    for row in written:
        print(f"{row['file']:<24}  {row['page_count']} pages")

    print(f"\nManifest saved to:\n{manifest_path}\n")
    print(f"Per-tune PDFs saved in:\n{OUTPUT_DIR}\n")

if __name__ == "__main__":
    main()