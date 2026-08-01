# Highlander Guitar renderer and curriculum tools

This repository contains Highlander guitar rendering, analysis, doctrine, and curriculum tooling. The content database foundation models the curriculum as a provenance-aware graph and can be inspected with DBeaver.

## Content database

```powershell
$env:PYTHONPATH='src'
$python='C:\Users\highl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $python -m highlander_render.db rebuild
& $python -m highlander_render.db validate
& $python -m highlander_render.db status
```

See `docs/database/dbeaver_setup.md`, `docs/database/architecture_decision.md`, and `sql/dbeaver_queries.sql`.
