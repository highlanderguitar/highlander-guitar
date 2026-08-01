# Play This format source audit

## Governing doctrine

The supplied implementation brief is authoritative for this slice:

- “Play This videos are short, dense, loopable, and play-along.”
- “Play This scripts begin with `PLAY THIS`.”
- “the closing hook must name the actual learner need.”
- “Part 2 is independently playable and independently loopable.”
- “lenses belong at the teachable-moment level.”
- “there is no global `primary_lens`.”

These statements are encoded as schema constraints, relationships, validation, and tests.

## Repository sources found

- `exports/air_mail_special_segmentation_crosswalk.csv`: ten proposed Play This groupings mapped to structural units and motifs.
- `exports/air_mail_special_new_teachable_moments.csv`: learner needs, play-along actions, visual ideas, mistakes, transfers, and closing hooks.
- `analysis/charlie_christian/air_mail_special/air_mail_special_external_transcript_contribution_audit.md`: distinguishes canonical analysis, external claims, proposed atomic moments, and transfer exercises.
- `analysis/charlie_christian/swing_riffs_study/charlie_christian_swing_riffs_study_rundown.md`: short imperative “Play this” loop exercises.
- `scripts/audit_air_mail_special_external_transcripts.py`: generates the related review artifacts and preserves transcript provenance.
- `scripts/analyze_charlie_christian_swing_riffs_study.py`: generates short play instructions from structured study items.

## Agreements

The sources consistently support brief, imperative actions, loopable material, reusable cells, explicit learner problems, transfer beyond a single tune, visual plans, and source-sensitive claims.

## Contradictions and unresolved interpretation

Repository materials often use title-case `Play This:` as an editorial label, while the governing doctrine requires script openings to begin exactly with uppercase `PLAY THIS`. The schema treats the latter as canonical for script text without rewriting historical titles.

No reachable source precisely defines video duration, number of repetitions, tempo conventions, or a mandatory Part 3. Those rules are not invented here. Existing external-teacher transcripts remain external sources and unreviewed/conflicting claims are exposed separately.

## Canonical foundation specification

A Play This item is a content node connected to ordered teachable moments, a script, a learner need, optional part layers, visual assets, exercises, sources, and other curriculum nodes. Every later part must stand alone as both content and script and be independently playable and loopable.
