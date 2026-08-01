import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.file.Files;
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

public class BuildSetlistLibrary {
    private record Tune(String slug, String title, String progression, int capo, int tempo, boolean dropD) {}
    private record Review(String slug, int measure, int sourceMeasure, int transposition, Integer continuationMeasure, Integer resolutionMeasure, int resolutionMidi, String reason) {}

    private static final Tune[] TUNES = {
        new Tune("walls_of_time", "Walls of Time", "G|G|G|G|G|G|C|F|G|G|G|G|C|D|G|G", 4, 140, false),
        new Tune("i_feel_the_blues_movin_in", "I Feel the Blues Movin' In", "G|G|G|D/G|G|G|G|D/G|G|G|G|G|C|C|G|G|C|C|G", 4, 120, false),
        new Tune("farewell_blues", "Farewell Blues", "C/G|C|C/G|C|A7|D/D#|C/G|C|C/G|C|C/G|C|C|A7|D/D#|C/G|C|C", 0, 100, false),
        new Tune("dig_a_hole_in_the_meadow", "Dig a Hole in the Meadow", "C|C|C|C|C|C|C/G|C|C", 0, 100, false),
        new Tune("sarafina", "Sarafina", "G|D|A|Bm|Em|Bm|A|A|G|D|A|Bm|Em|A|D|D|G/A|Bm|G|A|G|Bm|A|A|G/A|Bm|G/A|Bm|Em|A|D|D", 0, 100, false),
        new Tune("trail_of_tears", "Trail of Tears", "Em|D|Em|Em|Em|Em|Em|Em|A|A|B7|B7|B7|B7|Em|Em", 0, 120, false),
        new Tune("perfume_powder_and_lead", "Perfume, Powder and Lead", "G|G|G|D/G|C|C|G|G|G|D/G", 0, 100, false),
        new Tune("rank_strangers", "Rank Strangers", "C|C|C|G|C|C|C|C|C|C|C|D|G|G7|C|C|C|G|C|C|C|C|C|C|C|G|C|F|C|C|C|C|C|C|C|C|C|C|C|D|G|G7|C|C|C|F|C|C|C|C|C|C|Am|G|C|F|C", 0, 100, false),
        new Tune("dear_old_dixie", "Dear Old Dixie", "G|G|G|G|C|C|G|G|G|G|G|G|A|A|D|D|G|G|G|G7|C|C|B7|B7|C|C|G|Em|A|D|G|G", 0, 100, false),
        new Tune("bright_sunny_south", "Bright Sunny South", "G|G/F|Dsus2|Dsus2|Dsus2|Dsus2|Dsus2|G", 2, 120, true),
        new Tune("somehow_tonight", "Somehow Tonight", "G|G|G|G|G|G|D|D|G|G|G|G|G|G|D|G", 0, 100, false),
        new Tune("cant_you_hear_me_calling", "Can't You Hear Me Calling", "G|G|G|G|C|C|G|G|C|C|G|G|C|D|G", 0, 100, false),
        new Tune("sitting_on_top_of_the_world", "Sitting on Top of the World", "G|G/G7|C|G|G|Em|G/D|G", 0, 100, false),
        new Tune("southern_flavor", "Southern Flavor", "Em|Em|Em|Em|Em|Em|B7|B7|Em|Em|Em|Em|G|B7|Em|Em|D|D|E|E|D|D|B7|B7|Em|Em|Em|Em|G|B7|Em|Em", 0, 100, false),
    };

    private static final Review[] REVIEWS = {
        new Review("walls_of_time", 3, 1, 11, null, 4, 71, "Repeated sounding-B tonic / played-G shape."),
        new Review("i_feel_the_blues_movin_in", 10, 1, 11, null, 11, 71, "Long sounding-B tonic plateau."),
        new Review("dig_a_hole_in_the_meadow", 3, 1, 0, null, 4, 64, "Strong canonical-C static tonic."),
        new Review("sarafina", 15, 1, 2, null, 16, 66, "Two-measure D tonic arrival."),
        new Review("perfume_powder_and_lead", 2, 1, 7, null, 3, 71, "Opening G tonic plateau."),
        new Review("rank_strangers", 41, 8, 0, 42, 43, 60, "Two-measure G/G7 dominant region; rest/continue before C."),
        new Review("dear_old_dixie", 15, 8, -5, 16, 17, 67, "First of two D dominant measures; delay G resolution."),
        new Review("somehow_tonight", 7, 8, -5, 8, 9, 67, "First of two D dominant measures; delay G resolution."),
        new Review("cant_you_hear_me_calling", 2, 1, 7, null, 3, 71, "Opening G tonic space; short final D is not used."),
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
        Files.createDirectories(path.getParent());
        var handle = new TGSongWriterHandle();
        handle.setFactory(factory);
        handle.setSong(song);
        try (var output = new FileOutputStream(path.toFile())) {
            handle.setOutputStream(output);
            new TGSongWriterImpl().write(handle);
        }
    }

