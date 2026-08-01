# BH-Traversals review TG validation

All 14 files under `reviews/setlist/*/phrase_review` passed native TuxGuitar TG parsing after generation. Each file contains the four canonical guide tracks plus one independent `BH Traversal Review` track.

| Review file | Native open | Tracks | Review high-E max | Review other-string max | Acoustic limit |
|---|---|---:|---:|---:|---|
| bright-sunny-south | pass | 5 | 0 | 14 | pass |
| cant-you-hear-me-calling | pass | 5 | 0 | 12 | pass |
| dear-old-dixie | pass | 5 | 0 | 10 | pass |
| dig-a-hole-in-the-meadow | pass | 5 | 0 | 12 | pass |
| farewell-blues | pass | 5 | 7 | 9 | pass |
| i-feel-the-blues-movin-in | pass | 5 | 0 | 12 | pass |
| perfume-powder-and-lead | pass | 5 | 0 | 12 | pass |
| rank-strangers | pass | 5 | 0 | 10 | pass |
| sarafina | pass | 5 | 9 | 10 | pass |
| sitting-on-top-of-the-world | pass | 5 | 0 | 12 | pass |
| somehow-tonight | pass | 5 | 0 | 12 | pass |
| southern-flavor | pass | 5 | 6 | 6 | pass |
| trail-of-tears | pass | 5 | 6 | 6 | pass |
| walls-of-time | pass | 5 | 0 | 12 | pass |

The native generation path performed parse/save, and the validation pass reopened each result. Automated notation/TAB GUI inspection, audible playback, manual save/close/reopen, and musical approval were not automated and remain pending human review in TuxGuitar 2.0.1.
