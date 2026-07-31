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
        "Backing chords - PROVISIONAL",
        "Bass roots / harmonic guide",
        "Cycle of fourths preview - NEEDS REVIEW",
    ]
    assert all(len(track.findall("TGMeasure")) == 43 for track in tracks)
    assert len(root.findall(".//note")) == 824


def test_atlas_preserves_source_annotations_and_adds_harmonic_labels():
    root = _tg_root()
    texts = [node.text or "" for node in root.findall(".//text")]
    assert '"5" arrives at the 5, then jumps down to 7 1 4 3' in texts
    assert '"2" walks to 2, jumps down to 5, then back up to the 2' in texts
    assert "ALL TOGETHER" in texts
    assert "9th arp" in texts
    assert any("Chord: C6" in text and "PROVISIONAL" in text for text in texts)
    assert sum("CYCLE PREVIEW" in text for text in texts) == 12


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
