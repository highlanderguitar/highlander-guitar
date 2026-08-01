# Set-list cleanup and correction suggestions

Automatic repairs were limited to unreadable text, explicit dead-note events, and missing bass/click coverage where the authoritative rhythm measure sounded. Harmony, meter, repeats, and rhythm notes were not silently rewritten.

## Auto-repair summary

- Removed 152 notes carrying TuxGuitar's dead-note/X effect while retaining the other notes on each beat.
- Reduced repeated chord prose to chord symbols at actual chord-change beats.
- Extended bass/click coverage only where rhythm sounded beyond those guide tracks.
- Deleted no trailing measures because no in-scope file had empty measures after its final global musical/structural event.

## Suggestions requiring approval

| Tune | Measure/region | Current value | Possible correction | Evidence | Confidence | Approval required |
|---|---|---|---|---|---:|---|
| Dear Old Dixie review | 18–33 | Rhythm stops at M17 while bass/click continue to M33 | Confirm whether M18–33 belong to the current form or are guide-only continuation | Native track audit; application note occurs at M18 | 0.78 | yes |
| Rank Strangers review | 43–81 | Rhythm stops at M42; bass/click continue and application reaches M62 | Confirm the intended long form and regenerate rhythm only if the user says it is missing | Native track audit | 0.82 | yes |
| Sarafina review | 34–44 | Rhythm stops at M33 while bass/click continue | Confirm whether M34–44 are an ending/rehearsal extension | Native track audit | 0.76 | yes |
| Somehow Tonight review | 11–19 | Rhythm stops at M10 while bass/click continue; application reaches M12 | Confirm whether the later guide measures are intentional | Native track audit | 0.80 | yes |
| Farewell Blues | D/D♯ split | Following harmony is functionally ambiguous for A7 resolution | Confirm the actual chord and split beat before approving a traversal | Existing user progression and opportunity audit | 0.55 | yes |
| Bright Sunny South | Dsus2 plateau | Suspended quality conflicts with a phrase that asserts F♯ | Keep as review-only or choose a no-third fragment | Note-structure analysis | 0.84 | yes |
| Sitting on Top of the World | M7 split | Full-measure review phrase is longer than the proposed second-half window | Approve a two-beat extraction and exact split beat | Current chord split and phrase duration | 0.74 | yes |

Unusual harmony and meter were preserved when structurally valid. Audible playback and stylistic approval remain human TuxGuitar checks.
