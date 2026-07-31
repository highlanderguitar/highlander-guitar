from __future__ import annotations

import json
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TG = Path(r"C:\Users\highl\OneDrive\Desktop\Tabs\BH-5432.tg")
SOURCE_MUSICXML = Path(r"C:\Users\highl\OneDrive\Desktop\Tabs\BH-5432.musicxml")
OUT = ROOT / "reviews" / "bh_5432" / "harmonic_atlas"
ANALYSIS = ROOT / "analysis"

SECTIONS = [
    ("from 5", 1, 1, "C6", "I6", "C6 or G7", 0.68, "chord arrival / tonic fill"),
    ("from 4", 2, 7, "C6", "I6", "C6 or F7", 0.56, "static tonic or IV-color fill"),
    ("from 3", 8, 8, "C6", "I6", "C6", 0.68, "tonic phrase opening"),
    ("separator", 9, 9, None, None, "unresolved", 1.0, "audible space"),
    ("from 2", 10, 11, "C6", "I6", "C6 or G7", 0.52, "one-bar fill / dominant preparation"),
    ("ALL TOGETHER", 12, 20, "C6", "I6", "C6; continuation harmony unresolved", 0.55, "sequence opportunity"),
    ("9th arp", 21, 21, "C9", "I9", "C9, F9, or G9", 0.45, "tonic or dominant-color arrival"),
    ("additional upper-position variants", 22, 28, "C6", "I6", "multiple plausible", 0.35, "phrase fill / register opening"),
    ("separator", 29, 29, None, None, "unresolved", 1.0, "audible space"),
    ("low-position instructional material", 30, 31, "C6", "I6", "multiple plausible", 0.35, "low-position fill"),
    ("separator", 32, 32, None, None, "unresolved", 1.0, "audible space"),
    ("upper-register application material", 33, 40, "C6", "I6", "multiple plausible", 0.32, "upper-register opening"),
    ("separator", 41, 41, None, None, "unresolved", 1.0, "audible space"),
    ("closing transition variants", 42, 43, "C6", "I6", "multiple plausible", 0.30, "transition / phrase ending"),
]

TUNING = [64, 59, 55, 50, 45, 40]
PITCH_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def section_for(measure: int):
    return next(section for section in SECTIONS if section[1] <= measure <= section[2])


def read_tg(path: Path):
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("content.xml"))


def pitch_name(midi: int) -> str:
    return f"{PITCH_NAMES[midi % 12]}{midi // 12 - 1}"


def measure_data(track, measure_number: int):
    measure = track.findall("TGMeasure")[measure_number - 1]
    events = []
    for beat in measure.findall("TGBeat"):
        text = beat.findtext("text", "")
        voice = beat.find("voice")
        duration = int(voice.find("duration").get("value")) if voice is not None else 4
        notes = []
        if voice is not None:
            for note in voice.findall("note"):
                string = int(note.get("string"))
                fret = int(note.get("value"))
                midi = TUNING[string - 1] + fret
                notes.append((midi, string, fret))
        events.append({"text": text, "duration": duration, "notes": notes})
    return events


def source_audit(source_root):
    rows = []
    for track_index, track in enumerate(source_root.findall("./TGSong/TGTrack"), 1):
        name = track.findtext("name", f"Track {track_index}")
        for measure in range(1, 44):
            events = measure_data(track, measure)
            annotation = " | ".join(e["text"] for e in events if e["text"])
            notes = [pitch_name(n[0]) for e in events for n in e["notes"]]
            fingering = [f"{n[1]}/{n[2]}" for e in events for n in e["notes"]]
            rhythm = [str(e["duration"]) for e in events if e["notes"]]
            section = section_for(measure)
            rows.append({
                "track": name,
                "track_index": track_index,
                "measure": measure,
                "section": section[0],
                "annotation": annotation,
                "notes": " ".join(notes) or "rest/empty",
                "rhythm": " ".join(rhythm) or "rest/empty",
                "fingering": " ".join(fingering) or "none",
                "pattern_family": section[0],
                "likely_active_chord": section[3] or "unresolved",
                "confidence": section[6],
                "question": section[5],
            })
    return rows


