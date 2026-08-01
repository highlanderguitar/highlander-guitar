# Phase A Etude Corpus Audit

**Audit-only gate:** no TG, MusicXML, companion Markdown, or manifest was modified.

- TG files audited: 10
- Rhythm measures audited: 100
- Rhythm measures failing chord legality: 35
- Individual illegal rhythm notes: 90
- Illegal bass events: 72
- Files with rhythm failures: 10

## Existing deliverables

## E08 — bm7_to_cmaj7_dorian.tg

- Current Track 1: `Bm7 to Cmaj7 Arpeggio Weave in A Dorian` (fails required traceability format)
- Current state: source-derived realization; 4 tracks; rhythm illegality in 2 measures; bass illegal events: 0.
- Source-supported facts: Weave Bm7 and Cmaj7 arpeggios derived from A Dorian.
- Unsupported/invented elements: Bm7 into Cmaj7 arpeggio weave explicitly shown. Underlying source chord is Am7; Bm7 and Cmaj7 are lead arpeggio resources, not backing changes.
- Required correction/action: **repair**. Correct prior source-image mapping (image-0026 was wrong lesson). Rename and repair backing only.
- User-edit evidence: no later edit detected relative to batch
- SHA-256: `835584b5519cbd44e28b201954c81da00ef67498588481e5f68b617f318b6429`

## E10 — happy_birthday_outline_to_etude.tg

- Current Track 1: `Form Outline to Eighth-Note Etude` (fails required traceability format)
- Current state: incomplete / needs source review; 4 tracks; rhythm illegality in 7 measures; bass illegal events: 0.
- Source-supported facts: Simplified form, voice-led triads, quarter-note outline, eighth-note etude, approaches/neighbors, blues coloring.
- Unsupported/invented elements: Current single eighth-note line is invented and collapses multiple requested demonstrations. Instructor simplifies to 1-5-5-1 | 1-4-5-1 in C; current file uses that but does not distinguish original from simplification.
- Required correction/action: **replace-with-family**. Replace with Happy Birthday family; current image-0169/0170 attribution is wrong because those are Hotel California around 21:52.
- User-edit evidence: no later edit detected relative to batch
- SHA-256: `36177d80bf4370cd2e363df3c538f2f154d4e7a5a2253b806e32aabb08f44136`

## E01 — d_dorian_diatonic_fourths.tg

- Current Track 1: `D Dorian Diatonic Fourth Cells` (fails required traceability format)
- Current state: source-derived realization; 4 tracks; rhythm illegality in 2 measures; bass illegal events: 0.
- Source-supported facts: Three-note fourth cells; roots rise by diatonic thirds; reverse after register turn.
- Unsupported/invented elements: Pitch cell logic explicitly described and image-0001 supplies tab. Transcript explicitly says D minor/D Dorian; eight-bar drill form is constructed.
- Required correction/action: **repair**. Retain lead concept; replace traceability name and audit constructed form.
- User-edit evidence: no later edit detected relative to batch
- SHA-256: `bb5ca24abd26436d0fa9b6c03f0790edefbf2a4c45368c2ac4fb398d3a99e258`

## E06 — jim_hall_fourths_through_251.tg

- Current Track 1: `Jim Hall Fourths Through ii-V-I` (fails required traceability format)
- Current state: source-derived realization; 4 tracks; rhythm illegality in 6 measures; bass illegal events: 24.
- Source-supported facts: Move a chosen interval through changes with rhythmic displacement.
- Unsupported/invented elements: Fourth device explicit; current pitch sequence is a realization, not Jim Hall transcription. Fm7-Bb7-Ebmaj7 stated by source; drill repetition constructed.
- Required correction/action: **repair**. Repair and rename; do not claim exact phrase.
- User-edit evidence: no later edit detected relative to batch
- SHA-256: `4dc1bbfcc236d9b20f87320e92f229f29e056977667383d46eaaaaa177ca1647`

