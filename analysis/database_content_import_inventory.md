# Database content import inventory

Inventory date: 2026-07-24. The scan covered structured Markdown, JSON, YAML, CSV, and text under `docs`, `analysis`, `exports`, `data`, `fixtures`, `progressions`, and `score_parser/analysis`.

| Exact path | Format | Content represented | Likely entities | Canonical status | Confidence | Ambiguities | Automatic disposition |
|---|---|---|---|---|---|---|---|
| `docs/highlander_constitution.md` | Markdown | Governing publication doctrine | source, canonical claims, lenses | canonical by its explicit authority statement | high | broader than the content DB | Import source and two explicit claims |
| `fixtures/minor_pent_guardrail_doctrine.yaml` | JSON-compatible YAML | Enforced minor-pentatonic topology | source, system, lenses | canonical and regression-backed | high | visual corridors are outside this slice | Import source and system |
| `exports/take_five_teachable_moments.csv` | CSV | Four distinct learner problems, actions, lenses, exercises | tune, moments, systems, lenses, needs | Highlander-produced, provisional | high for rows; medium for harmonic labels | chord inference remains source-dependent | Import four separate moments; flag one |
| `exports/take_five_play_this_inventory.csv` | CSV | Three titled Play This candidates with openings, needs, Part 2 proposals, endings | content items, needs, relationships, candidate details | proposed | high for candidate metadata | no complete script; Part 2 is proposed | Import as `needs_review`, not scripts |
| `exports/take_five_phrase_inventory.csv` | CSV | Detailed extracted phrases and inferred targets | moments, systems, exercises | provisional analysis | medium | target chord degrees explicitly require review | Skip batch 001 |
| `analysis/take_five/take_five_*` | Markdown/JSON/TG | Source audit, form, harmony, grammar, playlist, renderer plans | tune, sources, systems, assets | mixed provisional package | medium-high | package files are untracked and partly generated | Review candidate for next batch |
| `exports/air_mail_special_external_claims.csv` | CSV | External-teacher claims with timestamps and confidence | external source claims, conflicts | external | high provenance; mixed claim confidence | exact music and history need adjudication | Import source plus one unreviewed doctrine candidate |
| `exports/air_mail_special_new_teachable_moments.csv` | CSV | Highlander synthesis mixed with external evidence | moments, Play This candidates, lenses | mixed proposed/external | medium | row-level authority varies | Skip pending adjudication |
| `analysis/charlie_christian/air_mail_special/**` | Markdown/JSON/text | Canonical analysis, structural units, transcripts, methodology | tune, units, systems, moments, sources, claims | mixed | medium-high | canonical analysis and external transcript trees coexist | Review batch |
| `analysis/swing_51/manifest.json` | JSON | Output filenames and counts | source/package metadata | generated manifest | low for curriculum import | no curriculum semantics | Skip |
| `score_parser/analysis/*.json` and subtrees | JSON/CSV | Parsed tune, chord, harmonic-function and treatment data | tunes, units, occurrences | structured but parser-derived | medium | many repairs and aggregate duplicates | Review batch; choose canonical layer first |
| `data/imports/i_am_a_pilgrim_*` | JSON | source-decision inventories and correction states | tune, moments, sources, review candidates | explicitly review-oriented | medium-high | unresolved human decisions | Review batch |
| `analysis/TEAL/**` | JSON/Markdown | cell library, etudes, reports, source extracts | systems, exercises, assets | mixed generated/experimental | low-medium | numerous drafts and repeated products | Do not auto-import |
| `archive/**`, `backups/**`, `tmp/**` | mixed | old implementations, scratch products, archived material | none by default | archived | low | stale/abandoned status | Excluded |

## Batch 001 decision

The reproducible manifest `data/database/ingestion_batch_001.json` records original repository-relative paths and SHA-256 hashes. It imports Take Five’s three strongest Play This candidates without inventing scripts, four separately supported teachable moments, two systems, ten lenses, three learner needs, two explicit prerequisite relationships, two canonical claims, and one external doctrine candidate. Incomplete or source-dependent entities are explicit review candidates.
