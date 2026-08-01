# Set-list TG cleanup audit

Date: 2026-08-01

## Authority and scope

- The current TG file in each `reviews/setlist/<tune>/canonical` and `bh_5432_review` directory was treated as authoritative.
- `source_working_copy`, `supporting_candidates`, and future `phrase_review` assets were excluded.
- User-edited measure headers, meter, tempo, repeats, rhythm notes, and application notes were retained.
- Empty text objects may remain in the TG serialization because TuxGuitar's model does not accept a null text assignment; all such text values are empty and render no label.

## Trail of Tears proof

`reviews/setlist/trail_of_tears/canonical/trail-of-tears.tg` was cleaned first and reopened with TuxGuitar's native TG reader before the operation was applied elsewhere.

| Check | Before | Reopened after cleanup |
|---|---:|---:|
| Measures | 27 | 27 |
| Rhythm/backing notes | 1,138 | 1,138 |
| Rhythm position/string/fret fingerprint | `7451095424404571089` | `7451095424404571089` |
| Visible rhythm chord labels | 296 | 30 |
| Bass last sounding measure | 17 | 27 |
| Click last sounding measure | 17 | 27 |
| Native TG reopen | pass | pass |

The added bass and click events cover the user's expanded measures 18–27. They are derived from the authoritative rhythm chord changes and existing measure lengths. No rhythm event was regenerated.

## Full-set results

- 23 current set-list TG files were saved and reopened successfully with the native TuxGuitar reader.
- 152 dead/X note events were removed from six files. The removal affected only notes explicitly marked with TuxGuitar's dead-note effect.
- Repeated prose chord descriptions were replaced by concise chord symbols at chord-change beats.
- Guide prose was removed; application-review labels were reduced to short musical cues where present.
- Existing bass/click tracks were extended only when a rhythm measure sounded and the corresponding guide measure was silent.
- Click extension uses each existing measure's actual length, so 3/4 and other meters are not forced into four beats.
- No measure was deleted: the pre-clean audit found no measure after the final globally sounding or annotated event in any in-scope TG.

## Playback status

Native parsing, native saving, and native reopening passed. Automated audible playback was not claimed; human playback review remains a TuxGuitar task.
