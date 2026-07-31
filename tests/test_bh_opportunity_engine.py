from __future__ import annotations

import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
OUT = ROOT / "reviews" / "bh_5432" / "setlist_opportunities"


def _root():
    with zipfile.ZipFile(OUT / "BH-5432-Setlist-Application-Review.tg") as archive:
        assert archive.read("version.txt").decode() == "TuxGuitar_file_format 2.0"
        return ET.fromstring(archive.read("content.xml"))


def test_1625_correction_and_exact_progression_notation():
    correction = (ANALYSIS / "bh_5432_1625_correction.md").read_text(encoding="utf-8")
    assert "I-vi-ii-V" in correction
    assert "C-Am-Dm-G/G7" in correction
    assert "no tracked BH-5432 report or database application encoded `C-Fm-Dm-G`" in correction
    normalization = (ANALYSIS / "bh_5432_progression_normalization.md").read_text(encoding="utf-8")
    assert "D/G" in normalization
    assert "C/G" in normalization
    assert "G/F" in normalization
    assert "D/D#" in normalization
    assert "G/G7" in normalization
    assert "G/D" in normalization


def test_opportunity_csv_covers_every_tune_and_required_timing_fields():
    with (ANALYSIS / "bh_5432_setlist_opportunities.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 35
    assert len({row["tune"] for row in rows}) == 14
    assert sum(row["review_example"] == "yes" for row in rows) == 14
    required = {
        "opportunity_window", "musical_preconditions", "entry_beat", "target_note",
        "resolution", "continuation_required", "minimum_harmonic_duration",
        "preferred_harmonic_duration", "maximum_useful_duration", "tier", "confidence",
    }
    assert required <= rows[0].keys()
    assert all(row["strategy"] in {"PRIMARY", "SPECIALIZED ii OPTION"} for row in rows)
    assert all(row["tier"] in {"1", "2", "3", "4"} for row in rows)


def test_setlist_review_has_14_synchronized_slow_and_source_tempo_examples():
    root = _root()
    tracks = {track.findtext("name"): track for track in root.findall("./TGSong/TGTrack")}
    assert set(tracks) == {
        "Tier 1 Licks / Resolutions",
        "Preceding / Active / Following Harmony",
        "Bass Root Guide",
        "Count-In",
        "WHY This Opportunity",
    }
    assert all(len(track.findall("TGMeasure")) == 168 for track in tracks.values())
    for example in range(14):
        for version in (0, 6):
            base = example * 12 + version
            assert tracks["Count-In"].findall("TGMeasure")[base].findall(".//note")
            assert tracks["Preceding / Active / Following Harmony"].findall("TGMeasure")[base + 1].findall(".//note")
            assert tracks["Tier 1 Licks / Resolutions"].findall("TGMeasure")[base + 2].findall(".//note")
            assert tracks["Preceding / Active / Following Harmony"].findall("TGMeasure")[base + 2].findall(".//note")
            assert tracks["Tier 1 Licks / Resolutions"].findall("TGMeasure")[base + 3].findall(".//note")
            assert tracks["Preceding / Active / Following Harmony"].findall("TGMeasure")[base + 3].findall(".//note")
            assert not tracks["Tier 1 Licks / Resolutions"].findall("TGMeasure")[base + 5].findall(".//note")


def test_review_fingerings_obey_acoustic_limits_and_manifest_requires_human_review():
    root = _root()
    lick_track = root.findall("./TGSong/TGTrack")[0]
    for note in lick_track.findall(".//note"):
        string = int(note.get("string"))
        fret = int(note.get("value"))
        assert fret <= (16 if string == 1 else 15)
    manifest = json.loads((OUT / "BH-5432-Setlist-Application-Review.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "needs_human_tuxguitar_review"
    assert manifest["tier_1_count"] == 14
    assert all(example["decision"] == "pending" for example in manifest["tier_1_examples"])


def test_support_exports_exist_and_match_five_tracks():
    assert (OUT / "BH-5432-Setlist-Application-Review.mid").stat().st_size > 5000
    xml_root = ET.parse(OUT / "BH-5432-Setlist-Application-Review.musicxml").getroot()
    assert len(xml_root.findall("part")) == 5
