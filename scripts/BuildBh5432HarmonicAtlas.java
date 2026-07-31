import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import app.tuxguitar.io.base.TGSongReaderHandle;
import app.tuxguitar.io.base.TGSongWriterHandle;
import app.tuxguitar.io.tg.TGSongReaderImpl;
import app.tuxguitar.io.tg.TGSongWriterImpl;
import app.tuxguitar.song.factory.TGFactory;
import app.tuxguitar.song.models.TGBeat;
import app.tuxguitar.song.models.TGChannel;
import app.tuxguitar.song.models.TGDuration;
import app.tuxguitar.song.models.TGMeasure;
import app.tuxguitar.song.models.TGMeasureHeader;
import app.tuxguitar.song.models.TGNote;
import app.tuxguitar.song.models.TGSong;
import app.tuxguitar.song.models.TGString;
import app.tuxguitar.song.models.TGText;
import app.tuxguitar.song.models.TGTrack;
import app.tuxguitar.song.models.TGVoice;

public class BuildBh5432HarmonicAtlas {
    private record ChordSpec(String symbol, String function, int[][] notes, int bassString, int bassFret) {}

    private static final ChordSpec CMAJ = new ChordSpec(
        "C", "I (NEUTRAL)", new int[][]{{5,3},{4,2},{3,0},{2,1},{1,0}}, 3, 3
    );
    private static final ChordSpec CMAJ7 = new ChordSpec(
        "Cmaj7", "Imaj7 (HYPOTHESIS)", new int[][]{{5,3},{4,2},{3,0},{2,0},{1,0}}, 3, 3
    );
    private static final ChordSpec CMAJ9 = new ChordSpec(
        "Cmaj9", "Imaj9 (HYPOTHESIS)", new int[][]{{5,3},{4,2},{3,0},{2,0},{1,3}}, 3, 3
    );
    private static final ChordSpec GMAJ = new ChordSpec(
        "G", "G MAJOR (USER-CORRECTED)", new int[][]{{6,3},{5,2},{4,0},{3,0},{2,0},{1,3}}, 4, 3
    );
    private static TGSong read(Path path, TGFactory factory) throws Exception {
        var handle = new TGSongReaderHandle();
        handle.setFactory(factory);
        try (var input = new FileInputStream(path.toFile())) {
            handle.setInputStream(input);
            new TGSongReaderImpl().read(handle);
        }
        return handle.getSong();
    }

    private static void write(Path path, TGSong song, TGFactory factory) throws Exception {
        var handle = new TGSongWriterHandle();
        handle.setFactory(factory);
        handle.setSong(song);
        try (var output = new FileOutputStream(path.toFile())) {
            handle.setOutputStream(output);
            new TGSongWriterImpl().write(handle);
        }
    }

    private static TGChannel channel(TGFactory factory, int id, int program, String name) {
        TGChannel channel = factory.newChannel();
        channel.setChannelId(id);
        channel.setBank((short)0);
        channel.setProgram((short)program);
        channel.setVolume((short)105);
        channel.setBalance((short)64);
        channel.setChorus((short)0);
        channel.setReverb((short)0);
        channel.setPhaser((short)0);
        channel.setTremolo((short)0);
        channel.setName(name);
        return channel;
    }

    private static List<TGString> guitarStrings(TGFactory factory) {
        int[] values = {64,59,55,50,45,40};
        List<TGString> strings = new ArrayList<>();
        for (int i = 0; i < values.length; i++) {
            TGString string = factory.newString();
            string.setNumber(i + 1);
            string.setValue(values[i]);
            strings.add(string);
        }
        return strings;
    }

    private static List<TGString> bassStrings(TGFactory factory) {
        int[] values = {43,38,33,28};
        List<TGString> strings = new ArrayList<>();
        for (int i = 0; i < values.length; i++) {
            TGString string = factory.newString();
            string.setNumber(i + 1);
            string.setValue(values[i]);
            strings.add(string);
        }
        return strings;
    }

    private static ChordSpec assignment(int measure) {
        if (measure == 26) {
            return GMAJ;
        }
        if (measure == 1) {
            return CMAJ7;
        }
        if ((measure >= 2 && measure <= 8)
            || (measure >= 10 && measure <= 28)
            || (measure >= 33 && measure <= 40)
            || (measure >= 42 && measure <= 43)) {
            return CMAJ9;
        }
        return null;
    }

