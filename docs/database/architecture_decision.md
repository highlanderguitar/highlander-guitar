# ADR: Highlander content database foundation

Status: accepted for the foundation slice.

## Decision

- SQLite is the canonical local engine. It is inspectable in DBeaver, needs no server, and remains portable because the schema avoids SQLite-only data modeling.
- The implementation uses Python's `sqlite3` module and ordered, checksummed SQL migrations under `sql/migrations`. This matches the repository's lightweight Python style and avoids adding a competing ORM or migration framework.
- The package is `highlander_render.db`; the generated database is `var/highlander_content.sqlite3`.
- Durable migrations, seed/import code, tests, queries, documentation, and small deterministic review exports are tracked. The live database, WAL/SHM files, private archives, caches, and machine-local configuration are ignored.
- Human-readable slugs are stable canonical identifiers; integer keys are internal relationships.
- Timestamps are UTC-like SQLite `CURRENT_TIMESTAMP` values. They are audit metadata, not source authority.
- Parent/owned rows cascade only where the child has no independent meaning. Canonical sources, lenses, learner needs, and relationship targets use restrictive deletion.
- Every imported document and claim retains source authority, path/citation, and content hash where available. External claims remain external and cannot silently become Highlander doctrine.
- SQL uses ordinary tables, foreign keys, checks, joins, and text timestamps to keep a later PostgreSQL migration straightforward.
- Source excerpts should be minimal and necessary. The database stores citations, hashes, and claim summaries rather than copyrighted full texts.

## Curriculum doctrine preserved

The database is a curriculum graph. Lenses attach to teachable moments with `active`, `referenced`, `prerequisite`, or `deferred` relationships. There is no global `primary_lens`. Play This scripts require `PLAY THIS` at the opening and a named learner need at the close. Part 2 and Part 3 require independent content and scripts and must be independently playable and loopable.
