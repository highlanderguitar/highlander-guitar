from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NATIVE_VERSION_TOKEN = "TuxGuitar_file_format 2.0"


def validate_tg_archive(path: Path) -> dict:
    result = {
        "archive_readable": False,
        "xml_well_formed": False,
        "schema_shape_recognized": False,
        "version_metadata_present": False,
        "native_parser_accepted": False,
        "application_opened": False,
        "playback_ready": False,
        "reopen_verified": False,
        "review_ready": False,
        "track_count": 0,
        "note_count": 0,
        "error": None,
    }
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            result["archive_readable"] = True
            if names != {"version.txt", "content.xml"}:
                raise ValueError(f"unexpected archive entries: {sorted(names)}")
            version_text = archive.read("version.txt").decode("utf-8")
            xml = archive.read("content.xml")
        root = ET.fromstring(xml)
        result["xml_well_formed"] = True
        version = root.find("TGVersion")
        song = root.find("TGSong")
        result["schema_shape_recognized"] = (
            root.tag == "TuxGuitarFile" and version is not None and song is not None
        )
        result["version_metadata_present"] = (
            version_text == NATIVE_VERSION_TOKEN
            and version is not None
            and (
                version.get("major"),
                version.get("minor"),
                version.get("revision"),
            )
            == ("2", "0", "1")
        )
        if not result["version_metadata_present"]:
            raise ValueError("missing or invalid native TG version metadata")
        result["track_count"] = len(root.findall("./TGSong/TGTrack"))
        result["note_count"] = len(root.findall(".//note"))
    except (OSError, UnicodeError, zipfile.BadZipFile, ET.ParseError, ValueError) as exc:
        result["error"] = str(exc)
    return result


def apply_native_results(
    result: dict,
    *,
    native_parser_accepted: bool,
    application_opened: bool,
    playback_ready: bool,
    reopen_verified: bool,
) -> dict:
    result.update(
        native_parser_accepted=native_parser_accepted,
        application_opened=application_opened,
        playback_ready=playback_ready,
        reopen_verified=reopen_verified,
    )
    result["review_ready"] = all(
        result[key]
        for key in (
            "archive_readable",
            "xml_well_formed",
            "schema_shape_recognized",
            "version_metadata_present",
            "native_parser_accepted",
            "application_opened",
            "playback_ready",
            "reopen_verified",
        )
    )
    return result
