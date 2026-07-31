from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from generate_bh5432_atlas_support import read_tg, musicxml_from_atlas, midi_from_atlas

ROOT = Path(__file__).resolve().parents[1]
TABS = Path(r"C:\Users\highl\OneDrive\Desktop\Tabs")
OUT = ROOT / "reviews" / "setlist"
ANALYSIS = ROOT / "analysis"

TUNES = [
    ("walls_of_time", "Walls of Time", "G | G | G | G | G | G | C | F | G | G | G | G | C | D | G | G", "G", "B", 4, 140),
    ("i_feel_the_blues_movin_in", "I Feel the Blues Movin' In", "G | G | G | D/G | G | G | G | D/G | G | G | G | G | C | C | G | G | C | C | G", "G", "B", 4, 120),
    ("farewell_blues", "Farewell Blues", "C/G | C | C/G | C | A7 | D/D# | C/G | C | C/G | C | C/G | C | C | A7 | D/D# | C/G | C | C", "C", "C", 0, 100),
    ("dig_a_hole_in_the_meadow", "Dig a Hole in the Meadow", "C | C | C | C | C | C | C/G | C | C", "C", "C", 0, 100),
    ("sarafina", "Sarafina", "G | D | A | Bm | Em | Bm | A | A | G | D | A | Bm | Em | A | D | D | G/A | Bm | G | A | G | Bm | A | A | G/A | Bm | G/A | Bm | Em | A | D | D", "D", "D", 0, 100),
    ("trail_of_tears", "Trail of Tears", "Em | D | Em | Em | Em | Em | Em | Em | A | A | B7 | B7 | B7 | B7 | Em | Em", "Em", "Em", 0, 120),
    ("perfume_powder_and_lead", "Perfume, Powder and Lead", "G | G | G | D/G | C | C | G | G | G | D/G", "G", "G", 0, 100),
    ("rank_strangers", "Rank Strangers", "C | C | C | G | C | C | C | C | C | C | C | D | G | G7 | C | C | C | G | C | C | C | C | C | C | C | G | C | F | C | C | C | C | C | C | C | C | C | C | C | D | G | G7 | C | C | C | F | C | C | C | C | C | C | Am | G | C | F | C", "C", "C", 0, 100),
    ("dear_old_dixie", "Dear Old Dixie", "G | G | G | G | C | C | G | G | G | G | G | G | A | A | D | D | G | G | G | G7 | C | C | B7 | B7 | C | C | G | Em | A | D | G | G", "G", "G", 0, 100),
    ("bright_sunny_south", "Bright Sunny South", "G | G/F | Dsus2 | Dsus2 | Dsus2 | Dsus2 | Dsus2 | G", "G", "A", 2, 120),
    ("somehow_tonight", "Somehow Tonight", "G | G | G | G | G | G | D | D | G | G | G | G | G | G | D | G", "G", "G", 0, 100),
    ("cant_you_hear_me_calling", "Can't You Hear Me Calling", "G | G | G | G | C | C | G | G | C | C | G | G | C | D | G", "G", "G", 0, 100),
    ("sitting_on_top_of_the_world", "Sitting on Top of the World", "G | G/G7 | C | G | G | Em | G/D | G", "G", "G", 0, 100),
    ("southern_flavor", "Southern Flavor", "Em | Em | Em | Em | Em | Em | B7 | B7 | Em | Em | Em | Em | G | B7 | Em | Em | D | D | E | E | D | D | B7 | B7 | Em | Em | Em | Em | G | B7 | Em | Em", "Em", "Em", 0, 100),
]

EXACT = {
    "walls_of_time": ["walls-of-time.tg", "walls-of-time.musicxml"],
    "i_feel_the_blues_movin_in": ["i-feel-the-blues-movin-in.tg"],
    "trail_of_tears": ["trail-of-tears.tg"],
    "bright_sunny_south": ["bright-sunny-south.tg"],
}
UNCERTAIN = {"dear_old_dixie": ["dixie-hoedown.tg"]}

