# BH-Traversals source audit

Date: 2026-08-01

## Source selection

The canonical source is the user's `C:\Users\highl\OneDrive\Desktop\Tabs\bh-traversals.tg`.

| Candidate | Modified | Bytes | Measures | Visible annotations | Decision |
|---|---|---:|---:|---:|---|
| `bh-traversals.tg` | 2026-07-30 23:11:47 | 2,353 | 19 | 5 | Canonical: newest user-authored source named in the slice |
| `bh-traversals-expanded.tg` | 2026-07-20 23:10:17 | 8,126 | 80 | 80 | Reference only: older generated expansion, including realizations beyond the current acoustic fret limits |

Canonical SHA-256: `A2362B74FA3F8F60C5DA207478E97F72395E2067A8DA35C35F6CDFA03A89104C`

The byte-identical repository copy is `reviews/bh_traversals/canonical/BH-Traversals.tg`. Neither external source was changed.

## Native structure audit

- Native TuxGuitar parse: pass
- Tracks: 1 (`Track 1`)
- Measures: 19, all 4/4
- Tuning/string count: 6 strings
- Sounding-note measures: 16
- Deliberate separator measures: 5, 11, and 15
- Markers: none
- Maximum fret: 15

## Measure and annotation inventory

| Measure(s) | Annotation | Musical content |
|---|---|---|
| 1–4 | M1: `Up a 3rd, Down a Chord` | Four eight-note realizations/registers of the opening traversal |
| 5 | none | Deliberate empty separator |
| 6–9 | M6: `Up a 3rd, Down a Chord` | Four descending-return realizations |
| 10 | `(or lead back to the 1, via the 5)` | Alternate resolution attached to the M6 family |
| 11 | none | Deliberate empty separator |
| 12–14 | M12: `Down a 3rd, Down a Chord` | Three realizations; M14 uses a faster opening subdivision |
| 15 | none | Deliberate empty separator |
| 16–19 | M16: `Down a 3rd, Up a Chord` | Four realizations/registers of the closing traversal |

All five source annotations were retained verbatim in the canonical TG. The separator measures were retained because they encode the user's phrase-family layout rather than accidental trailing space.

## Corpus interpretation boundary

The audit treats the four annotated traversal families as phrase entities and the individual sounding measures as realizations. Harmonic labels, relationship types, successor rules, and confidence are added by the database/analysis slice; they are not written back into this preserved source file.
