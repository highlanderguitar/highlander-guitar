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
import app.tuxguitar.song.models.TGNote;
import app.tuxguitar.song.models.TGSong;
import app.tuxguitar.song.models.TGString;
import app.tuxguitar.song.models.TGText;
import app.tuxguitar.song.models.TGTrack;
import app.tuxguitar.song.models.TGVoice;

public class BuildBh5432HarmonicAtlas {
    private record ChordSpec(String symbol, String function, int[][] notes, int bassString, int bassFret) {}

    private static final ChordSpec C6 = new ChordSpec(
        "C6", "I6 (PROVISIONAL)", new int[][]{{5,3},{4,2},{3,2},{2,1},{1,0}}, 3, 3
    );
    private static final ChordSpec C9 = new ChordSpec(
        "C9", "I9 (PROVISIONAL)", new int[][]{{5,3},{4,2},{3,3},{2,3}}, 3, 3
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
        if (measure == 21) {
            return C9;
        }
        if ((measure >= 1 && measure <= 8)
            || (measure >= 10 && measure <= 28)
            || (measure >= 30 && measure <= 31)
            || (measure >= 33 && measure <= 40)
            || (measure >= 42 && measure <= 43)) {
            return C6;
        }
        return null;
    }

    private static String sectionLabel(int measure) {
        return switch (measure) {
            case 1 -> "FROM 5 | Starts: 5 | Entry: tonic/chord arrival | Status: PROVISIONAL - REVIEW";
            case 2 -> "FROM 4 | Starts: 4 | Entry: static tonic or IV-color fill | Status: PROVISIONAL - REVIEW";
            case 8 -> "FROM 3 | Starts: 3 | Entry: tonic phrase opening | Status: PROVISIONAL - REVIEW";
            case 10 -> "FROM 2 | Starts: 2 | Entry: one-bar fill; C6 or G7 plausible | Status: PROVISIONAL - REVIEW";
            case 12 -> "ALL TOGETHER | Entry: sequence opportunity | Status: PROVISIONAL - REVIEW";
            case 21 -> "9th arp | Chord: C9 | Entry: tonic/dominant-color arrival | Status: PROVISIONAL - REVIEW";
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
        track.setMaxFret(29);
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

    private static int[] realizePitch(int midi, int previousString, int previousFret) {
        int[] tuning = {64,59,55,50,45,40};
        int bestString = 1;
        int bestFret = 0;
        int bestScore = Integer.MAX_VALUE;
        for (int octave = -2; octave <= 2; octave++) {
            int candidateMidi = midi + (12 * octave);
            for (int string = 1; string <= tuning.length; string++) {
                int fret = candidateMidi - tuning[string - 1];
                if (fret >= 0 && fret <= 19) {
                    int score = Math.abs(fret - previousFret) + 2 * Math.abs(string - previousString);
                    if (score < bestScore) {
                        bestScore = score;
                        bestString = string;
                        bestFret = fret;
                    }
                }
            }
        }
        return new int[]{bestString, bestFret};
    }

    private static void addCyclePreview(
        TGFactory factory, TGSong song, TGTrack source, TGTrack cycle
    ) {
        int[] transpositions = {0,5,10,3,8,1,6,11,4,9,2,7};
        String[] labels = {"C6","F6","Bb6","Eb6","Ab6","Db6","Gb/F#6","B6","E6","A6","D6","G6"};
        TGMeasure sourceMeasure = source.getMeasure(0);
        long sourceStart = TGDuration.toPreciseTime(sourceMeasure.getHeader().getStart());
        for (int keyIndex = 0; keyIndex < labels.length; keyIndex++) {
            TGMeasure destination = cycle.getMeasure(31 + keyIndex);
            long destinationStart = TGDuration.toPreciseTime(destination.getHeader().getStart());
            int previousString = 4;
            int previousFret = 5;
            boolean firstBeat = true;
            for (TGBeat sourceBeat : sourceMeasure.getBeats()) {
                TGBeat beat = factory.newBeat();
                beat.setPreciseStart(destinationStart + sourceBeat.getPreciseStart() - sourceStart);
                if (firstBeat) {
                    TGText text = factory.newText();
                    text.setValue(
                        "CYCLE PREVIEW | " + labels[keyIndex]
                        + " | FROM 5 | physical re-realization | NEEDS REVIEW"
                    );
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
                        sourceMidi + transpositions[keyIndex], previousString, previousFret
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
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("usage: source.tg atlas.tg");
        }
        TGFactory factory = new TGFactory();
        TGSong song = read(Path.of(args[0]), factory);
        song.setName("BH-5432 Harmonic Atlas");
        song.setComments(
            "Canonical C instructional atlas. Harmonic applications and generated realizations are provisional."
        );
        song.getTrack(0).setName("Canonical lick material");
        song.getTrack(1).setName("Alternate / banjo realization");

        int backingChannel = 20;
        int bassChannel = 21;
        int cycleChannel = 22;
        song.addChannel(channel(factory, backingChannel, 25, "Atlas backing guitar"));
        song.addChannel(channel(factory, bassChannel, 32, "Atlas bass roots"));
        song.addChannel(channel(factory, cycleChannel, 25, "Cycle preview guitar"));
        TGTrack backing = newTrack(
            factory, song, song.countTracks() + 1, backingChannel,
            "Backing chords - PROVISIONAL", guitarStrings(factory)
        );
        TGTrack bass = newTrack(
            factory, song, song.countTracks() + 2, bassChannel,
            "Bass roots / harmonic guide", bassStrings(factory)
        );
        TGTrack cycle = newTrack(
            factory, song, song.countTracks() + 3, cycleChannel,
            "Cycle of fourths preview - NEEDS REVIEW", guitarStrings(factory)
        );

        for (int i = 0; i < song.countMeasureHeaders(); i++) {
            int measureNumber = i + 1;
            ChordSpec chord = assignment(measureNumber);
            if (chord != null) {
                String label = sectionLabel(measureNumber);
                String text = (label != null ? label + " | " : "")
                    + "Chord: " + chord.symbol() + " | Function: " + chord.function();
                wholeNoteBeat(factory, backing.getMeasure(i), chord.notes(), text);
                wholeNoteBeat(
                    factory, bass.getMeasure(i),
                    new int[][]{{chord.bassString(), chord.bassFret()}},
                    "Root: " + chord.symbol().substring(0, 1)
                );
            }
        }
        song.addTrack(backing);
        song.addTrack(bass);
        addCyclePreview(factory, song, song.getTrack(0), cycle);
        song.addTrack(cycle);
        write(Path.of(args[1]), song, factory);
    }
}
