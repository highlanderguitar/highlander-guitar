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

public class BuildBh5432SetlistReview {
    private record Example(
        String tune, int tuneMeasure, String preceding, String active, String following,
        int sourceMeasure, int transposition, int resolutionMidi, String family, String why
    ) {}

    private static final Example[] EXAMPLES = {
        new Example("Walls of Time", 3, "G", "G", "G", 1, 7, 71, "FROM 5", "Repeated middle tonic gives the phrase air."),
        new Example("Walls of Time", 14, "C", "D7", "G", 8, -5, 67, "FROM 3", "Full dominant immediately before tonic."),
        new Example("I Feel the Blues Movin' In", 10, "G", "G", "G", 1, 7, 71, "FROM 5", "Long third tonic plateau; use during melody space."),
        new Example("I Feel the Blues Movin' In", 13, "G", "C", "C", 1, 0, 64, "FROM 5", "First of two static IV measures."),
        new Example("Dig a Hole in the Meadow", 3, "C", "C", "C", 1, 0, 64, "FROM 5", "Strongest canonical-C static-tonic window."),
        new Example("Dig a Hole in the Meadow", 6, "C", "C", "C", 2, 0, 60, "FROM 4 SHORT SEGMENT", "Late tonic before the split connector."),
        new Example("Sarafina", 14, "Em", "A7", "D", 8, 2, 62, "FROM 3", "Clear A dominant resolving to D."),
        new Example("Perfume, Powder and Lead", 2, "G", "G", "G", 1, 7, 71, "FROM 5", "Opening G plateau before D/G."),
        new Example("Rank Strangers", 7, "C", "C", "C", 1, 0, 64, "FROM 5", "Extended C tonic with room for development."),
        new Example("Rank Strangers", 42, "G", "G7", "C", 21, 0, 60, "9TH ARP / G13", "Late explicit G7 resolves decisively to C."),
        new Example("Dear Old Dixie", 20, "G", "G7", "C", 21, 0, 60, "9TH ARP / G13", "Cleanest original-root G13 to C opportunity."),
        new Example("Dear Old Dixie", 30, "A", "D7", "G", 8, -5, 67, "FROM 3", "End-of-form D-to-G turnaround."),
        new Example("Somehow Tonight", 8, "D7", "D7", "G", 8, -5, 67, "FROM 3", "Use the second dominant measure, then release."),
        new Example("Can't You Hear Me Calling", 14, "C", "D7", "G", 8, -5, 67, "FROM 3", "Final C-D-G cadence: preparation, opportunity, resolution."),
    };

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
        channel.setName(name);
        return channel;
    }

    private static List<TGString> strings(TGFactory factory, boolean bass) {
        int[] values = bass ? new int[]{43,38,33,28} : new int[]{64,59,55,50,45,40};
        List<TGString> result = new ArrayList<>();
        for (int i = 0; i < values.length; i++) {
            TGString string = factory.newString();
            string.setNumber(i + 1);
            string.setValue(values[i]);
            result.add(string);
        }
        return result;
    }

    private static TGTrack track(TGFactory factory, TGSong song, int number, int channelId, String name, boolean bass) {
        TGTrack track = factory.newTrack();
        track.setNumber(number);
        track.setSong(song);
        track.setName(name);
        track.setChannelId(channelId);
        track.setMaxFret(17);
        track.setStrings(strings(factory, bass));
        for (int i = 0; i < song.countMeasureHeaders(); i++) {
            track.addMeasure(factory.newMeasure(song.getMeasureHeader(i)));
        }
        return track;
    }

    private static int maxFret(int string) {
        return string == 1 ? 16 : 15;
    }

    private static int[] realize(int midi, int previousString, int previousFret) {
        int[] tuning = {64,59,55,50,45,40};
        int[] best = null;
        int bestScore = Integer.MAX_VALUE;
        for (int octave = -2; octave <= 2; octave++) {
            int pitch = midi + octave * 12;
            for (int string = 1; string <= 6; string++) {
                int fret = pitch - tuning[string - 1];
                if (fret >= 0 && fret <= maxFret(string)) {
                    int score = Math.abs(fret - previousFret) + 2 * Math.abs(string - previousString)
                        + Math.abs(octave) * 8 + (string == 1 ? 3 : 0);
                    if (score < bestScore) {
                        bestScore = score;
                        best = new int[]{string, fret};
                    }
                }
            }
        }
        if (best == null) throw new IllegalArgumentException("No acoustic-safe fingering for MIDI " + midi);
        return best;
    }

    private static int[][] chord(String symbol) {
        return switch (symbol) {
            case "C" -> new int[][]{{5,3},{4,2},{3,0},{2,1},{1,0}};
            case "C7" -> new int[][]{{5,3},{4,2},{3,3},{2,1},{1,0}};
            case "G" -> new int[][]{{6,3},{5,2},{4,0},{3,0},{2,0},{1,3}};
            case "G7" -> new int[][]{{6,3},{5,2},{4,0},{3,0},{2,0},{1,1}};
            case "D" -> new int[][]{{4,0},{3,2},{2,3},{1,2}};
            case "D7" -> new int[][]{{4,0},{3,2},{2,1},{1,2}};
            case "A" -> new int[][]{{5,0},{4,2},{3,2},{2,2},{1,0}};
            case "A7" -> new int[][]{{5,0},{4,2},{3,0},{2,2},{1,0}};
            case "Em" -> new int[][]{{6,0},{5,2},{4,2},{3,0},{2,0},{1,0}};
            default -> throw new IllegalArgumentException("Unsupported review chord " + symbol);
        };
    }

    private static int bassFret(String symbol) {
        return switch (symbol.substring(0, 1)) {
            case "C" -> 8;
            case "D" -> 10;
            case "E" -> 0;
            case "G" -> 3;
            case "A" -> 5;
            default -> 0;
        };
    }

    private static void whole(TGFactory factory, TGMeasure measure, int[][] notes, String text) {
        TGBeat beat = factory.newBeat();
        beat.setPreciseStart(TGDuration.toPreciseTime(measure.getHeader().getStart()));
        if (text != null) {
            TGText label = factory.newText();
            label.setValue(text);
            beat.setText(label);
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
    }

    private static void countIn(TGFactory factory, TGMeasure measure, String label) {
        long start = TGDuration.toPreciseTime(measure.getHeader().getStart());
        long quarter = TGDuration.WHOLE_PRECISE_DURATION / 4;
        for (int i = 0; i < 4; i++) {
            TGBeat beat = factory.newBeat();
            beat.setPreciseStart(start + i * quarter);
            if (i == 0) {
                TGText text = factory.newText();
                text.setValue(label + " | COUNT-IN 1 2 3 4");
                beat.setText(text);
            }
            TGVoice voice = beat.getVoice(0);
            voice.getDuration().setValue(TGDuration.QUARTER);
            TGNote note = factory.newNote();
            note.setString(1);
            note.setValue(12);
            note.setVelocity(65);
            note.setVoice(voice);
            voice.addNote(note);
            voice.setEmpty(false);
            measure.addBeat(beat);
        }
    }

    private static void copyLick(TGFactory factory, TGTrack source, int sourceNumber, TGMeasure destination,
                                 int transposition, String annotation) {
        TGMeasure sourceMeasure = source.getMeasure(sourceNumber - 1);
        long sourceStart = TGDuration.toPreciseTime(sourceMeasure.getHeader().getStart());
        long destinationStart = TGDuration.toPreciseTime(destination.getHeader().getStart());
        int previousString = 4;
        int previousFret = 5;
        boolean first = true;
        for (TGBeat sourceBeat : sourceMeasure.getBeats()) {
            TGBeat beat = factory.newBeat();
            beat.setPreciseStart(destinationStart + sourceBeat.getPreciseStart() - sourceStart);
            if (first) {
                TGText text = factory.newText();
                text.setValue(annotation);
                beat.setText(text);
                first = false;
            }
            TGVoice sourceVoice = sourceBeat.getVoice(0);
            TGVoice voice = beat.getVoice(0);
            voice.getDuration().copyFrom(sourceVoice.getDuration());
            for (TGNote sourceNote : sourceVoice.getNotes()) {
                int midi = source.getStrings().get(sourceNote.getString() - 1).getValue()
                    + sourceNote.getValue() + transposition;
                int[] fingering = realize(midi, previousString, previousFret);
                TGNote note = factory.newNote();
                note.setString(fingering[0]);
                note.setValue(fingering[1]);
                note.setVelocity(88);
                note.setVoice(voice);
                voice.addNote(note);
                previousString = fingering[0];
                previousFret = fingering[1];
            }
            voice.setEmpty(sourceVoice.getNotes().isEmpty());
            destination.addBeat(beat);
        }
    }

    private static void resolution(TGFactory factory, TGMeasure measure, int midi, String text) {
        int[] fingering = realize(midi, 3, 5);
        whole(factory, measure, new int[][]{fingering}, text);
    }

    private static void addVersion(TGFactory factory, Example example, int exampleIndex, int versionOffset,
                                   String tempoLabel, TGTrack source, TGTrack licks, TGTrack backing,
                                   TGTrack bass, TGTrack click, TGTrack notes) {
        int base = exampleIndex * 12 + versionOffset;
        String heading = example.tune() + " m" + example.tuneMeasure() + " | " + example.family()
            + " | " + tempoLabel;
        countIn(factory, click.getMeasure(base), heading);
        whole(factory, backing.getMeasure(base + 1), chord(example.preceding()), "PRECEDING: " + example.preceding());
        whole(factory, backing.getMeasure(base + 2), chord(example.active()), "ACTIVE: " + example.active());
        whole(factory, backing.getMeasure(base + 3), chord(example.following()), "RESOLUTION: " + example.following());
        whole(factory, backing.getMeasure(base + 4), chord(example.following()), "CONTINUATION: " + example.following());
        for (int offset : new int[]{1,2,3,4}) {
            String chordName = offset == 1 ? example.preceding() : offset == 2 ? example.active() : example.following();
            whole(factory, bass.getMeasure(base + offset), new int[][]{{4,bassFret(chordName)}}, "Root: " + chordName.substring(0,1));
        }
        copyLick(factory, source, example.sourceMeasure(), licks.getMeasure(base + 2), example.transposition(),
            heading + " | WHY: " + example.why());
        resolution(factory, licks.getMeasure(base + 3), example.resolutionMidi(), "TARGET / RESOLUTION");
        whole(factory, notes.getMeasure(base + 2), new int[][]{}, "Tier 1 | " + example.why());
        whole(factory, notes.getMeasure(base + 5), new int[][]{}, "SEPARATOR | next example");
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("usage: harmonic-atlas.tg setlist-review.tg");
        TGFactory factory = new TGFactory();
        TGSong atlas = read(Path.of(args[0]), factory);
        TGTrack source = atlas.getTrack(0);
        TGSong song = factory.newSong();
        song.setName("BH-5432 Set-list Application Review");
        song.setComments("Tier 1 only. Human TuxGuitar approval is required before database approval.");
        long start = TGDuration.QUARTER_TIME;
        int measureCount = EXAMPLES.length * 12;
        for (int i = 0; i < measureCount; i++) {
            TGMeasureHeader header = factory.newHeader();
            header.setNumber(i + 1);
            header.setStart(start);
            header.getTimeSignature().setNumerator(4);
            header.getTimeSignature().getDenominator().setValue(4);
            int withinExample = i % 12;
            int tempo = withinExample < 6 ? 70 : 120;
            header.getTempo().setValueBase(tempo, TGDuration.QUARTER, false);
            song.addMeasureHeader(header);
            start += header.getLength();
        }
        song.addChannel(channel(factory, 50, 25, "Tier 1 licks"));
        song.addChannel(channel(factory, 51, 25, "Aligned backing"));
        song.addChannel(channel(factory, 52, 32, "Bass roots"));
        song.addChannel(channel(factory, 53, 115, "Count in"));
        song.addChannel(channel(factory, 54, 25, "Review notes"));
        TGTrack licks = track(factory, song, 1, 50, "Tier 1 Licks / Resolutions", false);
        TGTrack backing = track(factory, song, 2, 51, "Preceding / Active / Following Harmony", false);
        TGTrack bass = track(factory, song, 3, 52, "Bass Root Guide", true);
        TGTrack click = track(factory, song, 4, 53, "Count-In", false);
        TGTrack notes = track(factory, song, 5, 54, "WHY This Opportunity", false);
        for (int i = 0; i < EXAMPLES.length; i++) {
            addVersion(factory, EXAMPLES[i], i, 0, "SLOW 70 BPM", source, licks, backing, bass, click, notes);
            addVersion(factory, EXAMPLES[i], i, 6, "SOURCE-TEMPO 120 BPM", source, licks, backing, bass, click, notes);
        }
        song.addTrack(licks);
        song.addTrack(backing);
        song.addTrack(bass);
        song.addTrack(click);
        song.addTrack(notes);
        write(Path.of(args[1]), song, factory);
    }
}