TIER1 = {
    "walls_of_time": "tune m3: from 5 over repeated played-G/sounding-B tonic",
    "i_feel_the_blues_movin_in": "tune m10: from 5 over long played-G/sounding-B tonic",
    "dig_a_hole_in_the_meadow": "tune m3: from 5 over static C",
    "sarafina": "tune m15: from 5 over first of two D tonic measures",
    "perfume_powder_and_lead": "tune m2: from 5 over opening G plateau",
    "rank_strangers": "tune m41-43: from 3 over G/G7, continuation space, then C",
    "dear_old_dixie": "tune m15-17: from 3 over first D, continuation on second D, then G",
    "somehow_tonight": "tune m7-9: from 3 over first D, continuation on second D, then G",
    "cant_you_hear_me_calling": "tune m2: from 5 over opening G; short final D excluded",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tg_audit(path: Path) -> dict:
    root = read_tg(path)
    song = root.find("./TGSong")
    tracks = song.findall("TGTrack")
    headers = song.findall("TGMeasureHeader")
    track_rows = []
    for track in tracks:
        notes = track.findall(".//note")
        frets = [int(note.get("value")) for note in notes]
        track_rows.append({
            "name": track.findtext("name", ""), "measures": len(track.findall("TGMeasure")),
            "notes": len(notes), "max_displayed_fret": max(frets, default=None),
            "capo": int(track.findtext("offset", "0") or 0),
            "tuning": [int(node.text) for node in track.findall("TGString")],
        })
    return {"headers": len(headers), "tempo": headers[0].findtext("tempo", "unknown") if headers else "unknown", "tracks": track_rows}


def source_inventory():
    rows = []
    tune_by_slug = {slug: title for slug, title, *_ in TUNES}
    for slug, names in EXACT.items():
        for name in names:
            path = TABS / name
            audit = tg_audit(path) if path.suffix.lower() == ".tg" else {}
            rows.append({
                "original_absolute_path": str(path), "source_filename": name,
                "file_type": path.suffix.lower(), "source_sha256": sha256(path),
                "modified_date": path.stat().st_mtime, "matched_canonical_tune": tune_by_slug[slug],
                "match_confidence": "1.00", "import_status": "working_copy_retained",
                "repair_status": "not_overwritten; canonical scaffold built separately",
                "measure_count": audit.get("headers", "not audited"), "track_count": len(audit.get("tracks", [])),
                "source_notes": sum(t["notes"] for t in audit.get("tracks", [])),
            })
    for slug, names in UNCERTAIN.items():
        for name in names:
            path = TABS / name
            audit = tg_audit(path)
            rows.append({
                "original_absolute_path": str(path), "source_filename": name,
                "file_type": path.suffix.lower(), "source_sha256": sha256(path),
                "modified_date": path.stat().st_mtime, "matched_canonical_tune": tune_by_slug[slug],
                "match_confidence": "0.35", "import_status": "uncertain_supporting_candidate_only",
                "repair_status": "not merged; user review required",
                "measure_count": audit["headers"], "track_count": len(audit["tracks"]),
                "source_notes": sum(t["notes"] for t in audit["tracks"]),
            })
    path = ANALYSIS / "setlist_source_inventory.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return rows


def export_support():
    for tg in sorted(OUT.rglob("*.tg")):
        if "source_working_copy" in tg.parts or "supporting_candidates" in tg.parts:
            continue
        root = read_tg(tg)
        title = root.findtext("./TGSong/name", tg.stem)
        musicxml_from_atlas(root, tg.with_suffix(".musicxml"), title)
        midi_from_atlas(root, tg.with_suffix(".mid"))


def generated_validation():
    rows = []
    for tg in sorted(OUT.rglob("*.tg")):
        audit = tg_audit(tg)
        for track in audit["tracks"]:
            displayed = track["max_displayed_fret"]
            physical = None if displayed is None else displayed + track["capo"]
            rows.append({
                "file": str(tg.relative_to(ROOT)), "track": track["name"], "capo": track["capo"],
                "max_displayed_fret": displayed if displayed is not None else "no notes",
                "max_physical_fret": physical if physical is not None else "no notes",
                "limit": 16, "status": "pass" if physical is None or physical <= 16 else "FAIL",
                "measures": track["measures"], "notes": track["notes"],
            })
    with (ANALYSIS / "setlist_physical_fret_validation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    assert all(row["status"] == "pass" for row in rows)
    return rows


def reports(inventory, validation):
    found = {slug for slug in EXACT}
    lines = ["# Set-list source-match report", "", "Original files were read-only. Exact sources are retained byte-for-byte; conflicting form lengths were not silently merged with the user-supplied progression.", "", "| Tune | Match | Strongest source | Audit result |", "|---|---|---|---|"]
    for slug, title, progression, played, sounding, capo, tempo in TUNES:
        if slug in EXACT:
            names = ", ".join(EXACT[slug]); status = "exact title; retained as source working copy"
        elif slug in UNCERTAIN:
            names = ", ".join(UNCERTAIN[slug]); status = "uncertain title only; not merged"
        else:
            names = "none"; status = "no usable source found"
        lines.append(f"| {title} | {status} | {names} | canonical scaffold uses supplied {len([x for x in progression.split('|')])}-measure progression + count-in |")
    (ANALYSIS / "setlist_source_match_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    missing = [title for slug, title, *_ in TUNES if slug not in found]
    (ANALYSIS / "setlist_missing_tunes.md").write_text("# Missing set-list tune sources\n\nNo exact usable title source was found for:\n\n" + "\n".join(f"- {title}" for title in missing) + "\n\n`dixie-hoedown.tg` is retained only as an uncertain candidate for Dear Old Dixie.\n", encoding="utf-8")

    repair = ["# Set-list tune-by-tune repair/build report", "", "| Tune | Existing-source treatment | Canonical build | Review build |", "|---|---|---|---|"]
    for slug, title, progression, *_ in TUNES:
        source = "byte-preserved working copy; arrangement conflict documented" if slug in EXACT else ("uncertain candidate isolated" if slug in UNCERTAIN else "no source")
        review = TIER1.get(slug, "none; no high-confidence insertion")
        repair.append(f"| {title} | {source} | lead placeholders + exact chords + bass + click/count-in; {len(progression.split('|'))} tune measures | {review} |")
    (ANALYSIS / "setlist_tune_repair_report.md").write_text("\n".join(repair) + "\n", encoding="utf-8")

    capo_lines = ["# Set-list capo and transposition report", "", "| Tune | Capo | Played-shape key | Sounding key | Tempo authority |", "|---|---:|---|---|---|"]
    for slug, title, progression, played, sounding, capo, tempo in TUNES:
        authority = "exact TG source" if slug in EXACT else "practice default; needs user confirmation"
        capo_lines.append(f"| {title} | {capo} | {played} | {sounding} | {tempo} BPM ({authority}) |")
    capo_lines += ["", "Walls of Time and I Feel the Blues Movin' In satisfy the capo-4 doctrine: played G shapes, sounding B. Bright Sunny South preserves source capo 2 and is documented as played G / sounding A."]
    (ANALYSIS / "setlist_capo_transposition_report.md").write_text("\n".join(capo_lines) + "\n", encoding="utf-8")

    prog = ["# Set-list canonical progression normalization", "", "Canonical TG measure 1 is count-in. User tune measure 1 begins at TG measure 2. `/` means two successive chords, provisionally two beats each; all such labels say `SPLIT TIMING NEEDS REVIEW`.", "", "| Tune | Exact supplied progression |", "|---|---|"]
    prog.extend(f"| {title} | `{progression}` |" for _, title, progression, *_ in TUNES)
    (ANALYSIS / "setlist_progression_normalization.md").write_text("\n".join(prog) + "\n", encoding="utf-8")

    fret_lines = ["# Set-list physical-fret validation", "", f"Validated {len(validation)} tracks. Physical fret equals displayed fret plus capo; every sounding note is at or below physical fret 16.", "", "Detailed evidence: `analysis/setlist_physical_fret_validation.csv`."]
    (ANALYSIS / "setlist_physical_fret_validation.md").write_text("\n".join(fret_lines) + "\n", encoding="utf-8")

    manifest = {
        "library": "Highlander set-list practice scaffolds",
        "status": "needs_human_tuxguitar_review",
        "canonical_count": 14, "tier_1_review_count": len(TIER1),
        "progression_authority": "user-supplied progressions",
        "source_files_are_read_only": True,
        "tier_1": TIER1,
        "decisions_required": [
            "Confirm all split changes occur on beat 3.", "Confirm default tempos for tunes without exact TG sources.",
            "Confirm Bright Sunny South sounding key A with capo 2.", "Confirm whether dixie-hoedown.tg is related to Dear Old Dixie.",
            "Align retained source lead arrangements to canonical forms before importing melody.", "Approve Tier 1 review files in TuxGuitar before database approval.",
        ],
    }
    (OUT / "setlist_review_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    ANALYSIS.mkdir(exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    inventory = source_inventory()
    export_support()
    validation = generated_validation()
    reports(inventory, validation)
    print(json.dumps({"exact_tunes_found": len(EXACT), "missing_or_uncertain": 10, "canonical_tg": 14, "tier1_review_tg": len(TIER1), "validated_tracks": len(validation)}, indent=2))


if __name__ == "__main__": main()