## E02 — g_dorian_arrival_color.tg

- Current Track 1: `G Dorian Arrival Color in Minor ii-V-i` (fails required traceability format)
- Current state: source-derived realization; 4 tracks; rhythm illegality in 2 measures; bass illegal events: 0.
- Source-supported facts: E-natural Dorian color is emphasized on arrival at Gm7.
- Unsupported/invented elements: G Dorian E-natural arrival concept is explicit; current exact note ordering is constructed. Source minor ii-V-i is Am7b5-D7b9-Gm7; repeated drill form is constructed.
- Required correction/action: **repair**. Honest label should emphasize realization, not transcription.
- User-edit evidence: no later edit detected relative to batch
- SHA-256: `2f60070e521ceca54f49df7a1a37c0266651ad4ce59a82540094e9a0df78d6b6`

## E03 — one_minor_across_minor_251.tg

- Current Track 1: `One Minor Sound Across Minor ii-V-i` (fails required traceability format)
- Current state: pedagogical reconstruction; 4 tracks; rhythm illegality in 2 measures; bass illegal events: 0.
- Source-supported facts: Think G minor across the entire minor ii-V-i.
- Unsupported/invented elements: G minor pentatonic/blues/arpeggio strategy explicit; present line invented as exercise. Am7b5-D7b9-Gm7 stated by source.
- Required correction/action: **repair**. Retain as reconstruction after chord legality repair.
- User-edit evidence: no later edit detected relative to batch
- SHA-256: `7c85361fce37c7c996bac84f390df8a537661240a2a168c6908c632f1119fd23`

## E07 — a_dorian_four_dominant.tg

- Current Track 1: `A Dorian via the IV Dominant Sound` (fails required traceability format)
- Current state: pedagogical reconstruction; 4 tracks; rhythm illegality in 2 measures; bass illegal events: 0.
- Source-supported facts: Think IV dominant/D Mixolydian over A Dorian.
- Unsupported/invented elements: D Mixolydian emphasis over Am7 explicit; exact notes constructed. Source form is Am7 / Bbm7 bridge; IV-dominant concept is D7 over Am7. Current alternating Am7-D7 is a constructed drill, not tune form.
- Required correction/action: **replace-harmony-implementation-after-review**. Likely split into Am7 vamp with D7 conceptual annotation rather than literal D7 accompaniment.
- User-edit evidence: no later edit detected relative to batch
- SHA-256: `38d7cac6c0d2da2b91c42ef411fadae83e213b2116b71a1965eca0d92dd6fcf8`

## E09 — a_melodic_minor_contrast.tg

- Current Track 1: `A Melodic Minor Contrast Against A Dorian` (fails required traceability format)
- Current state: pedagogical reconstruction; 4 tracks; rhythm illegality in 2 measures; bass illegal events: 0.
- Source-supported facts: Raise Dorian seventh G to G# for A melodic minor contrast.
- Unsupported/invented elements: A melodic minor pitch collection explicit; current sequence constructed. A minor modal vamp source-supported; eight-bar form constructed.
- Required correction/action: **repair-metadata**. Retain as reconstruction; remove incorrect image-0027 attribution (Pat Metheny section).
- User-edit evidence: no later edit detected relative to batch
- SHA-256: `ff79f3dee053dc393f580593e2962631a8ff326c9936f2032788ed745ae4cb6a`

## E04 — abmaj7_over_bb7.tg

- Current Track 1: `Abmaj7 Upper Structure Over Bb7` (fails required traceability format)
- Current state: pedagogical reconstruction; 4 tracks; rhythm illegality in 6 measures; bass illegal events: 24.
- Source-supported facts: Abmaj7 tones over Bb7 yield b7, 9, 4, 13.
- Unsupported/invented elements: Abmaj7 pitch collection over Bb7 explicit; current line constructed. Fm7-Bb7-Ebmaj7 stated; repetition/form constructed.
- Required correction/action: **repair**. Repair illegal backing tones; classify individual upper extensions Teal, not whole file by engine branding.
- User-edit evidence: no later edit detected relative to batch
- SHA-256: `fe9a0f653536b4ae7481a78213035fee4f36a06a91f9746493f0668fcae74f25`

