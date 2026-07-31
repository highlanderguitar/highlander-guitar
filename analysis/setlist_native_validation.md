# Set-list native validation

- All 23 generated set-list TG files (14 canonical and 9 Tier 1 review files) passed the TuxGuitar 2.0.1 native parser, native save, and native reopen probe.
- The four exact retained TG sources and the uncertain `dixie-hoedown.tg` candidate also passed native parse/save/reopen when probed individually.
- Canonical notation/TAB timelines, backing, bass, click, capo, tuning, split-measure alignment, and physical-fret limits passed automated structural tests.
- Every generated TG has a nonempty MIDI and MusicXML support export.
- Desktop playback automation could not reliably acquire the TuxGuitar window in this environment. Audible playback and visual notation/TAB inspection remain explicit human review items; they are not reported as automated passes.
