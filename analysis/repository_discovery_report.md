# Repository discovery report

## Selected root

`C:\Users\highl\prism-archive\projects\_bootstrap\highlander_migration\highlander_render`

This is the canonical root because it is an existing Git repository, contains the `highlander_render` Python package and Highlander doctrine/rendering material, and has the established remote `https://github.com/highlanderguitar/highlander-guitar.git`.

## Git state before database work

- Branch: `guardrail-render-cleanup`
- HEAD: `af7df8b9c28d5bfa55ce8f4be059f58d06dafa1c`
- Remote: `origin`
- Default historical branch present: `master`
- Numerous modified and untracked renderer, tune-analysis, source, data, and test files existed before this work.

The database work therefore uses `feature/content-database-foundation` and stages only files created or deliberately modified for this implementation. No pre-existing working-tree change is overwritten or committed.

## Existing architecture

- Package: `src/highlander_render`
- Tests: `pytest`
- Dependencies: small requirements file; no SQLAlchemy or Alembic
- Existing database implementation: none found
- Python command on PATH: unavailable
- Existing `.venv`: present but its base interpreter is stale/inaccessible
- Bundled Codex Python runtime: used for build and tests
- DBeaver: `C:\Program Files\DBeaver\dbeaver.exe`

## Source material and risks

The repository includes curated doctrine, manifests, analyses, JSON/CSV data, PDFs, images, transcripts, generated products, and large scratch/output trees. Raw media, private archives, temporary products, and the live database remain external to Git. The focused importer handles a small allowlist of doctrine/audit documents with hashes and authority classifications; it intentionally does not bulk-ingest PDFs, media, or every repository note.

The main unresolved risk is that the work begins from a renderer feature branch containing commits not yet on `master`. Existing user changes remain in the shared working tree and are excluded from database commits.