def write_source_map(rows):
    lines = [
        "# BH-5432 updated harmonic-atlas map", "",
        "The updated TG is authoritative. All 43 measures on both tracks are accounted for (86 track-measures).",
        "",
        "| Track | M | Section | Source annotation | Exact notes | Rhythm values | Fingering | Chord | Confidence | Question |",
        "|---|---:|---|---|---|---|---|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['track']} | {row['measure']} | {row['section']} | "
            f"{row['annotation']} | {row['notes']} | {row['rhythm']} | "
            f"{row['fingering']} | {row['likely_active_chord']} | "
            f"{row['confidence']:.2f} | {row['question']} |"
        )
    (ANALYSIS / "bh_5432_updated_atlas_map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(rows):
    boundary = [
        "# BH-5432 section boundaries", "",
        "| Section | Measures | Source annotation/evidence | Classification |",
        "|---|---|---|---|",
    ]
    chord = [
        "# BH-5432 chord-assignment review", "",
        "All assignments are provisional and require listening review. Canonical C describes the instructional reference, not a permanent accompaniment chord.",
        "",
        "| Section | Primary audible chord | Function | Alternatives | Confidence | Evidence/status |",
        "|---|---|---|---|---:|---|",
    ]
    entry = ["# BH-5432 entry opportunities", "", "| Section | Entry opportunity | Signal |", "|---|---|---|"]
    exit_lines = [
        "# BH-5432 exits and resolutions", "",
        "| Section | Final note | State | Safe exit | Strong exit | Expected next harmony |",
        "|---|---|---|---|---|---|",
    ]
    for name, start, end, symbol, function, alternatives, confidence, opportunity in SECTIONS:
        evidence = "source annotation" if any(
            row["annotation"] for row in rows if row["track_index"] == 1 and start <= row["measure"] <= end
        ) else "boundary inferred from source spacing/register; needs review"
        boundary.append(f"| {name} | {start}–{end} | {evidence} | {'separator' if name == 'separator' else 'provisional family/application'} |")
        chord.append(f"| {name} | {symbol or 'none'} | {function or 'none'} | {alternatives} | {confidence:.2f} | {evidence}; needs_review |")
        entry.append(f"| {name} | {opportunity} | hear the active chord before entering; use a melody rest or sustained note |")
        section_rows = [r for r in rows if r["track_index"] == 1 and start <= r["measure"] <= end and r["notes"] != "rest/empty"]
        final_note = section_rows[-1]["notes"].split()[-1] if section_rows else "none"
        state = "open pending harmonic confirmation" if symbol else "separator"
        exit_lines.append(f"| {name} | {final_note} | {state} | hold or resolve to chord root | target chord third/root | user must approve next chord |")
    (ANALYSIS / "bh_5432_section_boundaries.md").write_text("\n".join(boundary) + "\n", encoding="utf-8")
    (ANALYSIS / "bh_5432_chord_assignment_review.md").write_text("\n".join(chord) + "\n", encoding="utf-8")
    (ANALYSIS / "bh_5432_entry_opportunities.md").write_text("\n".join(entry) + "\n", encoding="utf-8")
    (ANALYSIS / "bh_5432_exit_and_resolution.md").write_text("\n".join(exit_lines) + "\n", encoding="utf-8")

    (ANALYSIS / "bh_5432_fingering_area_comparison.md").write_text("""# BH-5432 fingering-area comparison

The source Track 1 fingering is authoritative. The source Banjo track is preserved as an alternate/native realization where populated.

| Area | Status | Preservation rule |
|---|---|---|
| Source upper/middle position | source-supported | exact pitch, rhythm, string, and fret retained |
| Source low position (m30–31) | source-supported | retained as instructional material |
| Adjacent string set | needs_review | preserve degree contour and rhythm; octave changes must be labeled |
| Octave displacement | needs_review | entry/exit pitches and register change must be explicit |
| Cycle proof realizations | needs_review | choose continuity, not automatic fixed fret offsets |
""", encoding="utf-8")


def musicxml_support_check():
    root = ET.parse(SOURCE_MUSICXML).getroot()
    lines = [
        "# BH-5432 updated MusicXML support check", "",
        "The updated TG remains authoritative for annotations, track organization, tuning, and fingering. MusicXML is supporting evidence for notation order, pitch, rhythm, rests, and ties.",
        "",
        "| Part | Measures | Sounding notes | Rests | Ties | Technical string/fret events |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    names = {
        node.get("id"): node.findtext("part-name", node.get("id"))
        for node in root.findall("./part-list/score-part")
    }
    for part in root.findall("part"):
        measures = part.findall("measure")
        notes = part.findall(".//note")
        sounding = sum(note.find("rest") is None for note in notes)
        rests = sum(note.find("rest") is not None for note in notes)
        ties = len(part.findall(".//tie"))
        technical = len(part.findall(".//notations/technical"))
        lines.append(
            f"| {names.get(part.get('id'), part.get('id'))} | {len(measures)} | "
            f"{sounding} | {rests} | {ties} | {technical} |"
        )
    lines += [
        "",
        "The MusicXML contains no `<harmony>` elements and did not preserve the TG beat text. It is therefore not used to infer chord canon or replace TG annotations.",
    ]
    (ANALYSIS / "bh_5432_musicxml_support_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def cycle_proof():
    roots = [0, 5, 10, 3, 8, 1, 6, 11, 4, 9, 2, 7]
    labels = ["C", "F", "Bb", "Eb", "Ab", "Db", "Gb/F#", "B", "E", "A", "D", "G"]
    degree_semitones = [7, 8, 11, 2, 5, 4, 3, 2, 0, 7, 8, 5, 4]
    lines = [
        "# BH-5432 cycle-of-fourths proof: from 5", "",
        "This is a review preview, not an approved twelve-key library. The abstract contour is harmonically transposed; each fingering is then physically re-realized near a playable neck area.",
        "",
        "| Chord | Resulting pitch classes | Degree contour | Area | Strings | Start→end | Method |",
        "|---|---|---|---|---|---|---|",
    ]
    areas = ["low", "middle", "middle", "upper", "middle", "low", "middle", "upper", "low", "middle", "low", "middle"]
    for root, label, area in zip(roots, labels, areas):
        pitches = " ".join(PITCH_NAMES[(root + value) % 12] for value in degree_semitones)
        method = "revoiced/nearest string set" if area != "middle" else "shifted then re-realized"
        lines.append(f"| {label}6 | {pitches} | 5-b6-7-2-4-3-b3-2-1-5-b6-4-3 | {area} | adjacent 2–4 strings | review→review | {method} |")
    (ANALYSIS / "bh_5432_cycle_of_fourths_proof.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def musicxml_from_atlas(atlas_root, path: Path):
    tracks = atlas_root.findall("./TGSong/TGTrack")
    part_list = "".join(
        f'<score-part id="P{i}"><part-name>{escape(track.findtext("name", f"Track {i}"))}</part-name></score-part>'
        for i, track in enumerate(tracks, 1)
    )
    parts = []
    for part_index, track in enumerate(tracks, 1):
        measures = []
        strings = [int(node.text) for node in track.findall("TGString")]
        for number, measure in enumerate(track.findall("TGMeasure"), 1):
            content = []
            if number == 1:
                content.append(
                    '<attributes><divisions>480</divisions><key><fifths>0</fifths></key>'
                    '<time><beats>4</beats><beat-type>4</beat-type></time>'
                    '<clef><sign>G</sign><line>2</line></clef></attributes>'
                )
                content.append('<direction><sound tempo="120"/></direction>')
            beats = measure.findall("TGBeat")
            if not beats:
                content.append('<note><rest/><duration>1920</duration><voice>1</voice><type>whole</type></note>')
            for beat in beats:
                text = beat.findtext("text", "")
                if text:
                    content.append(f'<direction placement="above"><direction-type><words>{escape(text)}</words></direction-type></direction>')
                voice = beat.find("voice")
                if voice is None:
                    continue
                value = int(voice.find("duration").get("value"))
                duration = int(1920 / value)
                notes = voice.findall("note")
                if not notes:
                    content.append(f'<note><rest/><duration>{duration}</duration><voice>1</voice></note>')
                for note_index, note in enumerate(notes):
                    string = int(note.get("string"))
                    fret = int(note.get("value"))
                    midi = strings[string - 1] + fret
                    pc, octave = midi % 12, midi // 12 - 1
                    names = [("C",0),("C",1),("D",0),("D",1),("E",0),("F",0),("F",1),("G",0),("G",1),("A",0),("A",1),("B",0)]
                    step, alter = names[pc]
                    content.append(
                        "<note>" + ("<chord/>" if note_index else "") +
                        f"<pitch><step>{step}</step>{f'<alter>{alter}</alter>' if alter else ''}<octave>{octave}</octave></pitch>"
                        f"<duration>{duration}</duration><voice>1</voice><notations><technical><string>{string}</string><fret>{fret}</fret></technical></notations></note>"
                    )
            measures.append(f'<measure number="{number}">{"".join(content)}</measure>')
        parts.append(f'<part id="P{part_index}">{"".join(measures)}</part>')
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<score-partwise version="4.0"><work><work-title>BH-5432 Harmonic Atlas</work-title></work>'
        f'<part-list>{part_list}</part-list>{"".join(parts)}</score-partwise>'
    )
    path.write_text(xml, encoding="utf-8")


def vlq(value: int) -> bytes:
    data = [value & 0x7F]
    value >>= 7
    while value:
        data.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(data))


def midi_from_atlas(atlas_root, path: Path):
    chunks = []
    for channel, track in enumerate(atlas_root.findall("./TGSong/TGTrack")):
        strings = [int(node.text) for node in track.findall("TGString")]
        data = bytearray(b"\x00\xff\x03" + bytes([len(track.findtext("name", "Track"))]) + track.findtext("name", "Track").encode())
        for measure in track.findall("TGMeasure"):
            beats = measure.findall("TGBeat")
            if not beats:
                data += vlq(1920)
                continue
            for beat in beats:
                voice = beat.find("voice")
                if voice is None:
                    continue
                duration = int(1920 / int(voice.find("duration").get("value")))
                notes = voice.findall("note")
                for index, note in enumerate(notes):
                    midi = strings[int(note.get("string")) - 1] + int(note.get("value"))
                    data += vlq(0) + bytes([0x90 | (channel % 16), midi, 75])
                first = True
                for note in notes:
                    midi = strings[int(note.get("string")) - 1] + int(note.get("value"))
                    data += vlq(duration if first else 0) + bytes([0x80 | (channel % 16), midi, 0])
                    first = False
                if not notes:
                    data += vlq(duration)
        data += b"\x00\xff\x2f\x00"
        chunks.append(b"MTrk" + struct.pack(">I", len(data)) + data)
    path.write_bytes(b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), 480) + b"".join(chunks))


