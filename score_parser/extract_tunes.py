import os
import re
import csv
import json
import argparse
from typing import List, Dict, Tuple
import fitz  # PyMuPDF

# ----------------------------
# ROOTS
# ----------------------------

SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

DEFAULT_INPUT_DIR = os.path.join(SCRIPT_DIR, "input_pdf")
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# ----------------------------
# UTIL
# ----------------------------

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def save_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def normalize_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]

# ----------------------------
# NORMALIZATION
# ----------------------------

GLYPH_MAP = {
    "": "b",   # flat
    "": "#",   # sharp variant
    "": "#",   # sharp variant
    "": "#",   # accidental glyph seen earlier
    "": "",
    "": "",
    "": "",
    "": "",
    "": "",
    "": "",
    "": "",
    "": "",
    "": "",
    "": "",
    "": "",
    "": "",
    "": "",
}

def normalize_text(raw: str) -> str:
    out = raw
    for k, v in GLYPH_MAP.items():
        out = out.replace(k, v)

    out = out.replace("\u00a0", " ")

    # collapse duplicate chord tokens
    out = re.sub(
        r"\b([A-G][#b]?(?:m|maj|min|dim|aug|sus)?\d*(?:\/\d+)?)\s+\1\b",
        r"\1",
        out,
    )

    # normalize dotted leaders
    out = re.sub(r"[.·•]{2,}", " ... ", out)

    # normalize whitespace
    out = re.sub(r"[ \t]+", " ", out)

    return out

# ----------------------------
# CONTENTS PARSING
# ----------------------------

TITLE_REJECT_PATTERNS = [
    r"^contents?$",
    r"^standard tuning$",
    r"^capo",
    r"^as performed by",
    r"^tony rice$",
    r"^john reischman$",
    r"^\d+$",
]

def looks_like_bad_title(line: str) -> bool:
    s = line.strip().lower()
    if not s:
        return True

    for pat in TITLE_REJECT_PATTERNS:
        if re.search(pat, s):
            return True

    # reject lines that are mostly symbols / notation junk
    alpha_count = sum(ch.isalpha() for ch in s)
    if alpha_count == 0:
        return True

    return False

def clean_title_candidate(title: str) -> str:
    t = title.strip()

    # remove trailing dotted leaders
    t = re.sub(r"\s*(?:\.{2,}|\. \. \.)\s*$", "", t)

    # collapse spaces
    t = re.sub(r"\s+", " ", t).strip()

    return t

def extract_inventory_from_lines(lines: List[str]) -> Tuple[List[Dict], List[Dict]]:
    """
    More robust contents parser.

    Supports:
    1) alternating lines:
         Title
         12

    2) inline:
         Title 12
         Title .... 12
         Title ... 12
    """
    rows: List[Dict] = []
    debug_matches: List[Dict] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Pattern A: inline title + page number on same line
        m_inline = re.match(r"^(?P<title>.+?)\s*(?:\.{2,}|\. \. \.)?\s*(?P<page>\d{1,3})$", line)
        if m_inline:
            title = clean_title_candidate(m_inline.group("title"))
            page = int(m_inline.group("page"))

            if not looks_like_bad_title(title):
                rows.append({
                    "title": title,
                    "start_page": page,
                })
                debug_matches.append({
                    "mode": "inline",
                    "raw_line": line,
                    "title": title,
                    "start_page": page,
                })
                i += 1
                continue

        # Pattern B: alternating title line then page line
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if re.fullmatch(r"\d{1,3}", next_line):
                title = clean_title_candidate(line)
                page = int(next_line)

                if not looks_like_bad_title(title):
                    rows.append({
                        "title": title,
                        "start_page": page,
                    })
                    debug_matches.append({
                        "mode": "two_line",
                        "raw_line": f"{line} || {next_line}",
                        "title": title,
                        "start_page": page,
                    })
                    i += 2
                    continue

        i += 1

    # Deduplicate exact title/page repeats while preserving order
    deduped_rows: List[Dict] = []
    seen = set()
    for row in rows:
        key = (row["title"], row["start_page"])
        if key not in seen:
            seen.add(key)
            deduped_rows.append(row)

    return deduped_rows, debug_matches

def extract_inventory_from_contents(contents_text: str) -> Tuple[List[Dict], Dict]:
    lines = normalize_lines(contents_text)
    rows, matches = extract_inventory_from_lines(lines)

    debug = {
        "line_count": len(lines),
        "lines": lines,
        "matches": matches,
        "row_count": len(rows),
    }
    return rows, debug

def save_inventory_csv(path: str, rows: List[Dict]) -> None:
    fieldnames = [
        "title",
        "start_page",
        "pink_room_score",
        "teal_room_score",
        "complexity_penalty",
        "recommended_treatment",
        "notes",
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
                "notes": "",
            })

# ----------------------------
# CORE PIPELINE
# ----------------------------

