from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from highlander_render.db.core import connect, import_repository, migrate, seed, validation_errors


def built_db(tmp_path: Path) -> Path:
    path = tmp_path / "content.sqlite3"
    migrate(path)
    seed(path)
    return path


def test_clean_migration_and_ordering(tmp_path: Path) -> None:
    path = tmp_path / "clean.sqlite3"
    assert migrate(path) == 1
    assert migrate(path) == 0
    with connect(path) as db:
        versions = [r[0] for r in db.execute("SELECT version FROM schema_migrations ORDER BY version")]
    assert versions == sorted(versions) == ["001_content_database.sql"]


def test_clean_build_has_all_tables_and_views(tmp_path: Path) -> None:
    path = built_db(tmp_path)
    with connect(path) as db:
        objects = {r[0] for r in db.execute("SELECT name FROM sqlite_schema")}
    assert {
        "tunes", "structural_units", "systems", "system_occurrences", "teachable_moments",
        "lenses", "teachable_moment_lenses", "learner_needs", "content_items",
        "content_teachable_moments", "play_this_scripts", "play_this_layers",
        "content_relationships", "visual_assets", "exercises", "sources", "source_claims",
        "v_play_this_readiness", "v_source_provenance",
    } <= objects


def test_seed_and_import_are_idempotent(tmp_path: Path) -> None:
    path = built_db(tmp_path)
    before = import_repository(path)
    after = import_repository(path)
    assert before["conflicted"] == 0
    assert after["inserted"] == 0
    with connect(path) as db:
        slugs = [r[0] for r in db.execute("SELECT slug FROM sources")]
    assert len(slugs) == len(set(slugs))


def test_foreign_keys_are_enforced(tmp_path: Path) -> None:
    with connect(built_db(tmp_path)) as db:
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO structural_units(tune_id,slug,title,sequence) VALUES (999,'x','x',1)")


def test_play_this_opening_and_learner_need_are_enforced(tmp_path: Path) -> None:
    with connect(built_db(tmp_path)) as db:
        item = db.execute("SELECT id FROM content_items LIMIT 1").fetchone()[0]
        db.execute("DELETE FROM play_this_scripts WHERE content_item_id=?", (item,))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO play_this_scripts(content_item_id,opening_text,body_text,closing_hook,learner_need_id) VALUES (?,?,?,?,NULL)",
                (item, "Try this", "body", "hook"),
            )


def test_primary_lens_relationship_is_prohibited(tmp_path: Path) -> None:
    with connect(built_db(tmp_path)) as db:
        tm = db.execute("SELECT id FROM teachable_moments LIMIT 1").fetchone()[0]
        lens = db.execute("SELECT id FROM lenses LIMIT 1").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO teachable_moment_lenses(teachable_moment_id,lens_id,relationship_type) VALUES (?,?,'primary')",
                (tm, lens),
            )


def test_part_two_must_be_independent(tmp_path: Path) -> None:
    with connect(built_db(tmp_path)) as db:
        item = db.execute("SELECT id FROM content_items LIMIT 1").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO play_this_layers(content_item_id,part_number,title,is_independently_playable,is_independently_loopable) VALUES (?,2,'Part 2',0,0)",
                (item,),
            )


def test_provenance_relationship_integrity_and_validation(tmp_path: Path) -> None:
    path = built_db(tmp_path)
    with connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM source_claims sc JOIN sources s ON s.id=sc.source_id").fetchone()[0] > 0
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert list(db.execute("PRAGMA foreign_key_check")) == []
    assert validation_errors(path) == []


def test_rebuild_semantics_are_reproducible(tmp_path: Path) -> None:
    first = built_db(tmp_path / "a")
    second = built_db(tmp_path / "b")
    with connect(first) as left, connect(second) as right:
        for table in ("lenses", "learner_needs", "content_items", "play_this_scripts", "source_claims"):
            columns = [
                r[1] for r in left.execute(f"PRAGMA table_info({table})")
                if r[1] not in {"created_at", "updated_at"}
            ]
            selection = ",".join(f'"{column}"' for column in columns)
            left_rows = [tuple(r) for r in left.execute(f"SELECT {selection} FROM {table}")]
            right_rows = [tuple(r) for r in right.execute(f"SELECT {selection} FROM {table}")]
            assert left_rows == right_rows