    private static String sectionLabel(int measure) {
        return switch (measure) {
            case 1 -> "FROM 5 | Cmaj7 hypothesis | stable C E G B; chromatic descent ornamental | NEEDS REVIEW";
            case 2 -> "FROM 4 | Cmaj9 hypothesis | C E G B D structural; chromatic approaches | NEEDS REVIEW";
            case 8 -> "FROM 3 | Cmaj9 / G13 comparison unresolved | NEEDS REVIEW";
            case 10 -> "FROM 2 | Cmaj9 hypothesis; C-C#-D approach to 9th | NEEDS REVIEW";
            case 12 -> "ALL TOGETHER | Entry: sequence opportunity | Status: PROVISIONAL - REVIEW";
            case 21 -> "9th arp | Cmaj9 hypothesis (B natural, not C9) | NEEDS REVIEW";
            case 26 -> "G LICK | G major backing | USER-CORRECTED";
            default -> null;
        };
    }

    private static TGTrack newTrack(
        TGFactory factory, TGSong song, int number, int channelId, String name,
        List<TGString> strings
    ) {
        TGTrack track = factory.newTrack();
        track.setNumber(number);
        track.setSong(song);
        track.setName(name);
        track.setChannelId(channelId);
        track.setMaxFret(17);
        track.setStrings(strings);
        for (int i = 0; i < song.countMeasureHeaders(); i++) {
            track.addMeasure(factory.newMeasure(song.getMeasureHeader(i)));
        }
        return track;
    }

    private static TGBeat wholeNoteBeat(
        TGFactory factory, TGMeasure measure, int[][] notes, String text
    ) {
        TGBeat beat = factory.newBeat();
        beat.setPreciseStart(TGDuration.toPreciseTime(measure.getHeader().getStart()));
        if (text != null) {
            TGText tgText = factory.newText();
            tgText.setValue(text);
            beat.setText(tgText);
        }
        TGVoice voice = beat.getVoice(0);
        voice.getDuration().setValue(TGDuration.WHOLE);
        for (int[] pair : notes) {
            TGNote note = factory.newNote();
            note.setString(pair[0]);
            note.setValue(pair[1]);
            note.setVelocity(80);
            note.setVoice(voice);
            voice.addNote(note);
        }
        voice.setEmpty(notes.length == 0);
        measure.addBeat(beat);
        return beat;
    }

    private static int maximumFret(int string) {
        // Acoustic review boundary: avoid fret 17 on high E; every other string stops at 15.
        return (string == 1 ? 16 : 15);
    }

    private static int[] realizePitch(int midi, int previousString, int previousFret) {
        int[] tuning = {64,59,55,50,45,40};
        int bestString = 1;
        int bestFret = 0;
        int bestScore = Integer.MAX_VALUE;
        for (int octave = -2; octave <= 2; octave++) {
            int candidateMidi = midi + (12 * octave);
            for (int string = 1; string <= tuning.length; string++) {
                int fret = candidateMidi - tuning[string - 1];
                if (fret >= 0 && fret <= maximumFret(string)) {
                    // User edits favor the B/G strings over an avoidable high-E reach.
                    int highEAcousticPenalty = (string == 1 ? 3 : 0);
                    int octavePenalty = Math.abs(octave) * 8;
                    int score = Math.abs(fret - previousFret)
                        + 2 * Math.abs(string - previousString)
                        + highEAcousticPenalty + octavePenalty;
                    if (score < bestScore) {
                        bestScore = score;
                        bestString = string;
                        bestFret = fret;
                    }
                }
            }
        }
        if (bestScore == Integer.MAX_VALUE) {
            throw new IllegalArgumentException("No acoustic-safe fingering for MIDI note " + midi);
        }
        return new int[]{bestString, bestFret};
    }

