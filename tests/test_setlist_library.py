from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reviews" / "setlist"
ANALYSIS = ROOT / "analysis"

PROGRESSION_LENGTHS = {
    "walls_of_time": 16, "i_feel_the_blues_movin_in": 19, "farewell_blues": 18,
    "dig_a_hole_in_the_meadow": 9, "sarafina": 32, "trail_of_tears": 16,
    "perfume_powder_and_lead": 10, "rank_strangers": 57, "dear_old_dixie": 32,
    "bright_sunny_south": 8, "somehow_tonight": 16, "cant_you_hear_me_calling": 15,
    "sitting_on_top_of_the_world": 8, "southern_flavor": 32,
}


def tg_root(path: Path):
    with zipfile.ZipFile(path) as archive:
        assert archive.read("version.txt").decode() == "TuxGuitar_file_format 2.0"
        return ET.fromstring(archive.read("content.xml"))


def canonical_files():
    return sorted(OUT.glob("*/canonical/*.tg"))


def review_files():
    return sorted(OUT.glob("*/bh_5432_review/*.tg"))


def test_every_tune_has_a_clean_four_track_canonical_scaffold():
    files = canonical_files()
    assert len(files) == 14
    for path in files:
        slug = path.parents[1].name
        root = tg_root(path)
        tracks = root.findall("./TGSong/TGTrack")
        assert [track.findtext("name") for track in tracks] == [
            "Lead Guide", "Rhythm / Backing Chords", "Bass Guide", "Click / Count-In"
        ]
        measure_counts = [len(track.findall("TGMeasure")) for track in tracks]
        assert len(set(measure_counts)) == 1
        assert measure_counts[0] > 1
        assert not tracks[0].findall(".//note")  # no invented melody
        assert not [node for node in tracks[0].findall(".//text") if (node.text or "").strip()]
        assert tracks[3].findall("TGMeasure")[0].findall(".//note")
        assert tracks[1].findall(".//note")
        assert tracks[2].findall(".//note")
        assert tracks[3].findall(".//note")


def test_capo_sounding_labels_and_bright_sunny_south_tuning():
    for slug in ("walls_of_time", "i_feel_the_blues_movin_in"):
        root = tg_root(next((OUT / slug / "canonical").glob("*.tg")))
        tracks = root.findall("./TGSong/TGTrack")
        assert all(int(track.findtext("offset")) == 4 for track in tracks)
        texts = [node.text or "" for node in tracks[1].findall(".//text")]
        assert "B" in texts
        assert all("Sounding:" not in text and "Played shape:" not in text for text in texts)
        assert max(int(note.get("value")) for note in root.findall(".//note")) <= 12
    bright = tg_root(next((OUT / "bright_sunny_south" / "canonical").glob("*.tg")))
    tracks = bright.findall("./TGSong/TGTrack")
    assert all(int(track.findtext("offset")) == 2 for track in tracks)
    assert [int(node.text) for node in tracks[0].findall("TGString")] == [64, 59, 55, 50, 45, 38]
    texts = [node.text or "" for node in tracks[1].findall(".//text")]
    assert "A" in texts
    assert all("Sounding:" not in text and "Played shape:" not in text for text in texts)


def test_split_measure_labels_stay_on_their_native_beat_without_verbose_prose():
    split_count = 0
    for path in canonical_files():
        root = tg_root(path)
        backing = root.findall("./TGSong/TGTrack")[1]
        for measure in backing.findall("TGMeasure"):
            texts = [node.text or "" for node in measure.findall(".//text")]
            assert all("SPLIT TIMING NEEDS REVIEW" not in text for text in texts)
            visible = [text for text in texts if text.strip()]
            if len(visible) > 1:
                split_count += 1
                starts = [int(beat.findtext("preciseStart")) for beat in measure.findall("TGBeat") if (beat.findtext("text") or "").strip()]
                assert starts == sorted(starts)
                assert len(set(starts)) == len(starts)
    assert split_count > 0


def test_physical_fret_limit_including_capo():
    with (ANALYSIS / "setlist_physical_fret_validation.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 107
    assert all(row["status"] == "pass" for row in rows)
    for path in list(canonical_files()) + list(review_files()):
        root = tg_root(path)
        for track in root.findall("./TGSong/TGTrack"):
            capo = int(track.findtext("offset", "0") or 0)
            assert all(int(note.get("value")) + capo <= 16 for note in track.findall(".//note"))


def test_tier1_reviews_are_separate_and_from3_has_delayed_resolution_space():
    files = review_files()
    assert len(files) == 9
    for path in files:
        root = tg_root(path)
        tracks = root.findall("./TGSong/TGTrack")
        assert len(tracks) == 5
        assert tracks[4].findtext("name") == "BH-5432 Application Review"
        assert tracks[4].findall(".//note")
        assert path.with_suffix(".mid").stat().st_size > 1000
        assert len(ET.parse(path.with_suffix(".musicxml")).getroot().findall("part")) == 5
    for slug in ("rank_strangers", "dear_old_dixie", "somehow_tonight"):
        root = tg_root(next((OUT / slug / "bh_5432_review").glob("*.tg")))
        texts = [node.text or "" for node in root.findall("./TGSong/TGTrack")[4].findall(".//text")]
        assert any(text in {"CONTINUE", "TARGET"} for text in texts)
        assert "TARGET" in texts


def test_review_playback_pitches_respect_capo_and_dominant_root():
    walls = tg_root(next((OUT / "walls_of_time" / "bh_5432_review").glob("*.tg")))
    walls_app = walls.findall("./TGSong/TGTrack")[4]
    walls_tuning = [int(node.text) for node in walls_app.findall("TGString")]
    walls_pcs = {
        (walls_tuning[int(note.get("string")) - 1] + int(note.get("value")) + 4) % 12
        for note in walls_app.findall(".//note")
    }
    assert {10, 11, 3, 6} <= walls_pcs  # Bb-B-Eb-F#: B-major from-5 structure/color

    rank = tg_root(next((OUT / "rank_strangers" / "bh_5432_review").glob("*.tg")))
    rank_app = rank.findall("./TGSong/TGTrack")[4]
    rank_tuning = [int(node.text) for node in rank_app.findall("TGString")]
    rank_pcs = {
        (rank_tuning[int(note.get("string")) - 1] + int(note.get("value"))) % 12
        for note in rank_app.findall(".//note")
    }
    assert {7, 11, 2, 5, 4} <= rank_pcs  # G-B-D-F-E: G13 reading, not D13


def test_source_provenance_and_review_manifest():
    with (ANALYSIS / "setlist_source_inventory.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 6
    assert sum(row["match_confidence"] == "1.00" for row in rows) == 5
    assert any(row["source_filename"] == "dixie-hoedown.tg" and row["match_confidence"] == "0.35" for row in rows)
    known_hash = hashlib.sha256((OUT / "walls_of_time" / "source_working_copy" / "walls-of-time-source.tg").read_bytes()).hexdigest()
    assert known_hash == "49309abaf32b5dc91ed9ce243cb0dd9136da53168b507146382957a43ea00a52"
    manifest = json.loads((OUT / "setlist_review_manifest.json").read_text(encoding="utf-8"))
    assert manifest["canonical_count"] == 14
    assert manifest["tier_1_review_count"] == 9
    assert manifest["status"] == "needs_human_tuxguitar_review"
