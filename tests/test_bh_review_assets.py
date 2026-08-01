from pathlib import Path
import zipfile
from highlander_render.db.review_assets import _tg_xml
from highlander_render.db.tg_validation import NATIVE_VERSION_TOKEN, validate_tg_archive

def test_comparison_tg_has_five_named_tracks():
    event={"string_number":2,"fret":5,"duration":0.5}
    tracks=[(name,[event],"review") for name in ("Original source excerpt","Extracted lick","Generated alternate fingering","Approved application examples","Review notes")]
    xml=_tg_xml(tracks)
    assert xml.count("<TGTrack ") == 5
    for name,_,_ in tracks: assert name in xml

def test_tg_notes_are_playable_string_fret_pairs():
    event={"string_number":3,"fret":7,"duration":0.5}
    xml=_tg_xml([("Guitar",[event],"")])
    assert 'note string="3" value="7"' in xml

def test_missing_version_metadata_is_rejected(tmp_path):
    path = tmp_path / "missing-version.tg"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("version.txt", "TuxGuitar file format 2.0")
        archive.writestr(
            "content.xml",
            '<TuxGuitarFile><TGVersion major="2" minor="0" revision="1"/>'
            "<TGSong/></TuxGuitarFile>",
        )
    result = validate_tg_archive(path)
    assert result["archive_readable"]
    assert result["xml_well_formed"]
    assert not result["version_metadata_present"]
    assert not result["native_parser_accepted"]
    assert not result["review_ready"]

def test_invalid_archive_is_rejected(tmp_path):
    path = tmp_path / "invalid.tg"
    path.write_bytes(b"not a zip")
    result = validate_tg_archive(path)
    assert not result["archive_readable"]
    assert not result["review_ready"]

def test_native_version_token_matches_tuxguitar_201():
    assert NATIVE_VERSION_TOKEN == "TuxGuitar_file_format 2.0"