    private static int[] realizeExactPitch(int midi, int previousString, int previousFret) {
        int[] tuning = {64,59,55,50,45,40};
        int[] best = null;
        int bestScore = Integer.MAX_VALUE;
        for (int string = 1; string <= tuning.length; string++) {
            int fret = midi - tuning[string - 1];
            if (fret >= 0 && fret <= maximumFret(string)) {
                int score = Math.abs(fret - previousFret)
                    + 2 * Math.abs(string - previousString)
                    + (string == 1 ? 3 : 0);
                if (score < bestScore) {
                    bestScore = score;
                    best = new int[]{string, fret};
                }
            }
        }
        if (best == null) {
            throw new IllegalArgumentException("No exact acoustic-safe fingering for MIDI note " + midi);
        }
        return best;
    }

    private static void copyOneOctaveLower(
        TGFactory factory, TGTrack sourceTrack, TGMeasure sourceMeasure,
        TGMeasure destination, String label
    ) {
        long sourceStart = TGDuration.toPreciseTime(sourceMeasure.getHeader().getStart());
        long destinationStart = TGDuration.toPreciseTime(destination.getHeader().getStart());
        int previousString = 5;
        int previousFret = 5;
        boolean firstBeat = true;
        for (TGBeat sourceBeat : sourceMeasure.getBeats()) {
            TGBeat beat = factory.newBeat();
            beat.setPreciseStart(destinationStart + sourceBeat.getPreciseStart() - sourceStart);
            if (firstBeat) {
                TGText text = factory.newText();
                text.setValue(label);
                beat.setText(text);
                firstBeat = false;
            }
            TGVoice sourceVoice = sourceBeat.getVoice(0);
            TGVoice voice = beat.getVoice(0);
            voice.getDuration().copyFrom(sourceVoice.getDuration());
            for (TGNote sourceNote : sourceVoice.getNotes()) {
                int sourceMidi = sourceTrack.getStrings().get(sourceNote.getString() - 1).getValue()
                    + sourceNote.getValue();
                int[] fingering = realizeExactPitch(sourceMidi - 12, previousString, previousFret);
                TGNote note = factory.newNote();
                note.setString(fingering[0]);
                note.setValue(fingering[1]);
                note.setVelocity(85);
                note.setVoice(voice);
                voice.addNote(note);
                previousString = fingering[0];
                previousFret = fingering[1];
            }
            voice.setEmpty(sourceVoice.getNotes().isEmpty());
            destination.addBeat(beat);
        }
    }

    private static void copyTransposedLick(
        TGFactory factory, TGTrack source, TGMeasure destination, int transposition,
        String label, int initialString, int initialFret, int octaveOffset
    ) {
        TGMeasure sourceMeasure = source.getMeasure(0);
        long sourceStart = TGDuration.toPreciseTime(sourceMeasure.getHeader().getStart());
        long destinationStart = TGDuration.toPreciseTime(destination.getHeader().getStart());
        int previousString = initialString;
        int previousFret = initialFret;
        boolean firstBeat = true;
        for (TGBeat sourceBeat : sourceMeasure.getBeats()) {
            TGBeat beat = factory.newBeat();
            beat.setPreciseStart(destinationStart + sourceBeat.getPreciseStart() - sourceStart);
            if (firstBeat) {
                TGText text = factory.newText();
                text.setValue(label);
                beat.setText(text);
                firstBeat = false;
            }
            TGVoice sourceVoice = sourceBeat.getVoice(0);
            TGVoice voice = beat.getVoice(0);
            voice.getDuration().copyFrom(sourceVoice.getDuration());
            for (TGNote sourceNote : sourceVoice.getNotes()) {
                int sourceMidi = source.getStrings().get(sourceNote.getString() - 1).getValue()
                    + sourceNote.getValue();
                int[] fingering = realizePitch(
                    sourceMidi + transposition + octaveOffset, previousString, previousFret
                );
                TGNote note = factory.newNote();
                note.setString(fingering[0]);
                note.setValue(fingering[1]);
                note.setVelocity(85);
                note.setVoice(voice);
                voice.addNote(note);
                previousString = fingering[0];
                previousFret = fingering[1];
            }
            voice.setEmpty(sourceVoice.getNotes().isEmpty());
            destination.addBeat(beat);
        }
    }

