import os
import re
import json
from typing import List, Dict, Any
import fitz  # PyMuPDF

BASE_DIR = os.path.dirname(__file__)
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis", "chord_symbols")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ----------------------------
# NORMALIZATION / FLAGS
# ----------------------------

AMBIGUOUS_GLYPHS = {
    "\ue260", "\ue261", "\ue262", "\ue870", "\ue873"
}

GLYPH_HINTS = {
    "\ue260": ["flat", "diminished", "other_accidental"],
    "\ue261": ["sharp", "other_accidental"],
    "\ue262": ["flat", "suffix_splitter", "other_accidental"],
    "\ue870": ["sharp", "other_accidental"],
    "\ue873": ["sharp", "extended_accidental", "other_accidental"],
}

TEXT_REPLACEMENTS = {
    "maj7 maj7": "maj7",
    "m7 m7": "m7",
    "Dm Dm": "Dm",
    "Am7 Am7": "Am7",
    "Gm7 Gm7": "Gm7",
    "E7 E7": "E7",
    "A7 A7": "A7",
    "Dm9 Dm9": "Dm9",
    "Em7 Em7": "Em7",
    "Bm7 Bm7": "Bm7",
    "B7 B7": "B7",
}


def normalize_raw_text(text: str) -> str:
    out = text
    for old, new in TEXT_REPLACEMENTS.items():
        out = out.replace(old, new)

    # compress whitespace
    out = re.sub(r"[ \t]+", " ", out)
    return out


def find_ambiguous_glyphs(token: str) -> List[str]:
    found = []
    for ch in token:
        if ch in AMBIGUOUS_GLYPHS:
            found.append(ch)
    return found


def classify_ambiguity(token: str) -> List[str]:
    labels = []
    for ch in token:
        if ch in GLYPH_HINTS:
            labels.extend(GLYPH_HINTS[ch])
    return sorted(set(labels))


# ----------------------------
# TOKEN HARVEST
# ----------------------------

def candidate_tokens_from_text(text: str) -> List[str]:
    """
    Harvest likely chord-symbol-like tokens from messy page text.
    We intentionally keep this permissive for later repair.
    """
    cleaned = normalize_raw_text(text)

    # split on whitespace but preserve messy symbol content
    rough_tokens = re.split(r"\s+", cleaned)

    candidates = []
    for tok in rough_tokens:
        tok = tok.strip().strip(",.;:()[]{}\"'")
        if not tok:
            continue

        # likely root-led chord token
        # examples:
        # Dm, E7, B6/9, F/G, C/B, DMaj9, G713, etc
        if re.match(r"^[A-G](?:[#b]|[\ue260\ue261\ue262\ue870\ue873])?.*", tok):
            candidates.append(tok)
            continue

        # common broken split suffix fragments we still want nearby
        if tok in {"maj7", "maj9", "m7", "m9", "m11", "dim7", "sus2", "sus4", "11", "13", "6/9", "7", "9"}:
            candidates.append(tok)

    return candidates


def merge_broken_tokens(tokens: List[str]) -> List[str]:
    """
    Merge things like:
    Cm7  m7   -> Cm7
    F F 6/9    -> F6/9
    G713 13   -> G713
    """
    merged = []
    i = 0

    while i < len(tokens):
        tok = tokens[i]

        # duplicate exact token
        if i + 1 < len(tokens) and tokens[i + 1] == tok:
            merged.append(tok)
            i += 2
            continue

        # root token + repeated suffix token
        if i + 1 < len(tokens):
            nxt = tokens[i + 1]

            if tok.startswith(tuple("ABCDEFG")) and nxt in {"maj7", "maj9", "m7", "m9", "m11", "11", "13", "6/9", "7", "9", "sus2", "sus4"}:
                if nxt not in tok:
                    merged.append(f"{tok}{nxt}")
                    i += 2
                    continue

        # F F 6/9 style
        if i + 2 < len(tokens):
            tok2 = tokens[i + 1]
            tok3 = tokens[i + 2]

            if tok in {"A", "B", "C", "D", "E", "F", "G"} and tok2 == tok and tok3 in {"6/9", "7", "9", "11", "13"}:
                merged.append(f"{tok}{tok3}")
                i += 3
                continue

        merged.append(tok)
        i += 1

    return merged


def dedupe_nearby(tokens: List[str]) -> List[str]:
    deduped = []
    for tok in tokens:
        if not deduped or deduped[-1] != tok:
            deduped.append(tok)
    return deduped


def harvest_page_tokens(page_text: str) -> List[str]:
    raw = candidate_tokens_from_text(page_text)
    merged = merge_broken_tokens(raw)
    deduped = dedupe_nearby(merged)
    return deduped


# ----------------------------
# CHORD RECORDS
# ----------------------------

def build_chord_records(tokens: List[str], page_index: int) -> List[Dict[str, Any]]:
    records = []
    for idx, token in enumerate(tokens):
        ambiguous_glyphs = find_ambiguous_glyphs(token)
        ambiguity_classes = classify_ambiguity(token)

        record = {
            "page_index": page_index,
            "sequence_index": idx,
            "raw_token": token,
            "normalized_token": token,   # placeholder for repair layer
            "ambiguous": len(ambiguous_glyphs) > 0,
            "ambiguous_glyphs": ambiguous_glyphs,
            "ambiguity_classes": ambiguity_classes,
            "repair_status": "unrepaired" if ambiguous_glyphs else "clean",
            "notes": ""
        }
        records.append(record)
    return records


# ----------------------------
# MAIN HARVEST
# ----------------------------

def harvest_pdf(pdf_path: str) -> Dict[str, Any]:
    title = os.path.splitext(os.path.basename(pdf_path))[0]
    doc = fitz.open(pdf_path)

    page_results = []
    all_records = []

    for page_index, page in enumerate(doc):
        text = page.get_text()
        harvested_tokens = harvest_page_tokens(text)
        records = build_chord_records(harvested_tokens, page_index)

        page_results.append({
            "page_index": page_index,
            "harvested_tokens": harvested_tokens,
            "records": records
        })

        all_records.extend(records)

    doc.close()

    result = {
        "title": title,
        "page_count": len(page_results),
        "page_results": page_results,
        "all_records": all_records
    }

    return result


def main() -> None:
    combined = []

    for filename in sorted(os.listdir(INPUT_DIR)):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(INPUT_DIR, filename)
        print(f"Harvesting chord symbols: {filename}")

        result = harvest_pdf(pdf_path)
        combined.append(result)

        out_path = os.path.join(OUTPUT_DIR, f"{result['title']}_chords.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4)

    combined_path = os.path.join(OUTPUT_DIR, "all_chord_symbol_harvest.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=4)

    print("\nSaved chord harvest results to:")
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()