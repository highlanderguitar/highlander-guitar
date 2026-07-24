# DBeaver setup for the Highlander content database

## Exact database paths

- Absolute: `C:\Users\highl\prism-archive\projects\_bootstrap\highlander_migration\highlander_render\var\highlander_content.sqlite3`
- Repository-relative: `var\highlander_content.sqlite3`

The database is generated and intentionally ignored by Git. Migrations, seed/import code, queries, tests, and review exports are version-controlled.

## Connect in DBeaver

1. Launch `C:\Program Files\DBeaver\dbeaver.exe`.
2. Choose **Database > New Database Connection**.
3. Select **SQLite**, then **Next**.
4. In **Path**, browse to or paste the absolute database path above.
5. Choose **Test Connection**. If DBeaver asks to download its SQLite JDBC driver, allow that normal one-time driver installation.
6. Choose **Finish**.
7. Expand the connection, then **Tables** and **Views**. The expected foundation contains 18 domain/migration tables and 13 human-readable views.
8. Open an SQL editor for this connection and load `sql\dbeaver_queries.sql`.
9. Run `PRAGMA foreign_keys;`; it should return `1` for the connection. Run `PRAGMA foreign_key_check;`; it should return no rows. Run `PRAGMA integrity_check;`; it should return `ok`.

DBeaver has been found on this PC, but the database can be verified without requiring GUI automation.

## Rebuild and validate

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH='src'
$python='C:\Users\highl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $python -m highlander_render.db rebuild
& $python -m highlander_render.db validate
```

Other commands replace `rebuild` with `build`, `migrate`, `seed`, `import-repository`, `export`, or `status`.

## Locked database

Close data editors and transactions using the SQLite connection, disconnect DBeaver, and retry. Do not delete `-wal` or `-shm` files while a process has the database open. If necessary, exit DBeaver completely, confirm no Python database command is running, then rebuild.

## Editing policy

Use DBeaver primarily for inspection and review queries. Manual edits are not reproducible and will be lost on rebuild. Durable changes belong in migrations, seed code, or the provenance-aware importer, followed by tests and `rebuild`.
