# BH-5432 source comparison

Package `bh-5432` contains `BH-5432.musicxml` (`90bafb3c…75a5c`) and `BH-5432.tg` (`075f05e9…07e1`) in `tabs_library`.

- Both identify two tracks (`Track 1`, `Banjo`) and 26 exported measures per track.
- TG explicitly stores 4/4 and 120 BPM. MusicXML carries 4/4 attributes but no tempo sound element.
- MusicXML is preferred for written pitches, octaves, onset/duration, rests, ties, and notation event order.
- TG is preferred for tempo, six-string guitar tuning, string/fret realization, beat annotations, and TuxGuitar-native metadata.
- MusicXML contains 482 note elements in Track 1 and 388 in Banjo. These counts include rests/notation events and are not silently equated with TG sounding-note counts.
- Neither representation contains harmony elements. Chord-relative applications therefore remain conservative and reviewable.
- No source supports verified historical authorship of every phrase. Attribution is stored as “Barry Harris 5432 analytical system; user-owned transcription/arrangement,” not verified authorship.

The sources are structurally equivalent at package/track/measure level. Tempo absence in MusicXML is a harmless metadata difference. Fingering authority is representationally stronger in TG. Harmony and exact cross-format event parity remain unresolved but are not blockers for importing a small source-preserving proof corpus.