    private static TGChannel channel(TGFactory factory, int id, int program, String name) {
        TGChannel result = factory.newChannel();
        result.setChannelId(id);
        result.setBank((short)0);
        result.setProgram((short)program);
        result.setVolume((short)100);
        result.setBalance((short)64);
        result.setName(name);
        return result;
    }

    private static List<TGString> guitarStrings(TGFactory factory, boolean dropD) {
        int[] values = {64,59,55,50,45,dropD ? 38 : 40};
        List<TGString> result = new ArrayList<>();
        for (int i = 0; i < values.length; i++) {
            TGString string = factory.newString();
            string.setNumber(i + 1);
            string.setValue(values[i]);
            result.add(string);
        }
        return result;
    }

    private static List<TGString> bassStrings(TGFactory factory) {
        int[] values = {43,38,33,28};
        List<TGString> result = new ArrayList<>();
        for (int i = 0; i < values.length; i++) {
            TGString string = factory.newString();
            string.setNumber(i + 1);
            string.setValue(values[i]);
            result.add(string);
        }
        return result;
    }

    private static TGTrack track(TGFactory factory, TGSong song, int number, int channelId, String name, int capo, boolean bass, boolean dropD) {
        TGTrack track = factory.newTrack();
        track.setNumber(number);
        track.setSong(song);
        track.setName(name);
        track.setChannelId(channelId);
        track.setMaxFret(16);
        track.setOffset(capo);
        track.setStrings(bass ? bassStrings(factory) : guitarStrings(factory, dropD));
        for (int i = 0; i < song.countMeasureHeaders(); i++) track.addMeasure(factory.newMeasure(song.getMeasureHeader(i)));
        return track;
    }

    private static String root(String symbol) {
        if (symbol.startsWith("D#")) return "D#";
        return symbol.substring(0, 1);
    }

    private static String quality(String symbol) {
        String root = root(symbol);
        return symbol.substring(root.length());
    }

    private static int rootPc(String root) {
        return switch (root) { case "C" -> 0; case "D" -> 2; case "D#" -> 3; case "E" -> 4; case "F" -> 5; case "G" -> 7; case "A" -> 9; case "B" -> 11; default -> throw new IllegalArgumentException(root); };
    }

    private static String pitchName(int pc) {
        return new String[]{"C","C#","D","Eb","E","F","F#","G","Ab","A","Bb","B"}[(pc + 12) % 12];
    }

    private static String sounding(String played, int capo) {
        return pitchName(rootPc(root(played)) + capo) + quality(played);
    }

    private static int[][] chord(String symbol) {
        return switch (symbol) {
            case "C" -> new int[][]{{5,3},{4,2},{3,0},{2,1},{1,0}};
            case "G" -> new int[][]{{5,2},{4,0},{3,0},{2,0},{1,3}};
            case "G7" -> new int[][]{{5,2},{4,0},{3,0},{2,0},{1,1}};
            case "F" -> new int[][]{{4,3},{3,2},{2,1},{1,1}};
            case "D" -> new int[][]{{4,0},{3,2},{2,3},{1,2}};
            case "Dsus2" -> new int[][]{{4,0},{3,2},{2,3},{1,0}};
            case "D#" -> new int[][]{{5,6},{4,8},{3,8}};
            case "E" -> new int[][]{{5,2},{4,2},{3,1},{2,0},{1,0}};
            case "Em" -> new int[][]{{5,2},{4,2},{3,0},{2,0},{1,0}};
            case "A" -> new int[][]{{5,0},{4,2},{3,2},{2,2},{1,0}};
            case "A7" -> new int[][]{{5,0},{4,2},{3,0},{2,2},{1,0}};
            case "Am" -> new int[][]{{5,0},{4,2},{3,2},{2,1},{1,0}};
            case "B7" -> new int[][]{{5,2},{4,1},{3,2},{2,0},{1,2}};
            case "Bm" -> new int[][]{{5,2},{4,4},{3,4},{2,3},{1,2}};
            default -> throw new IllegalArgumentException("No voicing for " + symbol);
        };
    }

    private static int bassFret(String symbol) {
        return switch (root(symbol)) { case "C" -> 8; case "D" -> 10; case "D#" -> 11; case "E" -> 0; case "F" -> 1; case "G" -> 3; case "A" -> 5; case "B" -> 7; default -> 0; };
    }

