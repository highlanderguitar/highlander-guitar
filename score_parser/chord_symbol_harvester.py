import os
import re
import json

BASE_DIR = os.path.dirname(__file__)
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis", "chord_symbols")

os.makedirs(OUTPUT_DIR, exist_ok=True)

VALID_ROOTS = {"A","B","C","D","E","F","G"}
VALID_ACCIDENTALS = {"#", "b"}

VALID_QUALIFIERS = {
    "", "m", "7", "m7", "maj7", "dim", "dim7",
    "aug", "9", "11", "13", "6", "6/9",
    "m9", "m11", "m13",
    "sus", "sus2", "sus4"
}

BANNED_WORDS = {
    "as", "by", "capo", "dew", "mountain",
    "performed", "standard", "tuning",
    "fret", "sl", "p", "h"
}

def is_valid_chord(token: str) -> bool:
    if not token:
        return False

    low = token.lower()
    if low in BANNED_WORDS:
        return False

    if token.isdigit():
        return False

    root = token[0]
    if root not in VALID_ROOTS:
        return False

    rest = token[1:]

    # accidental
    if rest.startswith("#") or rest.startswith("b"):
        rest = rest[1:]

    # slash chords
    if "/" in rest:
        parts = rest.split("/")
        if len(parts) != 2:
            return False
        rest = parts[0]  # ignore bass note for now

    return rest in VALID_QUALIFIERS

def load_text_from_pdf(pdf_path):
    import fitz
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return pages

def normalize_text(text):
    text = text.replace("\u2019", "'")
    text = text.replace("\u2018", "'")
    text = text.replace("\u201c", '"')
    text = text.replace("\u201d", '"')
    text = re.sub(r"\s+", " ", text)
    return text

def tokenize(text):
    return re.findall(r"[A-Za-z0-9#/]+", text)

def harvest_pdf(pdf_path):
    pages = load_text_from_pdf(pdf_path)

    page_results = []
    all_records = []

    for page_index, raw_text in enumerate(pages):
        text = normalize_text(raw_text)
        tokens = tokenize(text)

        harvested = []
        records = []

        seq = 0
        for token in tokens:
            if not is_valid_chord(token):
                continue

            harvested.append(token)

            record = {
                "page_index": page_index,
                "sequence_index": seq,
                "raw_token": token,
                "normalized_token": token,
                "repair_status": "clean"
            }

            records.append(record)
            all_records.append(record)
            seq += 1

        page_results.append({
            "page_index": page_index,
            "harvested_tokens": harvested,
            "records": records
        })

    return {
        "title": os.path.splitext(os.path.basename(pdf_path))[0],
        "page_count": len(pages),
        "page_results": page_results,
        "all_records": all_records
    }

def main():
    for filename in os.listdir(INPUT_DIR):
        if not filename.endswith(".pdf"):
            continue

        path = os.path.join(INPUT_DIR, filename)
        print(f"Harvesting: {filename}")

        result = harvest_pdf(path)

        out_path = os.path.join(
            OUTPUT_DIR,
            f"{result['title']}_chords.json"
        )

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4)

    print("\nDone.")

if __name__ == "__main__":
    main()