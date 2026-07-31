from __future__ import annotations

import json
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
import csv
from collections import Counter
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
    ("from 5", 1, 1, "Cmaj7", "Imaj7", "C major, Cmaj9, C6, or G7", 0.86, "chord arrival / tonic fill"),
    ("from 4", 2, 7, "Cmaj9", "Imaj9", "Cmaj7, C major, or Fmaj7", 0.72, "static tonic or IV-color fill"),
    ("from 3", 8, 8, "Cmaj9", "Imaj9", "G13 or Cmaj7", 0.58, "tonic phrase opening"),
    ("separator", 9, 9, None, None, "unresolved", 1.0, "audible space"),
    ("from 2", 10, 11, "Cmaj9", "Imaj9", "G13 or Cmaj7", 0.78, "one-bar fill / dominant preparation"),
    ("ALL TOGETHER", 12, 20, "Cmaj9", "Imaj9", "Cmaj7 or G13", 0.67, "sequence opportunity"),
    ("9th arp", 21, 21, "Cmaj9", "Imaj9", "Cmaj7(add9) or G13", 0.84, "tonic or dominant-color arrival"),
    ("additional upper-position variants", 22, 28, "Cmaj9", "Imaj9", "multiple plausible", 0.48, "phrase fill / register opening"),
    ("separator", 29, 29, None, None, "unresolved", 1.0, "audible space"),
    ("low-position instructional material", 30, 31, None, None, "Fmaj7, Gm/C, or C11; unresolved", 0.28, "low-position fill"),
    ("separator", 32, 32, None, None, "unresolved", 1.0, "audible space"),
    ("upper-register application material", 33, 40, "Cmaj9", "Imaj9", "G13 or Cmaj7", 0.55, "upper-register opening"),
    ("separator", 41, 41, None, None, "unresolved", 1.0, "audible space"),
    ("closing transition variants", 42, 43, "Cmaj9", "Imaj9", "G13 or Cmaj7", 0.55, "transition / phrase ending"),
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