    private static void beat(TGFactory factory, TGMeasure measure, long offset, int durationValue, int[][] notes, String text) {
        TGBeat beat = factory.newBeat();
        beat.setPreciseStart(TGDuration.toPreciseTime(measure.getHeader().getStart()) + offset);
        if (text != null) { TGText label = factory.newText(); label.setValue(text); beat.setText(label); }
        TGVoice voice = beat.getVoice(0);
        voice.getDuration().setValue(durationValue);
        for (int[] pair : notes) {
            TGNote note = factory.newNote(); note.setString(pair[0]); note.setValue(pair[1]); note.setVelocity(78); note.setVoice(voice); voice.addNote(note);
        }
        voice.setEmpty(notes.length == 0);
        measure.addBeat(beat);
    }

    private static void addClick(TGFactory factory, TGMeasure measure, String text) {
        long quarter = TGDuration.WHOLE_PRECISE_DURATION / 4;
        for (int i = 0; i < 4; i++) beat(factory, measure, i * quarter, TGDuration.QUARTER, new int[][]{{1,12}}, i == 0 ? text : null);
    }

    private static void addHarmony(TGFactory factory, Tune tune, TGMeasure backing, TGMeasure bass, String label) {
        String[] parts = label.split("/");
        long half = TGDuration.WHOLE_PRECISE_DURATION / 2;
        for (int i = 0; i < parts.length; i++) {
            String played = parts[i];
            int duration = parts.length == 2 ? TGDuration.HALF : TGDuration.WHOLE;
            long offset = parts.length == 2 ? i * half : 0;
            String text = "Sounding: " + sounding(played, tune.capo()) + " | Played shape: " + played
                + (parts.length == 2 ? " | SPLIT TIMING NEEDS REVIEW" : "");
            beat(factory, backing, offset, duration, chord(played), text);
            beat(factory, bass, offset, duration, new int[][]{{4,bassFret(played)}}, "Root: " + sounding(played, tune.capo()));
        }
    }

    private static int maxFret(int string, int capo) { return 16 - capo; }

    private static int[] realize(int midi, int capo, int previousString, int previousFret) {
        int[] tuning = {64,59,55,50,45,40};
        int[] best = null; int bestScore = Integer.MAX_VALUE;
        for (int octave = -2; octave <= 2; octave++) {
            int pitch = midi + octave * 12 - capo;
            for (int string = 1; string <= 6; string++) {
                int fret = pitch - tuning[string - 1];
                if (fret >= 0 && fret <= maxFret(string, capo)) {
                    int score = Math.abs(fret - previousFret) + 2 * Math.abs(string - previousString) + Math.abs(octave) * 8;
                    if (score < bestScore) { bestScore = score; best = new int[]{string,fret}; }
                }
            }
        }
        if (best == null) throw new IllegalArgumentException("No physical-fret-safe realization for MIDI " + midi + " capo " + capo);
        return best;
    }

    private static void copyLick(TGFactory factory, TGTrack source, int sourceNumber, TGMeasure destination, int transposition, int capo, String text) {
        TGMeasure sourceMeasure = source.getMeasure(sourceNumber - 1);
        long sourceStart = TGDuration.toPreciseTime(sourceMeasure.getHeader().getStart());
        long destinationStart = TGDuration.toPreciseTime(destination.getHeader().getStart());
        int previousString = 4, previousFret = 5; boolean first = true;
        for (TGBeat sourceBeat : sourceMeasure.getBeats()) {
            TGBeat targetBeat = factory.newBeat();
            targetBeat.setPreciseStart(destinationStart + sourceBeat.getPreciseStart() - sourceStart);
            if (first) { TGText label = factory.newText(); label.setValue(text); targetBeat.setText(label); first = false; }
            TGVoice sourceVoice = sourceBeat.getVoice(0), voice = targetBeat.getVoice(0);
            voice.getDuration().copyFrom(sourceVoice.getDuration());
            for (TGNote sourceNote : sourceVoice.getNotes()) {
                int midi = source.getStrings().get(sourceNote.getString() - 1).getValue() + sourceNote.getValue() + transposition;
                int[] fingering = realize(midi, capo, previousString, previousFret);
                TGNote note = factory.newNote(); note.setString(fingering[0]); note.setValue(fingering[1]); note.setVelocity(88); note.setVoice(voice); voice.addNote(note);
                previousString = fingering[0]; previousFret = fingering[1];
            }
            voice.setEmpty(sourceVoice.getNotes().isEmpty());
            destination.addBeat(targetBeat);
        }
    }

    private static Review reviewFor(String slug) {
        for (Review review : REVIEWS) if (review.slug().equals(slug)) return review;
        return null;
    }

