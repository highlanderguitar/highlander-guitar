from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "reviews" / "bh_5432" / "harmonic_atlas"


def _tg_root():
    with zipfile.ZipFile(ATLAS / "BH-5432-Harmonic-Atlas.tg") as archive:
        assert archive.read("version.txt").decode() == "TuxGuitar_file_format 2.0"
        return ET.fromstring(archive.read("content.xml"))


def test_atlas_has_five_meaningful_tracks_and_all_source_measures():
    root = _tg_root()
    tracks = root.findall("./TGSong/TGTrack")
    assert [track.findtext("name") for track in tracks] == [
        "Canonical lick material",
        "Alternate / banjo realization",
        "Structure-Derived Backing - NEEDS REVIEW",
        "Neutral Backing - MAJOR TRIADS",
        "Bass roots / harmonic guide",
    ]
    assert all(len(track.findall("TGMeasure")) == 43 for track in tracks)
    assert len(root.findall(".//note")) == 844


def test_atlas_preserves_source_annotations_and_adds_harmonic_labels():
    root = _tg_root()
    texts = [node.text or "" for node in root.findall(".//text")]
    assert '"5" arrives at the 5, then jumps down to 7 1 4 3' in texts
    assert '"2" walks to 2, jumps down to 5, then back up to the 2' in texts
    assert "ALL TOGETHER" in texts
    assert "9th arp" in texts
    assert any("Cmaj7 hypothesis" in text and "NEEDS REVIEW" in text for text in texts)
    assert any("Cmaj9 hypothesis (B natural, not C9)" in text for text in texts)
    assert not any("Chord: C6" in text for text in texts)
    measure_26_texts = [
        node.text or ""
        for track in root.findall("./TGSong/TGTrack")[2:]
        for node in track.findall("TGMeasure")[25].findall(".//text")
    ]
    assert any("Chord: G" in text for text in measure_26_texts)
    assert any("G major triad" in text for text in measure_26_texts)
    assert any("Root: G" in text for text in measure_26_texts)


def test_review_manifest_requires_user_decisions():
    manifest = json.loads((ATLAS / "BH-5432-Harmonic-Atlas-review.json").read_text())
    assert manifest["decisions"]
    for section in manifest["decisions"]:
        assert section["status"] == "needs_review"
        assert all(item["decision"] == "pending" for item in section["choices"].values())


def test_supporting_exports_are_nonempty_and_musicxml_has_four_parts():
    assert (ATLAS / "BH-5432-Harmonic-Atlas.mid").stat().st_size > 1000
    assert (ATLAS / "BH-5432-Harmonic-Atlas.pdf").stat().st_size > 10000
    root = ET.parse(ATLAS / "BH-5432-Harmonic-Atlas.musicxml").getroot()
    assert len(root.findall("part")) == 5


def test_cycle_review_is_five_measure_sections_with_separate_sixth_layer():
    with zipfile.ZipFile(ATLAS / "BH-5432-Cycle-Review.tg") as archive:
        root = ET.fromstring(archive.read("content.xml"))
    tracks = {track.findtext("name"): track for track in root.findall("./TGSong/TGTrack")}
    assert set(tracks) == {
        "Cycle Licks - Neutral",
        "Cycle Alternate Realizations",
        "Cycle Neutral Backing - MAJOR TRIADS",
        "Cycle Bass / Root Guide",
        "Cycle Count-In",
        "Cycle Sixth Chords - FUTURE BH6 REVIEW",
    }
    assert all(len(track.findall("TGMeasure")) == 60 for track in tracks.values())
    tuning = [64, 59, 55, 50, 45, 40]
    roots = [0, 5, 10, 3, 8, 1, 6, 11, 4, 9, 2, 7]
    for key_index in range(12):
        base = key_index * 5
        assert tracks["Cycle Count-In"].findall("TGMeasure")[base].findall(".//note")
        assert tracks["Cycle Neutral Backing - MAJOR TRIADS"].findall("TGMeasure")[base + 1].findall(".//note")
        assert tracks["Cycle Licks - Neutral"].findall("TGMeasure")[base + 2].findall(".//note")
        assert tracks["Cycle Neutral Backing - MAJOR TRIADS"].findall("TGMeasure")[base + 2].findall(".//note")
        assert tracks["Cycle Sixth Chords - FUTURE BH6 REVIEW"].findall("TGMeasure")[base + 2].findall(".//note")
        assert tracks["Cycle Neutral Backing - MAJOR TRIADS"].findall("TGMeasure")[base + 3].findall(".//note")
        assert not tracks["Cycle Licks - Neutral"].findall("TGMeasure")[base + 4].findall(".//note")
        lick_notes = tracks["Cycle Licks - Neutral"].findall("TGMeasure")[base + 2].findall(".//note")
        alternate_notes = tracks["Cycle Alternate Realizations"].findall("TGMeasure")[base + 2].findall(".//note")
        assert len(lick_notes) == len(alternate_notes)
        lick_midis = [tuning[int(note.get("string")) - 1] + int(note.get("value")) for note in lick_notes]
        alternate_midis = [tuning[int(note.get("string")) - 1] + int(note.get("value")) for note in alternate_notes]
        assert alternate_midis == [midi - 12 for midi in lick_midis]
        neutral_notes = tracks["Cycle Neutral Backing - MAJOR TRIADS"].findall("TGMeasure")[base + 2].findall(".//note")
        sixth_notes = tracks["Cycle Sixth Chords - FUTURE BH6 REVIEW"].findall("TGMeasure")[base + 2].findall(".//note")
        neutral_pcs = {
            (tuning[int(note.get("string")) - 1] + int(note.get("value"))) % 12
            for note in neutral_notes
        }
        sixth_pcs = {
            (tuning[int(note.get("string")) - 1] + int(note.get("value"))) % 12
            for note in sixth_notes
        }
        root_pc = roots[key_index]
        assert neutral_pcs == {root_pc, (root_pc + 4) % 12, (root_pc + 7) % 12}
        assert sixth_pcs == neutral_pcs | {(root_pc + 9) % 12}

    for track_name in ("Cycle Licks - Neutral", "Cycle Alternate Realizations"):
        for note in tracks[track_name].findall(".//note"):
            string = int(note.get("string"))
            fret = int(note.get("value"))
            assert fret <= (16 if string == 1 else 15)
