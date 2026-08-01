from __future__ import annotations

import json
from pathlib import Path

from highlander_render.db.core import connect
from highlander_render.db.inventory import inventory_sources


def _config(path: Path, roots: dict) -> Path:
    config = path / "roots.json"
    config.write_text(json.dumps({"source_roots": roots}), encoding="utf-8")
    return config


def test_inventory_is_idempotent_and_root_relative(tmp_path: Path) -> None:
    external, intake = tmp_path / "Tabs", tmp_path / "input"
    external.mkdir(); intake.mkdir()
    (external / "My Lick.musicxml").write_text("<score/>", encoding="utf-8")
    (external / "My Lick.tg").write_bytes(b"tg")
    (intake / "scan.png").write_bytes(b"png")
    config = _config(tmp_path, {
        "tabs_library": {"path": str(external), "kind": "external_library", "tracked_in_git": False, "writable": False},
        "repository_input": {"path": str(intake), "kind": "repository_relative", "tracked_in_git": False, "writable": False},
    })
    database = tmp_path / "inventory.sqlite3"
    first = inventory_sources(database, full=True, config_path=config)
    second = inventory_sources(database, config_path=config)
    assert first["new"] == 3
    assert second["new"] == second["changed"] == second["missing"] == 0
    assert second["unchanged"] == 3 and second["hashes_computed"] == 0
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM source_packages").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM source_files WHERE relative_path LIKE '%:%'").fetchone()[0] == 0


def test_inventory_detects_changed_and_missing(tmp_path: Path) -> None:
    root = tmp_path / "root"; root.mkdir()
    file = root / "a.musicxml"; file.write_text("one", encoding="utf-8")
    config = _config(tmp_path, {"tabs_library": {
        "path": str(root), "kind": "external_library", "tracked_in_git": False, "writable": False
    }})
    database = tmp_path / "inventory.sqlite3"
    inventory_sources(database, full=True, config_path=config)
    file.write_text("two changed", encoding="utf-8")
    assert inventory_sources(database, full=True, config_path=config)["changed"] == 1
    file.unlink()
    assert inventory_sources(database, config_path=config)["missing"] == 1