    private static TGSong build(TGFactory factory, Tune tune, TGTrack lickSource, boolean reviewMode) {
        String[] progression = tune.progression().split("\\|");
        TGSong song = factory.newSong();
        song.setName(tune.title() + (reviewMode ? " - BH-5432 Review" : " - Canonical Practice Scaffold"));
        song.setComments("User progression is harmonic authority. Slash means successive half-measure chords. Melody remains uninvented.");
        long start = TGDuration.QUARTER_TIME;
        for (int i = 0; i < progression.length + 1; i++) {
            TGMeasureHeader header = factory.newHeader(); header.setNumber(i + 1); header.setStart(start);
            header.getTimeSignature().setNumerator(4); header.getTimeSignature().getDenominator().setValue(4);
            header.getTempo().setValueBase(tune.tempo(), TGDuration.QUARTER, false); song.addMeasureHeader(header); start += header.getLength();
        }
        int baseChannel = Math.abs(tune.slug().hashCode() % 40) + 60;
        song.addChannel(channel(factory, baseChannel, 25, "Lead guide"));
        song.addChannel(channel(factory, baseChannel + 1, 25, "Rhythm backing"));
        song.addChannel(channel(factory, baseChannel + 2, 32, "Bass guide"));
        song.addChannel(channel(factory, baseChannel + 3, 115, "Click"));
        if (reviewMode) song.addChannel(channel(factory, baseChannel + 4, 25, "BH-5432 application"));
        TGTrack lead = track(factory, song, 1, baseChannel, "Lead Guide", tune.capo(), false, tune.dropD());
        TGTrack backing = track(factory, song, 2, baseChannel + 1, "Rhythm / Backing Chords", tune.capo(), false, tune.dropD());
        TGTrack bass = track(factory, song, 3, baseChannel + 2, "Bass Guide", tune.capo(), true, false);
        TGTrack click = track(factory, song, 4, baseChannel + 3, "Click / Count-In", tune.capo(), false, tune.dropD());
        TGTrack application = reviewMode ? track(factory, song, 5, baseChannel + 4, "BH-5432 Application Review", tune.capo(), false, tune.dropD()) : null;
        beat(factory, lead.getMeasure(0), 0, TGDuration.WHOLE, new int[][]{}, "COUNT-IN | LEAD STARTS NEXT MEASURE");
        addClick(factory, click.getMeasure(0), "COUNT-IN 1 2 3 4");
        for (int i = 0; i < progression.length; i++) {
            int songMeasure = i + 1;
            String chord = progression[i];
            String marker = chord.contains("/") ? "SPLIT TIMING NEEDS REVIEW" :
                (i > 0 && progression[i - 1].equals(chord) ? "REPEATED CHORD / POSSIBLE FILL WINDOW" : "CHORD ARRIVAL / MELODY NEEDED");
            beat(factory, lead.getMeasure(songMeasure), 0, TGDuration.WHOLE, new int[][]{}, "Tune m" + (i + 1) + " | " + marker);
            addHarmony(factory, tune, backing.getMeasure(songMeasure), bass.getMeasure(songMeasure), chord);
            addClick(factory, click.getMeasure(songMeasure), "Tune m" + (i + 1));
        }
        if (reviewMode) {
            Review review = reviewFor(tune.slug());
            int active = review.measure(); // +1 count-in offset maps tune mN to song index N
            copyLick(factory, lickSource, review.sourceMeasure(), application.getMeasure(active), review.transposition(), tune.capo(), "TIER 1 | " + review.reason());
            if (review.continuationMeasure() != null) {
                beat(factory, application.getMeasure(review.continuationMeasure()), 0, TGDuration.WHOLE, new int[][]{}, "SUSTAIN/REST | CONTINUATION PHRASE NEEDED BEFORE TONIC");
            }
            if (review.resolutionMeasure() != null) {
                int[] fingering = realize(review.resolutionMidi(), tune.capo(), 3, 5);
                beat(factory, application.getMeasure(review.resolutionMeasure()), 0, TGDuration.WHOLE, new int[][]{fingering}, "TARGET / RESOLUTION");
            }
        }
        song.addTrack(lead); song.addTrack(backing); song.addTrack(bass); song.addTrack(click); if (reviewMode) song.addTrack(application);
        return song;
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("usage: harmonic-atlas.tg output-root");
        TGFactory factory = new TGFactory();
        TGSong atlas = read(Path.of(args[0]), factory);
        TGTrack lickSource = atlas.getTrack(0);
        Path outputRoot = Path.of(args[1]);
        for (Tune tune : TUNES) {
            Path canonical = outputRoot.resolve(tune.slug()).resolve("canonical").resolve(tune.slug().replace('_','-') + ".tg");
            write(canonical, build(factory, tune, lickSource, false), factory);
            if (reviewFor(tune.slug()) != null) {
                Path review = outputRoot.resolve(tune.slug()).resolve("bh_5432_review").resolve(tune.slug().replace('_','-') + "-BH5432-Review.tg");
                write(review, build(factory, tune, lickSource, true), factory);
            }
        }
    }
}