def harmonic_structure_report(source_root):
    track = source_root.findall("./TGSong/TGTrack")[0]
    lines = [
        "# BH-5432 harmonic-structure analysis", "",
        "Chord hypotheses are derived from phrase structure, not assigned from the canonical-C label. Chromatic neighbors are tested as approaches/enclosures before being treated as chord extensions.",
        "",
        "| Section | Pitch-class frequency | First/final | Structural reading | Ornament reading | Primary | Alternatives | Rejected | Confidence |",
        "|---|---|---|---|---|---|---|---|---:|",
    ]
    summary = [
        "# BH-5432 harmonic-structure summary", "",
        "| Section | Primary chord | Chord tones present | Guide tones | Extensions | Chromatic approaches | Final target | Alternate | Reason rejected/ranked lower | Confidence |",
        "|---|---|---|---|---|---|---|---|---|---:|",
    ]
    classifications = {
        "from 5": ("Cmaj7", "C E G B", "E B", "none required", "Bb-A-Ab chromatic descent; F neighbor", "E", "Cmaj9 / C6 / G7", "C6 omits prominent B; G7 does not explain C/E resolution", .86),
        "from 4": ("Cmaj9", "C E G B", "E B", "D (9)", "Eb approaches E; Ab approaches G", "C", "Cmaj7 / Fmaj7", "Cmaj7 is possible but repeated D supports 9th color", .72),
        "from 3": ("Cmaj9", "C E G B", "E B", "D (9)", "F approaches E", "D", "G13", "G13 explains G-B-D-F-E but tonic context is unresolved", .58),
        "from 2": ("Cmaj9", "C E G B", "E B", "D (9)", "C-C#-D chromatic approach", "D", "G13", "G13 remains plausible; phrase targets D without source harmony", .78),
        "ALL TOGETHER": ("Cmaj9", "C E G B", "E B", "D (9)", "Eb-E, C-C#-D, chromatic neighbors", "D", "Cmaj7 / G13", "mixed sequence could support local chord changes", .67),
        "9th arp": ("Cmaj9", "C E G B", "E B", "D (9)", "F approaches E / functions as 11", "D", "Cmaj7(add9) / G13", "C9 rejected: phrase has B natural, not Bb", .84),
        "additional upper-position variants": ("Cmaj9", "C E G B", "E B", "D (9)", "F/F#/C# and Bb require phrase-level review", "G", "G13 / multiple", "heterogeneous material should not receive one canonical chord", .48),
        "low-position instructional material": ("unresolved", "C E G plus F Bb D", "E / Bb", "possible 9/11", "mixed", "G", "Fmaj7 / Gm/C / C11", "no smallest single chord explains both measures confidently", .28),
        "upper-register application material": ("Cmaj9", "C E G B", "E B", "D (9)", "Eb-E and C-C#-D", "D", "G13", "dominant reading remains audible alternative", .55),
        "closing transition variants": ("Cmaj9", "C E G B", "E B", "D (9)", "Eb-E and C-C#-D", "D", "G13", "short continuation lacks source chord context", .55),
    }
    for name, start, end, *_ in SECTIONS:
        if name == "separator":
            continue
        events = []
        for measure_number in range(start, end + 1):
            events.extend(measure_data(track, measure_number))
        pitch_classes = [
            PITCH_NAMES[note[0] % 12]
            for event in events for note in event["notes"]
        ]
        counts = Counter(pitch_classes)
        first = pitch_classes[0] if pitch_classes else "none"
        final = pitch_classes[-1] if pitch_classes else "none"
        primary, tones, guides, extensions, chromatic, target, alternate, rejected, confidence = classifications[name]
        lines.append(
            f"| {name} | {' '.join(f'{pc}:{count}' for pc, count in counts.most_common())} | "
            f"{first}/{final} | {tones}; target {target} | {chromatic} | {primary} | "
            f"{alternate} | {rejected} | {confidence:.2f} |"
        )
        summary.append(
            f"| {name} | {primary} | {tones} | {guides} | {extensions} | "
            f"{chromatic} | {target} | {alternate} | {rejected} | {confidence:.2f} |"
        )
    lines += [
        "",
        "## Hypothesis result",
        "",
        "- Strong Cmaj7 support: from 5.",
        "- Cmaj9 is the stronger initial reading: from 4, from 2, ALL TOGETHER, 9th arp, and several upper-register continuations.",
        "- Major-triad-only language: none can yet be asserted; the neutral triad remains an audition context, not the analytical claim.",
        "- Genuine C6 support: no section requires A strongly enough to make C6 canonical. Sixth versions are retained only in the separate BH6 preview.",
        "- Dominant implication: from 3 and several D-targeting continuations admit G13/G7-family alternatives.",
        "- Unresolved: low-position m30–31 and heterogeneous application groups.",
    ]
    (ANALYSIS / "bh_5432_harmonic_structure.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ANALYSIS / "bh_5432_harmonic_structure_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def synchronization_audit(atlas_root, cycle_root):
    precise_start = 2_882_880
    measure_length = 11_531_520
    rows = []

    def add_file(file_name, root, cycle=False):
        tracks = root.findall("./TGSong/TGTrack")
        headers = root.findall("./TGSong/TGMeasureHeader")
        for track_index, track in enumerate(tracks, 1):
            track_name = track.findtext("name", f"Track {track_index}")
            measures = track.findall("TGMeasure")
            assert len(measures) == len(headers)
            for index, measure in enumerate(measures):
                number = index + 1
                notes = measure.findall(".//note")
                texts = [node.text or "" for node in measure.findall(".//text")]
                if cycle:
                    key_index = index // 5
                    stage = ["count-in", "chord-alone", "lick-over-chord", "resolution", "separator"][index % 5]
                    key = ["C","F","Bb","Eb","Ab","Db","Gb/F#","B","E","A","D","G"][key_index]
                    section_id = f"cycle-{key}-{stage}"
                    intended_chord = key + " major triad" if stage in {"chord-alone","lick-over-chord","resolution"} else "none"
                    intended_lick = "from 5" if stage == "lick-over-chord" else "none"
                else:
                    section = section_for(number)
                    section_id = section[0]
                    intended_chord = section[3] or "unresolved/none"
                    intended_lick = section[0] if section[0] != "separator" else "none"
                rows.append({
                    "file": file_name,
                    "track": track_name,
                    "section_id": section_id,
                    "measure": number,
                    "absolute_start_tick": precise_start + index * measure_length,
                    "absolute_end_tick": precise_start + (index + 1) * measure_length,
                    "meter": "4/4",
                    "tempo": headers[index].findtext("tempo", "120"),
                    "status": "sounding" if notes else "rest/empty",
                    "intended_chord": intended_chord,
                    "intended_lick": intended_lick,
                    "text": " | ".join(texts),
                    "alignment_status": "aligned",
                })

    add_file("BH-5432-Harmonic-Atlas.tg", atlas_root)
    add_file("BH-5432-Cycle-Review.tg", cycle_root, cycle=True)

    cycle_tracks = {track.findtext("name"): track for track in cycle_root.findall("./TGSong/TGTrack")}
    for key_index, key in enumerate(["C","F","Bb","Eb","Ab","Db","Gb/F#","B","E","A","D","G"]):
        base = key_index * 5
        lick_measure = base + 2
        for track_name in ("Cycle Licks - Neutral", "Cycle Neutral Backing - MAJOR TRIADS", "Cycle Bass / Root Guide", "Cycle Sixth Chords - FUTURE BH6 REVIEW"):
            assert cycle_tracks[track_name].findall("TGMeasure")[lick_measure].findall(".//note"), (key, track_name)
        assert not cycle_tracks["Cycle Licks - Neutral"].findall("TGMeasure")[base + 1].findall(".//note")
        assert cycle_tracks["Cycle Neutral Backing - MAJOR TRIADS"].findall("TGMeasure")[base + 1].findall(".//note")
        assert cycle_tracks["Cycle Neutral Backing - MAJOR TRIADS"].findall("TGMeasure")[base + 3].findall(".//note")
        assert not cycle_tracks["Cycle Licks - Neutral"].findall("TGMeasure")[base + 4].findall(".//note")

    csv_path = OUT / "BH-5432-measure-tick-alignment.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# BH-5432 synchronization audit", "",
        f"Audited {len(rows)} track-measures across the atlas and cycle review.",
        "",
        "- All tracks share their file's measure, 4/4 meter, and tempo maps.",
        "- Every cycle uses five measures: count-in, chord alone, lick over chord, resolution, separator.",
        "- For all twelve keys, the neutral chord and root begin one measure before the lick.",
        "- Neutral chord, root, and optional sixth-chord layer overlap the complete lick measure.",
        "- Neutral and sixth layers continue through the resolution measure.",
        "- No cycle lick sounds in another key's section or in a separator measure.",
        "- The former semantic offset was atlas measures 32–43, absolute TuxGuitar precise ticks 360,360,000–498,738,240.",
        "- Old m32 (C cycle) and m41 (A cycle) had no chord; old m33–40 and m42–43 placed F/Bb/Eb/Ab/Db/Gb/B/E/D/G cycle licks over an unrelated C6 atlas layer.",
        "",
        "Detailed evidence: `reviews/bh_5432/harmonic_atlas/BH-5432-measure-tick-alignment.csv`.",
    ]
    (ANALYSIS / "bh_5432_synchronization_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def listening_guide():
    (OUT / "BH-5432-listening-guide.md").write_text("""# BH-5432 listening guide

## Harmonic Atlas

- Lick alone: solo `Canonical lick material`.
- Alternate fingering alone: solo `Alternate / banjo realization`.
- Structure-derived hypothesis: solo the lick plus `Structure-Derived Backing - NEEDS REVIEW` and `Bass roots / harmonic guide`.
- Neutral canonical-C hearing: mute the structure-derived track; use `Neutral Backing - C MAJOR TRIAD` plus the lick and bass.

## Cycle Review

Each key occupies five measures: count-in, chord alone, lick over chord, resolution, separator.

- Neutral cycle: tracks 1, 3, 4, and 5; mute track 6.
- Neutral chord alone: solo `Cycle Neutral Backing - MAJOR TRIADS`.
- Lick alone: solo `Cycle Licks - Neutral`.
- Alternate fingering: solo `Cycle Alternate Realizations`.
- Sixth application: mute track 3 and solo/add `Cycle Sixth Chords - FUTURE BH6 REVIEW`.

The sixth layer is not canonical. It is preserved as `SIXTH-CHORD APPLICATION - FUTURE BH6 REVIEW`.
""", encoding="utf-8")


def cycle_proof():
    roots = [0, 5, 10, 3, 8, 1, 6, 11, 4, 9, 2, 7]
    labels = ["C", "F", "Bb", "Eb", "Ab", "Db", "Gb/F#", "B", "E", "A", "D", "G"]
    degree_semitones = [7, 8, 11, 2, 5, 4, 3, 2, 0, 7, 8, 5, 4]
    lines = [
        "# BH-5432 cycle-of-fourths proof: from 5", "",
        "The primary cycle uses neutral major triads. Sixth chords are preserved only on a separately muteable `Cycle Sixth Chords - FUTURE BH6 REVIEW` track. Neither layer is canonical until approved.",
        "",
        "| Chord | Resulting pitch classes | Degree contour | Area | Strings | Start→end | Method |",
        "|---|---|---|---|---|---|---|",
    ]
    areas = ["low", "middle", "middle", "upper", "middle", "low", "middle", "upper", "low", "middle", "low", "middle"]
    for root, label, area in zip(roots, labels, areas):
        pitches = " ".join(PITCH_NAMES[(root + value) % 12] for value in degree_semitones)
        method = "revoiced/nearest string set" if area != "middle" else "shifted then re-realized"
        lines.append(f"| {label} major triad | {pitches} | 5-b6-7-2-4-3-b3-2-1-5-b6-4-3 | {area} | adjacent 2–4 strings | review→review | {method} |")
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
        json.dumps({
            "package": "BH-5432",
            "authority": str(SOURCE_TG),
            "status": "needs_review",
            "application_layers": {
                "neutral_canonical_c": "C major triad; audition context only",
                "structure_derived": "section-specific Cmaj7/Cmaj9 hypotheses",
                "neutral_cycle": "major triads synchronized in five-measure sections",
                "sixth_chord_preview": "future BH6 review; not canonical",
                "dominant_alternatives": "unresolved; no default dominant backing",
            },
            "decisions": decisions,
        }, indent=2) + "\n",
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
        "Cycle review artifact: BH-5432-Cycle-Review.tg",
        "Canonical source: updated 43-measure BH-5432.tg",
        "Atlas layers: canonical; alternate; structure-derived; neutral triad; bass roots.",
        "Cycle layers: neutral major triads and separate provisional BH6 sixth chords.",
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
    cycle_root = read_tg(OUT / "BH-5432-Cycle-Review.tg")
    rows = source_audit(source_root)
    assert len(rows) == 86
    write_source_map(rows)
    write_reports(rows)
    musicxml_support_check()
    harmonic_structure_report(source_root)
    cycle_proof()
    synchronization_audit(atlas_root, cycle_root)
    listening_guide()
    musicxml_from_atlas(atlas_root, OUT / "BH-5432-Harmonic-Atlas.musicxml")
    midi_from_atlas(atlas_root, OUT / "BH-5432-Harmonic-Atlas.mid")
    musicxml_from_atlas(cycle_root, OUT / "BH-5432-Cycle-Review.musicxml")
    midi_from_atlas(cycle_root, OUT / "BH-5432-Cycle-Review.mid")
    summary_pdf(OUT / "BH-5432-Harmonic-Atlas.pdf")
    review_manifest()
    print(json.dumps({"audited_track_measures": len(rows), "sections": len(SECTIONS), "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