    private static int[][] chordVoicing(int transposition, boolean sixth) {
        int[] source = sixth ? new int[]{48,55,60,64,67,69} : new int[]{48,55,60,64,67};
        int[][] notes = new int[source.length][2];
        int previousString = 6;
        int previousFret = 3;
        for (int i = 0; i < source.length; i++) {
            int[] fingering = realizePitch(source[i] + transposition, previousString, previousFret);
            notes[i] = fingering;
            previousString = fingering[0];
            previousFret = fingering[1];
        }
        return notes;
    }

    private static void addCountIn(TGFactory factory, TGMeasure measure, String label) {
        long start = TGDuration.toPreciseTime(measure.getHeader().getStart());
        long quarter = TGDuration.WHOLE_PRECISE_DURATION / 4;
        for (int beatIndex = 0; beatIndex < 4; beatIndex++) {
            TGBeat beat = factory.newBeat();
            beat.setPreciseStart(start + beatIndex * quarter);
            if (beatIndex == 0) {
                TGText text = factory.newText();
                text.setValue(label + " | COUNT-IN 1 2 3 4");
                beat.setText(text);
            }
            TGVoice voice = beat.getVoice(0);
            voice.getDuration().setValue(TGDuration.QUARTER);
            TGNote note = factory.newNote();
            note.setString(1);
            note.setValue(12);
            note.setVelocity(70);
            note.setVoice(voice);
            voice.addNote(note);
            voice.setEmpty(false);
            measure.addBeat(beat);
        }
    }

    private static TGSong createCycleReview(TGFactory factory, TGTrack source) {
        TGSong cycleSong = factory.newSong();
        cycleSong.setName("BH-5432 Cycle Review");
        cycleSong.setComments(
            "Neutral major-triad cycle is primary. Sixth-chord layer is a future BH6 application and needs review."
        );
        long start = TGDuration.QUARTER_TIME;
        for (int index = 0; index < 60; index++) {
            TGMeasureHeader header = factory.newHeader();
            header.setNumber(index + 1);
            header.setStart(start);
            header.getTimeSignature().setNumerator(4);
            header.getTimeSignature().getDenominator().setValue(4);
            header.getTempo().setValueBase(70, TGDuration.QUARTER, false);
            cycleSong.addMeasureHeader(header);
            start += header.getLength();
        }
        cycleSong.addChannel(channel(factory, 30, 25, "Cycle licks"));
        cycleSong.addChannel(channel(factory, 31, 25, "Cycle alternate realizations"));
        cycleSong.addChannel(channel(factory, 32, 25, "Cycle neutral backing"));
        cycleSong.addChannel(channel(factory, 33, 32, "Cycle bass roots"));
        cycleSong.addChannel(channel(factory, 34, 115, "Cycle count-in"));
        cycleSong.addChannel(channel(factory, 35, 25, "Cycle sixth-chord preview"));
        TGTrack licks = newTrack(factory, cycleSong, 1, 30, "Cycle Licks - Neutral", guitarStrings(factory));
        TGTrack alternate = newTrack(factory, cycleSong, 2, 31, "Cycle Alternate Realizations", guitarStrings(factory));
        TGTrack neutral = newTrack(factory, cycleSong, 3, 32, "Cycle Neutral Backing - MAJOR TRIADS", guitarStrings(factory));
        TGTrack bass = newTrack(factory, cycleSong, 4, 33, "Cycle Bass / Root Guide", bassStrings(factory));
        TGTrack click = newTrack(factory, cycleSong, 5, 34, "Cycle Count-In", guitarStrings(factory));
        TGTrack sixth = newTrack(factory, cycleSong, 6, 35, "Cycle Sixth Chords - FUTURE BH6 REVIEW", guitarStrings(factory));

        int[] transpositions = {0,5,10,3,8,1,6,11,4,9,2,7};
        String[] labels = {"C","F","Bb","Eb","Ab","Db","Gb/F#","B","E","A","D","G"};
        for (int keyIndex = 0; keyIndex < labels.length; keyIndex++) {
            int base = keyIndex * 5;
            String context = labels[keyIndex] + " major | FROM 5 | NEUTRAL";
            addCountIn(factory, click.getMeasure(base), context);
            int[][] neutralChord = chordVoicing(transpositions[keyIndex], false);
            int[][] sixthChord = chordVoicing(transpositions[keyIndex], true);
            for (int offset : new int[]{1,2,3}) {
                wholeNoteBeat(
                    factory, neutral.getMeasure(base + offset), neutralChord,
                    context + (offset == 1 ? " | CHORD ALONE" : offset == 2 ? " | LICK OVER CHORD" : " | RESOLUTION")
                );
                wholeNoteBeat(
                    factory, sixth.getMeasure(base + offset), sixthChord,
                    "SIXTH-CHORD APPLICATION - FUTURE BH6 REVIEW | " + labels[keyIndex] + "6 | NEEDS REVIEW"
                );
                wholeNoteBeat(
                    factory, bass.getMeasure(base + offset),
                    new int[][]{{4, 8 + transpositions[keyIndex]}},
                    labels[keyIndex] + " root"
                );
            }
            copyTransposedLick(
                factory, source, licks.getMeasure(base + 2), transpositions[keyIndex],
                context + " | synchronized lick | acoustic-safe fingering", 4, 5, 0
            );
            copyOneOctaveLower(
                factory, licks, licks.getMeasure(base + 2), alternate.getMeasure(base + 2),
                context + " | ONE OCTAVE LOWER | acoustic-safe alternate | NEEDS REVIEW"
            );
        }
        cycleSong.addTrack(licks);
        cycleSong.addTrack(alternate);
        cycleSong.addTrack(neutral);
        cycleSong.addTrack(bass);
        cycleSong.addTrack(click);
        cycleSong.addTrack(sixth);
        return cycleSong;
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) {
            throw new IllegalArgumentException("usage: source.tg atlas.tg cycle-review.tg");
        }
        TGFactory factory = new TGFactory();
        TGSong song = read(Path.of(args[0]), factory);
        song.setName("BH-5432 Harmonic Atlas");
        song.setComments(
            "Canonical C instructional atlas. Harmonic applications and generated realizations are provisional."
        );
        song.getTrack(0).setName("Canonical lick material");
        song.getTrack(1).setName("Alternate / banjo realization");