def process_pdf(
    pdf_path: str,
    output_dir: str,
    tag: str,
    contents_start_index: int,
    contents_end_index: int,
):
    ensure_dir(output_dir)

    doc = fitz.open(pdf_path)

    raw_pages = []
    norm_pages = []

    for i, page in enumerate(doc):
        raw = page.get_text()
        norm = normalize_text(raw)

        raw_pages.append({
            "page_index": i,
            "text": raw,
        })

        norm_pages.append({
            "page_index": i,
            "text": norm,
        })

        raw_path = os.path.join(output_dir, f"{tag}_page_{i+1:03d}_raw.txt")
        norm_path = os.path.join(output_dir, f"{tag}_page_{i+1:03d}_norm.txt")

        save_text(raw_path, raw)
        save_text(norm_path, norm)

    save_text(
        os.path.join(output_dir, f"{tag}_all_raw.txt"),
        "\n\n".join(p["text"] for p in raw_pages)
    )

    save_text(
        os.path.join(output_dir, f"{tag}_all_norm.txt"),
        "\n\n".join(p["text"] for p in norm_pages)
    )

    save_json(os.path.join(output_dir, f"{tag}_pages_raw.json"), raw_pages)
    save_json(os.path.join(output_dir, f"{tag}_pages_norm.json"), norm_pages)

    if contents_start_index < 0 or contents_start_index >= len(raw_pages):
        raise IndexError(
            f"contents_start_index={contents_start_index} out of range for PDF with {len(raw_pages)} pages."
        )

    if contents_end_index < contents_start_index or contents_end_index >= len(raw_pages):
        raise IndexError(
            f"contents_end_index={contents_end_index} invalid for start={contents_start_index} and PDF with {len(raw_pages)} pages."
        )

    contents_raw_parts = []
    contents_norm_parts = []

    for idx in range(contents_start_index, contents_end_index + 1):
        contents_raw_parts.append(f"--- PAGE {idx + 1} ---\n{raw_pages[idx]['text']}")
        contents_norm_parts.append(f"--- PAGE {idx + 1} ---\n{norm_pages[idx]['text']}")

    contents_raw = "\n\n".join(contents_raw_parts)
    contents_norm = "\n\n".join(contents_norm_parts)

    save_text(os.path.join(output_dir, f"{tag}_contents_raw.txt"), contents_raw)
    save_text(os.path.join(output_dir, f"{tag}_contents_norm.txt"), contents_norm)

    rows, debug = extract_inventory_from_contents(contents_norm)

    save_json(os.path.join(output_dir, f"{tag}_contents_parse_debug.json"), debug)

    csv_path = os.path.join(output_dir, f"{tag}_tune_inventory_seed.csv")
    save_inventory_csv(csv_path, rows)

    doc.close()
    return rows, csv_path, debug

# ----------------------------
# ARGPARSE
# ----------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract tune inventory and debug text from a PDF tune book."
    )

    parser.add_argument(
        "--pdf",
        required=True,
        help="Full path to source PDF."
    )

    parser.add_argument(
        "--tag",
        required=True,
        help="Stable tag for output filenames, e.g. spacegrass or unofficial_tr_marcel."
    )

    parser.add_argument(
        "--output-subdir",
        default="",
        help="Optional subdirectory inside score_parser/output."
    )

    parser.add_argument(
        "--contents-start-index",
        type=int,
        default=3,
        help="Zero-based first PDF page index to scan as contents."
    )

    parser.add_argument(
        "--contents-end-index",
        type=int,
        default=3,
        help="Zero-based last PDF page index to scan as contents."
    )

    return parser.parse_args()

# ----------------------------
# ENTRY
# ----------------------------

def main():
    args = parse_args()

    pdf_path = args.pdf
    tag = args.tag
    output_dir = os.path.join(DEFAULT_OUTPUT_DIR, args.output_subdir) if args.output_subdir else DEFAULT_OUTPUT_DIR

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    ensure_dir(output_dir)

    print(f"\nProcessing PDF:\n{pdf_path}\n")
    print(f"Tag: {tag}")
    print(f"Output dir: {output_dir}")
    print(f"Contents page scan: {args.contents_start_index} -> {args.contents_end_index}\n")

    rows, csv_path, debug = process_pdf(
        pdf_path=pdf_path,
        output_dir=output_dir,
        tag=tag,
        contents_start_index=args.contents_start_index,
        contents_end_index=args.contents_end_index,
    )

    print("Saved outputs to:")
    print(output_dir)
    print("\nDetected contents matches:\n")

    for m in debug["matches"]:
        print(f"{m['start_page']:>3}  {m['title']}  [{m['mode']}]")

    print(f"\nRow count: {debug['row_count']}")
    print(f"CSV:\n{csv_path}")
    print(f"Debug JSON:\n{os.path.join(output_dir, f'{tag}_contents_parse_debug.json')}\n")

    if not rows:
        print("WARNING: No tune rows were extracted.")
        print("Open the contents debug files and adjust the contents page scan range if needed.")

if __name__ == "__main__":
    main()