def review_manifest():
    decisions = []
    fields = [
        "section_name", "section_boundary", "starting_degree", "active_chord",
        "harmonic_function", "entry_opportunity", "target_note", "resolution",
        "original_fingering", "alternate_fingering", "backing_chord_voicing",
        "cycle_of_fourths_realization",
    ]
    for section in SECTIONS:
        if section[0] == "separator":
            continue
        decisions.append({
            "section": section[0],
            "source_measures": [section[1], section[2]],
            "status": "needs_review",
            "choices": {field: {"decision": "pending", "revision": ""} for field in fields},
        })
    (OUT / "BH-5432-Harmonic-Atlas-review.json").write_text(
        json.dumps({"package": "BH-5432", "authority": str(SOURCE_TG), "decisions": decisions}, indent=2) + "\n",
        encoding="utf-8",
    )


def summary_pdf(path: Path):
    c = canvas.Canvas(str(path), pagesize=letter)
    y = 750
    c.setFont("Helvetica-Bold", 16)
    c.drawString(54, y, "BH-5432 Harmonic Atlas")
    y -= 28
    c.setFont("Helvetica", 10)
    for line in [
        "Primary review artifact: BH-5432-Harmonic-Atlas.tg",
        "Canonical source: updated 43-measure BH-5432.tg",
        "Tracks: canonical material; alternate/banjo realization; provisional backing chords; bass roots.",
        "Chord assignments are audible proposals, not canon.",
        "Review sections: from 5, from 4, from 3, from 2, ALL TOGETHER, 9th arp, variants.",
        "See the review manifest and Markdown reports for approval fields and unresolved alternatives.",
    ]:
        c.drawString(54, y, line)
        y -= 18
    c.save()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ANALYSIS.mkdir(exist_ok=True)
    source_root = read_tg(SOURCE_TG)
    atlas_root = read_tg(OUT / "BH-5432-Harmonic-Atlas.tg")
    rows = source_audit(source_root)
    assert len(rows) == 86
    write_source_map(rows)
    write_reports(rows)
    musicxml_support_check()
    cycle_proof()
    musicxml_from_atlas(atlas_root, OUT / "BH-5432-Harmonic-Atlas.musicxml")
    midi_from_atlas(atlas_root, OUT / "BH-5432-Harmonic-Atlas.mid")
    summary_pdf(OUT / "BH-5432-Harmonic-Atlas.pdf")
    review_manifest()
    print(json.dumps({"audited_track_measures": len(rows), "sections": len(SECTIONS), "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
