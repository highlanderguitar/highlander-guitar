# BH-5432 TuxGuitar format failure

## Environment

- Application: TuxGuitar 2.0.1, Windows SWT x86_64 distribution
- Launcher: `C:\Users\highl\Downloads\tuxguitar-2.0.1-windows-swt-x86_64\tuxguitar-2.0.1-windows-swt-x86_64\tuxguitar.exe`
- Java process: the distribution's `jre\bin\javaw.exe`
- Known-good authority: external `BH-5432.tg` (left unmodified)

The known-good source opened in the installed application as
`TuxGuitar - BH-5432.tg`. Its installed native detector, reader, writer, and
reopen cycle also succeeded with 2 tracks, 58 track-measures, and 352 notes.

## Known-good versus failed archive

| Property | Known-good BH-5432.tg | Failed generated comparison |
|---|---|---|
| Archive entries | `version.txt`, `content.xml` | same |
| `version.txt` | `TuxGuitar_file_format 2.0` | `TuxGuitar file format 2.0` |
| Root | `TuxGuitarFile` | same |
| Version element | `TGVersion major="2" minor="0" revision="1"` | same |
| Song root | `TGSong` | same |
| Namespace declarations | none | none |
| Ordered song metadata | name plus artist, album, author, date, copyright, writer, transcriber, comments | name only |
| Serializer | TuxGuitar 2.0.1 native writer | handwritten ZIP/XML writer |

There is no extra manifest in this 2.0 format. The two required archive
members and the exact native version token are the archive-level metadata.

## First failures and precise cause

The first application failure was:

> Cannot invoke `TGVersion.getMajor()` because `version` is null

TuxGuitar's `TGFileFormatDetectorImpl` reads `version.txt` and recognizes the
exact `TuxGuitar_file_format 2.0` token. Spaces in place of underscores caused
format-version detection to return null. The XML `TGVersion` element could not
repair an archive that had already failed format detection.

After correcting that token, the installed native reader exposed a second
failure at `TGSongReaderImpl.readSong`: the handwritten document omitted the
ordered empty song-metadata siblings expected by the reader. The repair adds
all native metadata elements in their required order.

## Why the old validator passed invalid files

The old check proved only that the file was a readable ZIP containing
well-formed XML and plausible string/fret attributes. It did not:

- compare the exact native version token;
- invoke TuxGuitar's format detector or song reader;
- enforce the reader's ordered document shape;
- open the file in the application;
- exercise playback;
- save and reopen through the native writer.

Those structural checks are useful diagnostics, but they are not evidence that
a TG file is review-ready.

## Repair and acceptance

The generator now emits the exact 2.0 archive token and the required ordered
song metadata. The original ten failures are preserved under
`reviews/bh_5432/_invalid_generated_tg/`; the primary review paths contain the
repaired files.

All ten repaired files passed:

1. installed TuxGuitar 2.0.1 format detector;
2. installed native song reader;
3. isolated real application open;
4. responsive start/stop playback smoke test;
5. installed native writer save;
6. native reopen with an identical structural/musical fingerprint.

The fingerprint covers track names, track and measure counts, note counts,
tuning, string/fret assignments, voice durations, meter, tempo, and channel
bank/program. No loss was detected. The TG files were generated from the same
database events as their MusicXML companions; MusicXML was not used as a
lossy intermediate in this repair.

