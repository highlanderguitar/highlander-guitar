from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .core import DEFAULT_DB_PATH, REPO_ROOT, connect, migrate

CONFIG_PATH = REPO_ROOT / "configs" / "source_roots.local.json"
EXACT = {".musicxml", ".mxl", ".tg", ".mid", ".midi", ".json", ".csv", ".txt"}
SUPPORTED = {".musicxml", ".mxl", ".json", ".csv", ".txt"}
PARTIAL = {".tg", ".mid", ".midi", ".pdf", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
PRIORITY = {".musicxml": 1, ".mxl": 1, ".tg": 2, ".mid": 3, ".midi": 3, ".json": 4, ".txt": 4, ".csv": 4, ".pdf": 5,
            ".svg": 6, ".png": 6, ".jpg": 6, ".jpeg": 6, ".webp": 6, ".gif": 6}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _classification(ext: str) -> tuple[str, int, str]:
    media = mimetypes.guess_type(f"x{ext}")[0] or "application/octet-stream"
    if ext in {".musicxml", ".mxl", ".tg", ".mid", ".midi"}:
        likely = "exact_musical_data"
    elif ext in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
        likely = "visual_reference"
    elif ext in {".json", ".csv", ".txt", ".md"}:
        likely = "structured_or_text_reference"
    else:
        likely = "unknown"
    support = "supported" if ext in SUPPORTED else "partial" if ext in PARTIAL else "unsupported"
    return media, int(ext in EXACT), support


def _package_key(path: Path) -> str:
    stem = path.stem.casefold()
    stem = re.sub(r"\s*\(\d+\)$", "", stem)
    stem = re.sub(r"[-_ ](?:with[-_ ]backing|backing(?:[-_ ]only)?(?:[-_ ]\d+bpm)?|analysis|corrected|repaired|youtube)$", "", stem)
    return re.sub(r"[^a-z0-9]+", "-", stem).strip("-")


def inventory_sources(database: Path = DEFAULT_DB_PATH, full: bool = False, config_path: Path = CONFIG_PATH) -> dict:
    migrate(database)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    totals = {"roots": {}, "new": 0, "changed": 0, "missing": 0, "unchanged": 0, "hashes_computed": 0}
    with connect(database) as db:
        run_id = db.execute(
            "INSERT INTO source_inventory_runs(mode,status) VALUES (?,'running')", ("full" if full else "fast",)
        ).lastrowid
        for root_key, cfg in config["source_roots"].items():
            configured = cfg["path"]
            candidate = Path(configured)
            resolved = candidate if candidate.is_absolute() else REPO_ROOT / candidate
            try:
                resolved = resolved.resolve()
                available = resolved.is_dir()
            except OSError:
                available = False
            status = "available" if available else "unavailable"
            db.execute(
                "INSERT INTO source_roots(root_key,display_name,root_kind,configured_path,resolved_absolute_path,"
                "is_repository_relative,is_machine_local,is_writable,tracked_in_git,availability_status,last_verified_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(root_key) DO UPDATE SET "
                "configured_path=excluded.configured_path,resolved_absolute_path=excluded.resolved_absolute_path,"
                "availability_status=excluded.availability_status,last_verified_at=CURRENT_TIMESTAMP",
                (root_key, root_key.replace("_", " ").title(), cfg["kind"], configured, str(resolved),
                 int(cfg["kind"] == "repository_relative"), int(candidate.is_absolute()), int(cfg.get("writable", False)),
                 int(cfg.get("tracked_in_git", False)), status),
            )
            root_id = db.execute("SELECT id FROM source_roots WHERE root_key=?", (root_key,)).fetchone()[0]
            if not available:
                db.execute("UPDATE source_files SET missing_status='unresolved' WHERE source_root_id=?", (root_id,))
                db.execute(
                    "INSERT INTO source_inventory_events(inventory_run_id,event_type,details) VALUES (?,'root_unavailable',?)",
                    (run_id, root_key),
                )
                totals["roots"][root_key] = {"available": False, "files": 0, "extensions": {}}
                continue
            seen: set[str] = set()
            extensions: dict[str, int] = defaultdict(int)
            for file in sorted((p for p in resolved.rglob("*") if p.is_file()), key=lambda p: str(p).casefold()):
                relative = file.relative_to(resolved).as_posix()
                normalized = relative.casefold()
                seen.add(normalized)
                ext = file.suffix.casefold()
                extensions[ext or "(none)"] += 1
                stat = file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
                old = db.execute(
                    "SELECT * FROM source_files WHERE source_root_id=? AND normalized_path=?", (root_id, normalized)
                ).fetchone()
                unchanged_metadata = old and old["file_size"] == stat.st_size and old["modified_time"] == mtime
                digest = old["current_sha256"] if unchanged_metadata and not full else _sha256(file)
                if not unchanged_metadata or full:
                    totals["hashes_computed"] += 1
                media, exact, support = _classification(ext)
                event = "new" if not old else "unchanged" if old["current_sha256"] == digest else "changed"
                if event == "new":
                    cur = db.execute(
                        "INSERT INTO source_files(source_root_id,relative_path,normalized_path,resolved_absolute_path,extension,"
                        "media_type,file_size,modified_time,current_sha256,likely_content_type,exact_musical_data,"
                        "parse_support_status,provenance,missing_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'present')",
                        (root_id, relative, normalized, str(file), ext, media, stat.st_size, mtime, digest,
                         _classification(ext)[0] and ("exact_musical_data" if exact else "reference"),
                         exact, support, f"{root_key}:{relative}"),
                    )
                    file_id = cur.lastrowid
                else:
                    file_id = old["id"]
                    db.execute(
                        "UPDATE source_files SET relative_path=?,resolved_absolute_path=?,extension=?,media_type=?,file_size=?,"
                        "modified_time=?,current_sha256=?,exact_musical_data=?,parse_support_status=?,missing_status='present',"
                        "last_seen_at=CURRENT_TIMESTAMP WHERE id=?",
                        (relative, str(file), ext, media, stat.st_size, mtime, digest, exact, support, file_id),
                    )
                db.execute(
                    "INSERT OR IGNORE INTO source_file_hashes(source_file_id,sha256,file_size,modified_time,inventory_run_id) VALUES (?,?,?,?,?)",
                    (file_id, digest, stat.st_size, mtime, run_id),
                )
                db.execute(
                    "INSERT INTO source_inventory_events(inventory_run_id,source_file_id,event_type,details) VALUES (?,?,?,?)",
                    (run_id, file_id, "unsupported" if support == "unsupported" else event, relative),
                )
                totals[event] += 1
            missing_rows = list(db.execute(
                "SELECT id,normalized_path FROM source_files WHERE source_root_id=? AND missing_status='present'", (root_id,)
            ))
            for old in missing_rows:
                if old["normalized_path"] not in seen:
                    db.execute("UPDATE source_files SET missing_status='missing' WHERE id=?", (old["id"],))
                    db.execute(
                        "INSERT INTO source_inventory_events(inventory_run_id,source_file_id,event_type,details) VALUES (?,?,'missing',?)",
                        (run_id, old["id"], old["normalized_path"]),
                    )
                    totals["missing"] += 1
            totals["roots"][root_key] = {"available": True, "files": len(seen), "extensions": dict(sorted(extensions.items()))}
        _build_packages(db)
        db.execute(
            "UPDATE source_inventory_runs SET completed_at=CURRENT_TIMESTAMP,status='complete',roots_scanned=?,files_seen=?,"
            "new_files=?,changed_files=?,missing_files=?,unchanged_files=? WHERE id=?",
            (len(totals["roots"]), sum(v["files"] for v in totals["roots"].values()), totals["new"], totals["changed"],
             totals["missing"], totals["unchanged"], run_id),
        )
        totals["duplicate_hash_groups"] = db.execute("SELECT COUNT(*) FROM v_duplicate_source_hashes").fetchone()[0]
        totals["proposed_packages"] = db.execute("SELECT COUNT(*) FROM source_packages").fetchone()[0]
        totals["run_id"] = run_id
    return totals


def _build_packages(db) -> None:
    groups: dict[str, list] = defaultdict(list)
    for row in db.execute("SELECT * FROM source_files WHERE missing_status='present'"):
        groups[_package_key(Path(row["relative_path"]))].append(row)
    for key, files in groups.items():
        if len(files) < 2 or not key:
            continue
        extensions = {f["extension"] for f in files}
        confidence = "high" if len({Path(f["relative_path"]).stem.casefold() for f in files}) == 1 else "medium"
        review = "proposed" if confidence == "high" else "needs_review"
        ordered = sorted(files, key=lambda f: PRIORITY.get(f["extension"], 99))
        exact = next((f for f in ordered if f["exact_musical_data"]), None)
        visual = next((f for f in ordered if f["extension"] in {".pdf", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif"}), None)
        audio = next((f for f in ordered if f["extension"] in {".mid", ".midi"}), None)
        db.execute(
            "INSERT INTO source_packages(slug,title,package_type,preferred_exact_file_id,preferred_visual_file_id,"
            "preferred_audio_file_id,confidence,review_status) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET "
            "preferred_exact_file_id=excluded.preferred_exact_file_id,preferred_visual_file_id=excluded.preferred_visual_file_id,"
            "preferred_audio_file_id=excluded.preferred_audio_file_id,confidence=excluded.confidence,review_status=excluded.review_status",
            (key, key.replace("-", " ").title(), "related_source_files", exact["id"] if exact else None,
             visual["id"] if visual else None, audio["id"] if audio else None, confidence, review),
        )
        package_id = db.execute("SELECT id FROM source_packages WHERE slug=?", (key,)).fetchone()[0]
        for file in files:
            db.execute(
                "INSERT OR IGNORE INTO source_package_files(source_package_id,source_file_id,relationship_type) VALUES (?,?,'related_version')",
                (package_id, file["id"]),
            )
