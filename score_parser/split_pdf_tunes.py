import os
import re
import csv
import argparse
from typing import List, Dict, Optional, Tuple
import fitz  # PyMuPDF

print("RUNNING SPLIT_PDF_TUNES v3")

# --------------------------------------------------
# ROOTS
# --------------------------------------------------

SCRIPT_DIR = os.path.dirname(__file__)
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def safe_strip(value) -> str:
    if value is None:
        return ""
    return str(value).strip()

def slugify(title: str) -> str:
    s = safe_strip(title).lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def normalize_text(text: str) -> str:
    text = safe_strip(text)
    text = text.replace("\u2019", "'")
    text = text.replace("\u2018", "'")
    text = text.replace("\u201c", '"')
    text = text.replace("\u201d", '"')
    text = text.replace("\u2013", "-")
    text = text.replace("\u2014", "-")
    text = text.replace("\u00a0", " ")
    text = text.replace("\u00ad", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_title(title: str) -> str:
    """
    Keep digits because titles like Opus 57 and Swing 51 matter.
    """
    t = normalize_text(title).lower()
    t = t.replace("&", "and")
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def try_parse_int(value: str) -> Optional[int]:
    value = safe_strip(value)
    if not value:
        return None

    m = re.match(r"^(\d+)", value)
    if not m:
        return None
    return int(m.group(1))

def read_inventory(csv_path: str) -> List[Dict]:
    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = safe_strip(row.get("title"))
            if not title:
                continue

            start_page_raw = safe_strip(row.get("start_page"))
            notes = safe_strip(row.get("notes"))

            rows.append({
                "title": title,
                "title_norm": normalize_title(title),
                "start_page_raw": start_page_raw,
                "start_page_hint": try_parse_int(start_page_raw),
                "notes": notes,
            })
    return rows

def save_manifest(path: str, written: List[Dict]) -> None:
    fieldnames = [
        "title",
        "file",
        "path",
        "title_page_doc_index",
        "end_doc_index",
        "page_count",
        "title_anchor_found",
        "used_hint_fallback",
        "shared_title_page_with_next",
        "status",
    ]

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in written:
            writer.writerow(row)

def save_shared_page_report(path: str, rows: List[Dict]) -> None:
    fieldnames = [
        "title",
        "title_page_doc_index",
        "next_title",
        "next_title_page_doc_index",
        "issue",
    ]

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

# --------------------------------------------------
# TITLE DETECTION
# --------------------------------------------------

def get_page_texts(doc: fitz.Document) -> List[str]:
    return [normalize_text(page.get_text()) for page in doc]

def compress(s: str) -> str:
    return re.sub(r"\s+", "", s.lower())

def title_found_on_page(title_norm: str, page_norm_text: str) -> bool:
    if not title_norm:
        return False

    page_norm = normalize_title(page_norm_text)

    # normal match
    if title_norm in page_norm:
        return True

    # compressed match (handles "MountainDew")
    if compress(title_norm) in compress(page_norm):
        return True

    return False

def find_title_page_near_hint(
    texts: List[str],
    title_norm: str,
    first_score_doc_index: int,
    hint_doc_index: Optional[int],
    search_window: int,
    search_floor: int,
) -> Tuple[Optional[int], bool]:
    """
    Returns:
        (page_index, used_hint_fallback)
    """
    if hint_doc_index is not None:
        start = max(first_score_doc_index, hint_doc_index - search_window)
        end = min(len(texts) - 1, hint_doc_index + search_window)
        for i in range(start, end + 1):
            if title_found_on_page(title_norm, texts[i]):
                return i, False

    forward_start = max(first_score_doc_index, search_floor)
    for i in range(forward_start, len(texts)):
        if title_found_on_page(title_norm, texts[i]):
            return i, True

    return None, False

def detect_title_pages(
    doc: fitz.Document,
    inventory_rows: List[Dict],
    first_score_doc_index: int,
    search_window: int,
) -> List[Dict]:
    texts = get_page_texts(doc)
    detected = []
    search_floor = first_score_doc_index

    for row in inventory_rows:
        hint_doc_index = None
        if row["start_page_hint"] is not None:
            hint_doc_index = first_score_doc_index + (row["start_page_hint"] - 1)

        title_page_doc_index, used_hint_fallback = find_title_page_near_hint(
            texts=texts,
            title_norm=row["title_norm"],
            first_score_doc_index=first_score_doc_index,
            hint_doc_index=hint_doc_index,
            search_window=search_window,
            search_floor=search_floor,
        )

        found = title_page_doc_index is not None

        if found:
            search_floor = title_page_doc_index

        detected.append({
            "title": row["title"],
            "title_norm": row["title_norm"],
            "start_page_raw": row["start_page_raw"],
            "start_page_hint": row["start_page_hint"],
            "title_page_doc_index": title_page_doc_index,
            "title_anchor_found": found,
            "used_hint_fallback": used_hint_fallback,
            "notes": row["notes"],
        })

    return detected

# --------------------------------------------------
# RANGE BUILDING
# --------------------------------------------------

def build_ranges(detected_rows: List[Dict], total_doc_pages: int) -> Tuple[List[Dict], List[Dict]]:
    shared_page_report = []
    exportable = []

    usable = [r for r in detected_rows if r["title_anchor_found"] and r["title_page_doc_index"] is not None]

    for i, row in enumerate(usable):
        start_doc_index = row["title_page_doc_index"]

        if i < len(usable) - 1:
            next_row = usable[i + 1]
            next_start = next_row["title_page_doc_index"]
        else:
            next_row = None
            next_start = total_doc_pages

        if next_row is not None and next_start == start_doc_index:
            end_doc_index = start_doc_index
            shared_with_next = True
            status = "shared_title_page"
            shared_page_report.append({
                "title": row["title"],
                "title_page_doc_index": start_doc_index,
                "next_title": next_row["title"],
                "next_title_page_doc_index": next_start,
                "issue": "two_titles_share_same_page",
            })
        else:
            end_doc_index = next_start - 1
            if end_doc_index < start_doc_index:
                end_doc_index = start_doc_index
            shared_with_next = False
            status = "ok"

        exportable.append({
            "title": row["title"],
            "slug": slugify(row["title"]),
            "title_page_doc_index": start_doc_index,
            "end_doc_index": end_doc_index,
            "page_count": end_doc_index - start_doc_index + 1,
            "title_anchor_found": True,
            "used_hint_fallback": row["used_hint_fallback"],
            "shared_title_page_with_next": shared_with_next,
            "status": status,
        })

    found_titles = {r["title"] for r in exportable}
    for row in detected_rows:
        if row["title"] not in found_titles and not row["title_anchor_found"]:
            exportable.append({
                "title": row["title"],
                "slug": slugify(row["title"]),
                "title_page_doc_index": "",
                "end_doc_index": "",
                "page_count": "",
                "title_anchor_found": False,
                "used_hint_fallback": False,
                "shared_title_page_with_next": False,
                "status": "title_anchor_not_found",
            })

    return exportable, shared_page_report

# --------------------------------------------------
# PDF WRITING
# --------------------------------------------------

def write_split_pdfs(pdf_path: str, ranges: List[Dict], dest_dir: str) -> List[Dict]:
    ensure_dir(dest_dir)
    src = fitz.open(pdf_path)
    written = []

    for item in ranges:
        row = {
            "title": item["title"],
            "file": "",
            "path": "",
            "title_page_doc_index": item["title_page_doc_index"],
            "end_doc_index": item["end_doc_index"],
            "page_count": item["page_count"],
            "title_anchor_found": item["title_anchor_found"],
            "used_hint_fallback": item["used_hint_fallback"],
            "shared_title_page_with_next": item["shared_title_page_with_next"],
            "status": item["status"],
        }

        if item["status"] == "title_anchor_not_found":
            written.append(row)
            continue

        if item["title_page_doc_index"] == "":
            written.append(row)
            continue

        out_doc = fitz.open()

        for page_index in range(item["title_page_doc_index"], item["end_doc_index"] + 1):
            out_doc.insert_pdf(src, from_page=page_index, to_page=page_index)

        if len(out_doc) == 0:
            row["status"] = "zero_pages_skipped"
            written.append(row)
            out_doc.close()
            continue

        out_name = f"{item['slug']}.pdf"
        out_path = os.path.join(dest_dir, out_name)

        out_doc.save(out_path)
        out_doc.close()

        row["file"] = out_name
        row["path"] = out_path
        written.append(row)

    src.close()
    return written

# --------------------------------------------------
# ARGPARSE
# --------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Split a tune-book PDF into per-tune PDFs using title-page anchors."
    )

    parser.add_argument(
        "--pdf",
        required=True,
        help="Full path to the source PDF."
    )

    parser.add_argument(
        "--inventory-csv",
        required=True,
        help="Full path to the tune inventory CSV created by extract_tunes.py."
    )

    parser.add_argument(
        "--dest-dir",
        required=True,
        help="Destination folder for split per-tune PDFs."
    )

    parser.add_argument(
        "--manifest-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where manifest/report CSVs will be written."
    )

    parser.add_argument(
        "--manifest-name",
        required=True,
        help="Filename for the manifest CSV."
    )

    parser.add_argument(
        "--shared-report-name",
        default="shared_page_tunes.csv",
        help="Filename for the shared-page review CSV."
    )

    parser.add_argument(
        "--first-score-doc-index",
        type=int,
        required=True,
        help="Zero-based first PDF page index that contains tune score pages."
    )

    parser.add_argument(
        "--search-window",
        type=int,
        default=2,
        help="How many pages around the contents hint to search first."
    )

    return parser.parse_args()

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    args = parse_args()

    pdf_path = args.pdf
    csv_path = args.inventory_csv
    dest_dir = args.dest_dir
    manifest_dir = args.manifest_dir
    manifest_name = args.manifest_name
    shared_report_name = args.shared_report_name
    first_score_doc_index = args.first_score_doc_index
    search_window = args.search_window

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    ensure_dir(dest_dir)
    ensure_dir(manifest_dir)

    inventory_rows = read_inventory(csv_path)
    if not inventory_rows:
        raise ValueError("No tune rows found in inventory CSV.")

    doc = fitz.open(pdf_path)

    if first_score_doc_index < 0 or first_score_doc_index >= len(doc):
        raise ValueError(
            f"--first-score-doc-index={first_score_doc_index} is invalid for a PDF with {len(doc)} pages."
        )

    detected_rows = detect_title_pages(
        doc=doc,
        inventory_rows=inventory_rows,
        first_score_doc_index=first_score_doc_index,
        search_window=search_window,
    )
    exportable_ranges, shared_page_report = build_ranges(detected_rows, len(doc))
    doc.close()

    written = write_split_pdfs(pdf_path, exportable_ranges, dest_dir)

    manifest_path = os.path.join(manifest_dir, manifest_name)
    shared_report_path = os.path.join(manifest_dir, shared_report_name)

    save_manifest(manifest_path, written)
    save_shared_page_report(shared_report_path, shared_page_report)

    print("\nCreated per-tune PDFs (title-page-anchor mode):\n")
    for row in written:
        file_name = row["file"] or "[no file]"
        page_count = row["page_count"] if row["page_count"] != "" else "-"
        print(
            f"{file_name:<34} "
            f"{str(page_count):<4} "
            f"{row['status']:<22} "
            f"{row['title']}"
        )

    print(f"\nManifest saved to:\n{manifest_path}")
    print(f"\nShared-page report saved to:\n{shared_report_path}")
    print(f"\nPer-tune PDFs saved in:\n{dest_dir}\n")

if __name__ == "__main__":
    main()