## E05 — g_minor_pentatonic_over_ebmaj7.tg

- Current Track 1: `G Minor Pentatonic Color Over Ebmaj7` (fails required traceability format)
- Current state: pedagogical reconstruction; 4 tracks; rhythm illegality in 4 measures; bass illegal events: 24.
- Source-supported facts: G minor pentatonic over Ebmaj7 supplies 9 and 13 plus chord tones.
- Unsupported/invented elements: G-Bb-D-F collection is present; source concept requires G minor pentatonic G-Bb-C-D-F, so C/13 must be made explicit without overwriting user work blindly. Concept target is Ebmaj7; current Fm7-Bb7-Ebmaj7 frame is source-context but must not obscure target.
- Required correction/action: **repair-first-preserve-user-edits**. Pink exercise. Chord tones keep priority; F=9 and C=13 split Pink/Teal when active. File modified 2026-08-01 12:06 after batch generation; preserve m5-6.
- User-edit evidence: YES — later mtime; preserve m5-6 rhythm voicings
- SHA-256: `38656093b514d2896682eab9c1995f320b860c52f28d0a557a0a64fdb63c2a3e`

## Missing Marbin deliverables and proposed split

The current E10 must be replaced, not merely renamed. Proposed Phase C IDs:

- E10A–D: Happy Birthday — quarter-note outline, eighth-note etude, melody-rhythm/arpeggio realization, free-practice backing.
- E11A–D: Lonesome Whistle — 3/4 AABA outline, eighth-note etude, melody-rhythm/arpeggio realization, free-practice backing.
- E12A–D: Hotel California — form outline, etude, source-supported melody-rhythm treatment if recoverable, free-practice backing.

Hotel California screenshots image-0169–0176 belong to the ~21:52 demonstration and must not remain attached to Happy Birthday. Lonesome Whistle evidence occupies the 16:07–20:35 transcript region; the 19:56 frame is a strong alignment anchor. Happy Birthday uses the simplified C progression 1-5-5-1 | 1-4-5-1 explicitly identified as the instructor's simplification.

## Proposed traceable Track 1 names

- E01 | Rosenwinkel Pattern | D Dorian Fourths | Source-derived
- E02 | Jim Hall / You'd Be So Nice | G Dorian Arrival | Source-derived
- E03 | Jim Hall / You'd Be So Nice | One-Minor ii-V-i | Reconstruction
- E04 | Jim Hall / You'd Be So Nice | Abmaj7 over Bb7 | Reconstruction
- E05 | Jim Hall / You'd Be So Nice | Gm Pent over Ebmaj7 | Reconstruction
- E06 | Jim Hall / You'd Be So Nice | Fourths Through ii-V-I | Source-derived
- E07 | Pat Martino / Impressions | IV-Dominant Lens | Reconstruction
- E08 | Pat Martino / Impressions | Bm7-Cmaj7 Weave | Source-derived
- E09 | Pat Martino / Impressions | Melodic Minor Contrast | Reconstruction
- E10A–D / E11A–D / E12A–D use the Marbin tune-and-device format specified above.

## Phase B order

1. Snapshot and compare E05, preserving user-corrected rhythm m5–6.
2. Repair E05 harmony/bass and implement Pink plus per-tone split Pink/Teal semantics.
3. Replace vague Track 1 names across E01–E09.
4. Correct every failed rhythm voicing and bass mismatch with symbol-literal chord tones only.
5. Regenerate records/manifests and run native reopen plus chord-legality gate.

## Gate decision

The scope matches the requested repair, but source audit proves E07's D7 accompaniment and E10's source-image attribution require substantive replacement. Per the requested implementation order, stop here for review before Phase B.
