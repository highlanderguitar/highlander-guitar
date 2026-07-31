# External source inventory

The database indexes source files in place. It never moves, renames, copies, or writes to either source folder, and it stores no binary file content.

## Configuration

- Tracked template: `configs/source_roots.example.json`
- Machine-local ignored configuration: `configs/source_roots.local.json`

The local configuration registers:

- `tabs_library`: external, read-only exact-musical-data library.
- `repository_input`: read-only repository intake and reference folder.

Canonical file identity is the source-root key plus the normalized relative path. SHA-256 history detects content changes. Cached absolute paths are regenerable from the local root configuration.

## Commands

```powershell
$env:PYTHONPATH='src'
$python='C:\Users\highl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $python -m highlander_render.db inventory-sources --full
& $python -m highlander_render.db inventory-sources
& $python -m highlander_render.db validate
```

Full mode hashes every file. Fast mode reuses the prior hash when size and UTC modified time are unchanged. Missing or unavailable roots retain prior records and hashes.

## Package policy

The inventory proposes packages for related basenames and conservative corrected/backing variants. Exact basename matches receive high confidence; heuristic groupings require review. MusicXML/MXL is preferred, followed by TuxGuitar, MIDI, structured text, PDF, images, and audio. Conflicting representations are retained.

Package proposals are preparation for lick extraction, not approval to extract or publish material.