        int derivedChannel = 20;
        int neutralChannel = 21;
        int bassChannel = 22;
        song.addChannel(channel(factory, derivedChannel, 25, "Atlas structure-derived backing"));
        song.addChannel(channel(factory, neutralChannel, 25, "Atlas neutral backing"));
        song.addChannel(channel(factory, bassChannel, 32, "Atlas bass roots"));
        TGTrack derived = newTrack(
            factory, song, song.countTracks() + 1, derivedChannel,
            "Structure-Derived Backing - NEEDS REVIEW", guitarStrings(factory)
        );
        TGTrack neutral = newTrack(
            factory, song, song.countTracks() + 2, neutralChannel,
            "Neutral Backing - MAJOR TRIADS", guitarStrings(factory)
        );
        TGTrack bass = newTrack(
            factory, song, song.countTracks() + 3, bassChannel,
            "Bass roots / harmonic guide", bassStrings(factory)
        );

        for (int i = 0; i < song.countMeasureHeaders(); i++) {
            int measureNumber = i + 1;
            ChordSpec chord = assignment(measureNumber);
            if (chord != null) {
                ChordSpec neutralChord = (measureNumber == 26 ? GMAJ : CMAJ);
                String label = sectionLabel(measureNumber);
                String text = (label != null ? label + " | " : "")
                    + "Chord: " + chord.symbol() + " | Function: " + chord.function();
                wholeNoteBeat(factory, derived.getMeasure(i), chord.notes(), text);
                wholeNoteBeat(
                    factory, neutral.getMeasure(i), neutralChord.notes(),
                    (measureNumber == 26
                        ? "User-corrected context | G major triad | G lick requires G backing"
                        : "Neutral canonical-C context | C major triad | no added 6/7/9")
                );
                wholeNoteBeat(
                    factory, bass.getMeasure(i),
                    new int[][]{{chord.bassString(), chord.bassFret()}},
                    "Root: " + chord.symbol().substring(0, 1)
                );
            }
        }
        song.addTrack(derived);
        song.addTrack(neutral);
        song.addTrack(bass);
        write(Path.of(args[1]), song, factory);
        write(Path.of(args[2]), createCycleReview(factory, song.getTrack(0)), factory);
    }
}
