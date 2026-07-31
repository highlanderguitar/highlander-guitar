from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = REPO_ROOT / "var" / "highlander_content.sqlite3"
MIGRATIONS = REPO_ROOT / "sql" / "migrations"
EXPORT_DIR = REPO_ROOT / "exports" / "database"


def connect(path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 5000")
    return db


def migrate(path: Path = DEFAULT_DB_PATH) -> int:
    with connect(path) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        applied = {r["version"]: r["checksum"] for r in db.execute("SELECT version, checksum FROM schema_migrations")}
        count = 0
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            sql = migration.read_text(encoding="utf-8")
            digest = hashlib.sha256(sql.encode()).hexdigest()
            if migration.name in applied:
                if applied[migration.name] != digest:
                    raise RuntimeError(f"Applied migration changed: {migration.name}")
                continue
            db.executescript(sql)
            db.execute("INSERT INTO schema_migrations(version, checksum) VALUES (?, ?)", (migration.name, digest))
            count += 1
    return count


def seed(path: Path = DEFAULT_DB_PATH) -> dict[str, int]:
    migrate(path)
    counts = {"lenses": 0, "learner_needs": 0, "content_items": 0}
    with connect(path) as db:
        for slug, name, description in [
            ("recognition", "Recognition", "Hear and identify the teachable event."),
            ("unpack", "Unpack", "Expose the event's structure and mechanics."),
            ("expression", "Expression", "Shape the event musically."),
            ("return-to-seed", "Return to Seed", "Reconnect elaboration to its compact source."),
        ]:
            cur = db.execute(
                "INSERT OR IGNORE INTO lenses(slug,name,description,authority) VALUES (?,?,?,'highlander')",
                (slug, name, description),
            )
            counts["lenses"] += cur.rowcount
        for slug, name in [
            ("short-loopable-practice", "A short passage I can loop and play along with"),
            ("part-two-independent", "A Part 2 that works as its own practice loop"),
            ("named-closing-need", "A closing hook that names what I need next"),
        ]:
            cur = db.execute(
                "INSERT OR IGNORE INTO learner_needs(slug,name,description) VALUES (?,?,?)",
                (slug, name, name),
            )
            counts["learner_needs"] += cur.rowcount
        source = db.execute(
            "INSERT OR IGNORE INTO sources(slug,title,source_type,authority_level,citation) "
            "VALUES ('governing-bootstrap-prompt','Highlander database governing prompt','prompt','canonical','User-supplied implementation brief');"
        )
        source_id = db.execute("SELECT id FROM sources WHERE slug='governing-bootstrap-prompt'").fetchone()[0]
        db.execute(
            "INSERT OR IGNORE INTO tunes(slug,title,status,source_id) VALUES ('doctrine-example','Doctrine Example','draft',?)",
            (source_id,),
        )
        tune_id = db.execute("SELECT id FROM tunes WHERE slug='doctrine-example'").fetchone()[0]
        db.execute(
            "INSERT OR IGNORE INTO teachable_moments(slug,title,description,status,source_id) "
            "VALUES ('loop-one-dense-idea','Loop One Dense Idea','A minimal doctrine-only play-along moment.','draft',?)",
            (source_id,),
        )
        moment_id = db.execute("SELECT id FROM teachable_moments WHERE slug='loop-one-dense-idea'").fetchone()[0]
        need_id = db.execute("SELECT id FROM learner_needs WHERE slug='short-loopable-practice'").fetchone()[0]
        db.execute(
            "INSERT OR IGNORE INTO content_items(slug,title,content_type,status,tune_id,learner_need_id,source_id,renderer_path,visual_plan) "
            "VALUES ('play-this-loop-one-dense-idea','Play This: Loop One Dense Idea','play_this','draft',?,?,?,"
            "'src/highlander_render/db/renderer_stub.py','Single loop card with beat markers and learner-need closing card')",
            (tune_id, need_id, source_id),
        )
        item_id = db.execute("SELECT id FROM content_items WHERE slug='play-this-loop-one-dense-idea'").fetchone()[0]
        counts["content_items"] += 1
        db.execute(
            "INSERT OR IGNORE INTO content_teachable_moments(content_item_id,teachable_moment_id,sequence) VALUES (?,?,1)",
            (item_id, moment_id),
        )
        db.execute(
            "INSERT OR IGNORE INTO play_this_scripts(content_item_id,opening_text,body_text,closing_hook,learner_need_id,status) "
            "VALUES (?,?,?,?,?,'draft')",
            (item_id, "PLAY THIS", "Loop one short, dense idea and play along.", "Use this when you need a short passage you can loop.", need_id),
        )
        db.execute(
            "INSERT OR IGNORE INTO play_this_layers(content_item_id,part_number,title,is_independently_playable,is_independently_loopable) "
            "VALUES (?,1,'Core loop',1,1)",
            (item_id,),
        )
        lens_id = db.execute("SELECT id FROM lenses WHERE slug='recognition'").fetchone()[0]
        db.execute(
            "INSERT OR IGNORE INTO teachable_moment_lenses(teachable_moment_id,lens_id,relationship_type) VALUES (?,?,'active')",
            (moment_id, lens_id),
        )
        db.execute(
            "INSERT OR IGNORE INTO source_claims(source_id,claim_text,claim_type,status,is_canonical) "
            "VALUES (?,?, 'doctrine','accepted',1)",
            (source_id, "Play This scripts begin with PLAY THIS."),
        )
    return counts


def import_repository(path: Path = DEFAULT_DB_PATH) -> dict[str, int]:
    migrate(path)
    report = {"inserted": 0, "updated": 0, "skipped": 0, "conflicted": 0}
    candidates = [
        REPO_ROOT / "docs" / "highlander_constitution.md",
        REPO_ROOT / "docs" / "highlander_book_architecture.md",
        REPO_ROOT / "analysis" / "charlie_christian" / "air_mail_special" / "air_mail_special_external_transcript_contribution_audit.md",
    ]
    with connect(path) as db:
        for file in candidates:
            if not file.is_file():
                report["skipped"] += 1
                continue
            relative = file.relative_to(REPO_ROOT).as_posix()
            digest = hashlib.sha256(file.read_bytes()).hexdigest()
            slug = relative.lower().replace("/", "-").replace("_", "-").replace(".", "-")
            old = db.execute("SELECT id,content_hash FROM sources WHERE repository_path=?", (relative,)).fetchone()
            authority = "external" if "external" in relative else "highlander"
            if old and old["content_hash"] == digest:
                report["skipped"] += 1
            elif old:
                db.execute(
                    "UPDATE sources SET content_hash=?, title=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (digest, file.stem.replace("_", " "), old["id"]),
                )
                report["updated"] += 1
            else:
                db.execute(
                    "INSERT INTO sources(slug,title,source_type,authority_level,repository_path,content_hash,citation) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (slug, file.stem.replace("_", " "), "repository_document", authority, relative, digest, relative),
                )
                report["inserted"] += 1
    batch_report = import_manifest(path)
    report["entities"] = batch_report
    report["needs_review"] = sum(v.get("needs_review", 0) for v in batch_report.values())
    return report


def import_manifest(path: Path = DEFAULT_DB_PATH) -> dict[str, dict[str, int]]:
    manifest_path = REPO_ROOT / "data" / "database" / "ingestion_batch_001.json"
    if not manifest_path.is_file():
        return {}
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    entities = [
        "sources", "tunes", "systems", "lenses", "learner_needs", "teachable_moments",
        "content_items", "relationships", "source_claims", "skipped_files",
    ]
    report = {name: {"inserted": 0, "updated": 0, "skipped": 0, "conflicted": 0, "needs_review": 0} for name in entities}

    def inserted(cur: sqlite3.Cursor, entity: str, review: bool = False) -> None:
        report[entity]["inserted" if cur.rowcount else "skipped"] += 1
        if review:
            report[entity]["needs_review"] += 1

    with connect(path) as db:
        source_ids: dict[str, int] = {}
        for item in data["sources"]:
            cur = db.execute(
                "INSERT OR IGNORE INTO sources(slug,title,source_type,authority_level,citation,repository_path,content_hash) "
                "VALUES (?,?, 'curated_manifest',?,?,?,?)",
                (item["slug"], item["title"], item["authority"], item["path"], item["path"], item["hash"]),
            )
            inserted(cur, "sources", item["status"] == "needs_review")
            source_ids[item["slug"]] = db.execute("SELECT id FROM sources WHERE slug=?", (item["slug"],)).fetchone()[0]
            db.execute(
                "INSERT OR REPLACE INTO import_file_log(repository_path,content_hash,disposition,reason) VALUES (?,?,?,?)",
                (item["path"], item["hash"], "needs_review" if item["status"] == "needs_review" else "imported",
                 f"Curated batch {data['batch']}: {item['status']}"),
            )
        for item in data["tunes"]:
            cur = db.execute(
                "INSERT OR IGNORE INTO tunes(slug,title,status,source_id,import_status) VALUES (?,?,'draft',?,?)",
                (item["slug"], item["title"], source_ids[item["source"]], item["status"]),
            )
            inserted(cur, "tunes", item["status"] == "needs_review")
        for item in data["systems"]:
            cur = db.execute(
                "INSERT OR IGNORE INTO systems(slug,name,description,status,import_status) VALUES (?,?,?,'draft',?)",
                (item["slug"], item["name"], item["description"], item["status"]),
            )
            inserted(cur, "systems", item["status"] == "needs_review")
        for item in data["lenses"]:
            cur = db.execute(
                "INSERT OR IGNORE INTO lenses(slug,name,description,authority,import_status) VALUES (?,?,?,'highlander','proposed')",
                (item["slug"], item["name"], f"Imported from {data['batch']}"),
            )
            inserted(cur, "lenses")
        for item in data["learner_needs"]:
            cur = db.execute(
                "INSERT OR IGNORE INTO learner_needs(slug,name,description,import_status) VALUES (?,?,?,'accepted')",
                (item["slug"], item["name"], item["name"]),
            )
            inserted(cur, "learner_needs")
        for item in data["moments"]:
            system_id = None
            if item.get("system"):
                system_id = db.execute("SELECT id FROM systems WHERE slug=?", (item["system"],)).fetchone()[0]
            cur = db.execute(
                "INSERT OR IGNORE INTO teachable_moments(slug,title,description,system_id,source_id,status,import_status) "
                "VALUES (?,?,?,?,?,'draft',?)",
                (item["slug"], item["title"], item["description"], system_id, source_ids[item["source"]], item["status"]),
            )
            inserted(cur, "teachable_moments", item["status"] == "needs_review")
            moment_id = db.execute("SELECT id FROM teachable_moments WHERE slug=?", (item["slug"],)).fetchone()[0]
            for lens_slug in item["lenses"]:
                lens_id = db.execute("SELECT id FROM lenses WHERE slug=?", (lens_slug,)).fetchone()[0]
                db.execute(
                    "INSERT OR IGNORE INTO teachable_moment_lenses(teachable_moment_id,lens_id,relationship_type) VALUES (?,?,'active')",
                    (moment_id, lens_id),
                )
            if item["status"] == "needs_review":
                db.execute(
                    "INSERT OR IGNORE INTO review_candidates(entity_type,entity_slug,reason,source_id) VALUES ('teachable_moment',?,?,?)",
                    (item["slug"], "Harmonic inference remains explicitly source-dependent.", source_ids[item["source"]]),
                )
        tune_id = db.execute("SELECT id FROM tunes WHERE slug='take-five'").fetchone()[0]
        play_source = source_ids["take-five-play-this-inventory"]
        for item in data["play_this"]:
            need_id = db.execute("SELECT id FROM learner_needs WHERE slug=?", (item["need"],)).fetchone()[0]
            cur = db.execute(
                "INSERT OR IGNORE INTO content_items(slug,title,content_type,status,tune_id,learner_need_id,source_id,import_status) "
                "VALUES (?,?,'play_this','draft',?,?,?,'needs_review')",
                (item["slug"], item["title"], tune_id, need_id, play_source),
            )
            inserted(cur, "content_items", True)
            content_id = db.execute("SELECT id FROM content_items WHERE slug=?", (item["slug"],)).fetchone()[0]
            moment_id = db.execute("SELECT id FROM teachable_moments WHERE slug=?", (item["moment"],)).fetchone()[0]
            db.execute("INSERT OR IGNORE INTO content_teachable_moments VALUES (?,?,1)", (content_id, moment_id))
            db.execute(
                "INSERT OR IGNORE INTO play_this_candidate_details VALUES (?,?,?,?,?,?,?)",
                (content_id, item["seed"], item["opening"], item["ending"], 0, item["part2"], item["evidence"]),
            )
            db.execute(
                "INSERT OR IGNORE INTO review_candidates(entity_type,entity_slug,reason,source_id) "
                "VALUES ('content_item',?,'Opening, seed and ending exist; complete script and independent Part 2 do not.',?)",
                (item["slug"], play_source),
            )
        for item in data["relationships"]:
            from_id = db.execute("SELECT id FROM content_items WHERE slug=?", (item["from"],)).fetchone()[0]
            to_id = db.execute("SELECT id FROM content_items WHERE slug=?", (item["to"],)).fetchone()[0]
            cur = db.execute(
                "INSERT OR IGNORE INTO content_relationships(from_content_item_id,to_content_item_id,relationship_type,notes) VALUES (?,?,?,?)",
                (from_id, to_id, item["type"], item["notes"]),
            )
            inserted(cur, "relationships")
        for item in data["claims"]:
            cur = db.execute(
                "INSERT OR IGNORE INTO source_claims(source_id,claim_text,claim_type,status,is_canonical) VALUES (?,?,?,?,?)",
                (source_ids[item["source"]], item["text"], item["type"], item["status"], int(item["canonical"])),
            )
            inserted(cur, "source_claims", item["status"] == "unreviewed")
        for item in data["skips"]:
            cur = db.execute(
                "INSERT OR IGNORE INTO import_file_log(repository_path,content_hash,disposition,reason) VALUES (?,?,'skipped',?)",
                (item["path"], item["hash"], item["reason"]),
            )
            inserted(cur, "skipped_files")
    return report


def validation_errors(path: Path = DEFAULT_DB_PATH) -> list[str]:
    errors: list[str] = []
    with connect(path) as db:
        checks = {
            "Play This opening does not begin with PLAY THIS":
                "SELECT id FROM play_this_scripts WHERE opening_text NOT LIKE 'PLAY THIS%'",
            "ending hook has no learner need":
                "SELECT id FROM play_this_scripts WHERE learner_need_id IS NULL OR trim(closing_hook)=''",
            "script has no ordered teachable moments":
                "SELECT s.id FROM play_this_scripts s LEFT JOIN content_teachable_moments c ON c.content_item_id=s.content_item_id GROUP BY s.id HAVING COUNT(c.teachable_moment_id)=0",
            "visual asset has no attachment":
                "SELECT id FROM visual_assets WHERE content_item_id IS NULL AND teachable_moment_id IS NULL",
            "exercise has no instructional relationship":
                "SELECT id FROM exercises WHERE content_item_id IS NULL AND teachable_moment_id IS NULL",
            "Play This content is missing a script":
                "SELECT * FROM v_missing_scripts",
            "Play This content is missing a visual plan":
                "SELECT * FROM v_missing_visual_plans",
            "Play This content is missing a renderer implementation":
                "SELECT * FROM v_missing_renderer_implementations",
            "exercise is missing TAB, notation, audio, or backing-track assets":
                "SELECT * FROM v_missing_exercise_assets",
            "Part 2 or Part 3 chain is invalid":
                "SELECT * FROM v_part_chain_gaps",
            "referenced concept requires missing Play This content":
                "SELECT * FROM v_missing_play_this_concepts",
            "invalid local repository path":
                "SELECT id,repository_path FROM sources WHERE repository_path IS NOT NULL",
            "source package has no files":
                "SELECT p.id,p.slug FROM source_packages p LEFT JOIN source_package_files pf ON pf.source_package_id=p.id GROUP BY p.id HAVING COUNT(pf.source_file_id)=0",
            "external source root incorrectly marked tracked":
                "SELECT id,root_key FROM source_roots WHERE root_kind='external_library' AND tracked_in_git=1",
            "configured source root unavailable":
                "SELECT id,root_key,availability_status FROM source_roots WHERE is_active=1 AND availability_status<>'available'",
            "indexed source file missing":
                "SELECT id,relative_path,missing_status FROM source_files WHERE missing_status<>'present'",
            "source file lacks root-relative identity":
                "SELECT id,relative_path FROM source_files WHERE trim(relative_path)='' OR relative_path LIKE '/%' OR relative_path LIKE '%:%' OR relative_path LIKE '../%'",
            "stale parse result":
                "SELECT * FROM v_stale_source_extractions",
            "lick source phrase without provenance":
                "SELECT id,slug FROM lick_source_phrases WHERE trim(provenance)=''",
            "lick note has invalid ordering or duration":
                "SELECT id FROM lick_version_notes WHERE event_index<1 OR duration<=0",
            "fingering has no tuning":
                "SELECT id,slug FROM lick_fingerings WHERE trim(tuning)=''",
            "generated fingering marked canonical":
                "SELECT id,slug FROM lick_fingerings WHERE source_or_generated='generated' AND is_canonical=1",
            "harmonic analysis has no system":
                "SELECT id FROM lick_harmonic_analyses WHERE trim(analytical_system)=''",
            "application has no harmonic context":
                "SELECT id FROM lick_applications WHERE trim(chord_quality)=''",
        }
        for label, sql in checks.items():
            rows = list(db.execute(sql))
            if label == "invalid local repository path":
                rows = [r for r in rows if not (REPO_ROOT / r["repository_path"]).is_file()]
            if label == "Play This content is missing a renderer implementation":
                rows = [r for r in rows if not r["renderer_path"] or not (REPO_ROOT / r["renderer_path"]).is_file()]
            if label in {
                "Play This content is missing a script",
                "Play This content is missing a visual plan",
                "Play This content is missing a renderer implementation",
            }:
                rows = [
                    r for r in rows
                    if db.execute("SELECT import_status FROM content_items WHERE slug=?", (r["slug"],)).fetchone()[0] != "needs_review"
                ]
            if label == "invalid local repository path":
                rows = [
                    r for r in rows
                    if not db.execute("SELECT 1 FROM import_file_log WHERE repository_path=? AND disposition IN ('imported','needs_review')",
                                      (r["repository_path"],)).fetchone()
                ]
            errors.extend(f"{label}: {dict(row)}" for row in rows)
        fk = list(db.execute("PRAGMA foreign_key_check"))
        errors.extend(f"foreign key violation: {tuple(row)}" for row in fk)
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            errors.append(f"integrity_check: {integrity}")
    return errors


EXPORTS = {
    "play_this_readiness.csv": "SELECT * FROM v_play_this_readiness",
    "teachable_moment_lenses.csv": "SELECT * FROM v_teachable_moment_lenses",
    "unresolved_claims.csv": "SELECT * FROM v_external_claim_conflicts",
    "missing_assets.csv": "SELECT * FROM v_missing_exercise_assets",
    "imported_tunes.csv": "SELECT slug,title,status,import_status FROM tunes ORDER BY slug",
    "imported_systems.csv": "SELECT slug,name,status,import_status FROM systems ORDER BY slug",
    "imported_lenses.csv": "SELECT slug,name,authority,import_status FROM lenses ORDER BY slug",
    "imported_teachable_moments.csv": "SELECT slug,title,status,import_status FROM teachable_moments ORDER BY slug",
    "imported_play_this_items.csv": "SELECT slug,title,status,import_status FROM content_items WHERE content_type='play_this' ORDER BY slug",
    "incomplete_play_this_candidates.csv": "SELECT * FROM v_incomplete_play_this_candidates ORDER BY slug",
    "needs_review_records.csv": "SELECT * FROM v_needs_review_records ORDER BY entity_type,entity_slug",
    "source_provenance.csv": "SELECT * FROM v_source_provenance ORDER BY authority_level,slug",
    "skipped_files.csv": "SELECT repository_path,content_hash,reason FROM import_file_log WHERE disposition='skipped' ORDER BY repository_path",
    "configured_source_roots.csv": "SELECT root_key,display_name,root_kind,availability_status FROM v_source_roots ORDER BY root_key",
    "source_file_inventory.csv": "SELECT * FROM v_source_file_inventory ORDER BY root_key,relative_path",
    "exact_musical_data_files.csv": "SELECT * FROM v_exact_musical_data_files ORDER BY root_key,relative_path",
    "unsupported_source_files.csv": "SELECT * FROM v_unsupported_source_files ORDER BY root_key,relative_path",
    "missing_source_files.csv": "SELECT * FROM v_missing_source_files ORDER BY root_key,relative_path",
    "changed_source_files.csv": "SELECT * FROM v_changed_source_files ORDER BY root_key,relative_path",
    "duplicate_source_hashes.csv": "SELECT * FROM v_duplicate_source_hashes ORDER BY file_count DESC,current_sha256",
    "proposed_source_packages.csv": "SELECT * FROM v_proposed_source_packages ORDER BY title",
    "unresolved_package_groupings.csv": "SELECT * FROM v_unresolved_package_groupings ORDER BY title",
    "source_parse_support.csv": "SELECT * FROM v_source_parse_support ORDER BY root_key,extension",
    "source_extraction_readiness.csv": "SELECT * FROM v_extraction_readiness ORDER BY title",
    "stale_source_extractions.csv": "SELECT * FROM v_stale_source_extractions ORDER BY root_key,relative_path",
}


def export(path: Path = DEFAULT_DB_PATH) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        tables = [r["name"] for r in db.execute(
            "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        with (EXPORT_DIR / "table_counts.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["table_name", "row_count"])
            writer.writerows((table, db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) for table in tables)
        foundation_counts = {
            "tunes": 1, "systems": 0, "lenses": 4, "learner_needs": 3,
            "teachable_moments": 1, "content_items": 1, "content_relationships": 0,
            "sources": 1, "source_claims": 1,
        }
        with (EXPORT_DIR / "entity_counts_before_after.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["entity", "before_ingestion", "after_ingestion", "net_change"])
            for table, before in foundation_counts.items():
                after = db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                writer.writerow([table, before, after, after - before])
        for name, sql in EXPORTS.items():
            rows = list(db.execute(sql))
            with (EXPORT_DIR / name).open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(rows[0].keys() if rows else ["no_rows"])
                writer.writerows([tuple(r) for r in rows])
        counts = {
            r["name"]: db.execute(f'SELECT COUNT(*) FROM "{r["name"]}"').fetchone()[0]
            for r in db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        }
        try:
            display_path = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            display_path = str(path)
        (EXPORT_DIR / "database_summary.md").write_text(
            "# Highlander content database summary\n\n"
            f"Database: `{display_path}`\n\n"
            + "\n".join(f"- {name}: {count}" for name, count in sorted(counts.items()))
            + "\n",
            encoding="utf-8",
        )
        imported = list(db.execute(
            "SELECT title,authority_level,repository_path,content_hash FROM sources "
            "WHERE repository_path IS NOT NULL ORDER BY repository_path"
        ))
        (EXPORT_DIR / "import_report.md").write_text(
            "# Repository import report\n\n"
            "The importer uses a small allowlist, is idempotent, and records repository-relative paths and SHA-256 hashes.\n\n"
            + "\n".join(
                f"- `{r['repository_path']}` — {r['authority_level']}; `{r['content_hash']}`"
                for r in imported
            )
            + "\n\nSkipped by design: PDFs, images, audio/video, scratch output, raw archives, and unstructured bulk notes.\n",
            encoding="utf-8",
        )


def status(path: Path = DEFAULT_DB_PATH) -> dict:
    if not path.exists():
        return {"path": str(path), "exists": False}
    with connect(path) as db:
        return {
            "path": str(path),
            "exists": True,
            "size_bytes": path.stat().st_size,
            "migrations": db.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0],
            "integrity": db.execute("PRAGMA integrity_check").fetchone()[0],
            "foreign_key_violations": len(list(db.execute("PRAGMA foreign_key_check"))),
        }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Highlander content database")
    parser.add_argument("command", choices=["build", "migrate", "seed", "import-repository", "inventory-sources", "inspect-source-package", "compare-source-package", "extract-lick-package", "validate-licks", "list-licks", "show-lick", "transpose-lick", "generate-fingering-alternatives", "find-applications", "score-transitions", "export-lick-review", "generate-bh-review-assets", "validate", "export", "rebuild", "status"])
    parser.add_argument("--database", type=Path, default=Path(os.environ.get("HIGHLANDER_DB_PATH", DEFAULT_DB_PATH)))
    parser.add_argument("--full", action="store_true", help="Recompute all source hashes during inventory")
    parser.add_argument("subject", nargs="?", default="bh-5432")
    parser.add_argument("--semitones", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        if args.command == "migrate":
            print(json.dumps({"migrations_applied": migrate(args.database)}, indent=2))
        elif args.command == "seed":
            print(json.dumps(seed(args.database), indent=2))
        elif args.command == "import-repository":
            print(json.dumps(import_repository(args.database), indent=2))
        elif args.command == "inventory-sources":
            from .inventory import inventory_sources
            result = inventory_sources(args.database, full=args.full)
            export(args.database)
            print(json.dumps(result, indent=2))
        elif args.command == "generate-bh-review-assets":
            from .review_assets import generate_review_assets
            print(json.dumps(generate_review_assets(args.database),indent=2))
        elif args.command in {"inspect-source-package","compare-source-package","extract-lick-package","validate-licks","list-licks","show-lick","transpose-lick","generate-fingering-alternatives","find-applications","score-transitions","export-lick-review"}:
            from .licks import compare_package, export_lick_review, extract_package, package_info, transpose
            if args.command == "inspect-source-package": result = package_info(args.database,args.subject)
            elif args.command == "compare-source-package": result = compare_package(args.database,args.subject)
            elif args.command in {"extract-lick-package","generate-fingering-alternatives","score-transitions"}: result = extract_package(args.database,args.subject)
            elif args.command == "transpose-lick": result = transpose(args.database,args.subject,args.semitones)
            elif args.command == "validate-licks": result = {"errors":validation_errors(args.database)}
            elif args.command == "export-lick-review": export_lick_review(args.database); result={"export_dir":str(EXPORT_DIR)}
            else:
                with connect(args.database) as db:
                    if args.command=="list-licks": result=[dict(r) for r in db.execute("SELECT * FROM v_lick_catalog")]
                    elif args.command=="show-lick": result=[dict(r) for r in db.execute("SELECT * FROM v_lick_notes WHERE version=?",(args.subject,))]
                    else: result=[dict(r) for r in db.execute("SELECT * FROM v_lick_applications WHERE version=?",(args.subject,))]
            print(json.dumps(result,indent=2))
        elif args.command == "validate":
            errors = validation_errors(args.database)
            print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
            return 1 if errors else 0
        elif args.command == "export":
            export(args.database)
            print(json.dumps({"export_dir": str(EXPORT_DIR)}, indent=2))
        elif args.command in {"build", "rebuild"}:
            if args.command == "rebuild" and args.database.exists():
                args.database.unlink()
            migrate(args.database)
            seeded = seed(args.database)
            imported = import_repository(args.database)
            errors = validation_errors(args.database)
            export(args.database)
            print(json.dumps({"database": status(args.database), "seeded": seeded, "imported": imported, "errors": errors}, indent=2))
            return 1 if errors else 0
        else:
            print(json.dumps(status(args.database), indent=2))
    except (sqlite3.Error, OSError, RuntimeError) as exc:
        print(f"database command failed: {exc}")
        return 2
    return 0
