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
import app.tuxguitar.song.models.TGDuration;
import app.tuxguitar.song.models.TGMeasure;
import app.tuxguitar.song.models.TGNote;
import app.tuxguitar.song.models.TGSong;
import app.tuxguitar.song.models.TGText;
import app.tuxguitar.song.models.TGTrack;
import app.tuxguitar.song.models.TGVoice;

public class CleanSetlistTg {
    private record ChordEvent(long offset, String displayed, String playedShape) {}

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

    private static String soundingChord(String text) {
        if (text == null) return null;
        String value = text.trim();
        if (value.startsWith("Sounding:")) {
            value = value.substring("Sounding:".length()).trim();
            int separator = value.indexOf('|');
            if (separator >= 0) value = value.substring(0, separator).trim();
        }
        if (value.matches("[A-G](#|b)?(m|7|m7|sus2)?")) return value;
        return null;
    }

    private static String playedShape(String text, String fallback) {
        if (text != null && text.contains("Played shape:")) {
            String value = text.substring(text.indexOf("Played shape:") + "Played shape:".length()).trim();
            int separator = value.indexOf('|');
            if (separator >= 0) value = value.substring(0, separator).trim();
            if (value.matches("[A-G](#|b)?(m|7|m7|sus2)?")) return value;
        }
        return fallback;
    }

    private static String conciseReviewText(String text) {
        if (text == null) return null;
        String upper = text.toUpperCase();
        if (upper.contains("COUNT-IN")) return "COUNT-IN";
        if (upper.contains("FROM 3")) return "BH5432 FROM 3";
        if (upper.contains("FROM 5")) return "BH5432 FROM 5";
        if (upper.contains("FROM 4")) return "BH5432 FROM 4";
        if (upper.contains("9TH ARP")) return "BH5432 9TH ARP";
        if (upper.contains("TRAVERSAL")) return text.length() <= 32 ? text : "TRAVERSAL";
        if (upper.contains("TARGET") || upper.contains("RESOLUTION")) return "TARGET";
        if (upper.contains("CONTINUATION") || upper.contains("CONTINUE")) return "CONTINUE";
        if (upper.matches("(VERSE|CHORUS|TURNAROUND|INTRO|OUTRO|BRIDGE).*")) return text;
        return null;
    }

    private static int bassFret(String symbol) {
        if (symbol.startsWith("D#") || symbol.startsWith("Eb")) return 11;
        return switch (symbol.substring(0, 1)) {
            case "C" -> 8; case "D" -> 10; case "E" -> 0; case "F" -> 1;
            case "G" -> 3; case "A" -> 5; case "B" -> 7; default -> 0;
        };
    }

    private static void addBeat(TGFactory factory, TGMeasure measure, long preciseStart, int duration, int string, int fret, String text) {
        TGBeat beat = factory.newBeat();
        beat.setPreciseStart(preciseStart);
        if (text != null) { TGText tgText = factory.newText(); tgText.setValue(text); beat.setText(tgText); }
        TGVoice voice = beat.getVoice(0);
        voice.getDuration().setValue(duration);
        TGNote note = factory.newNote(); note.setString(string); note.setValue(fret); note.setVelocity(72); note.setVoice(voice); voice.addNote(note);
        voice.setEmpty(false); measure.addBeat(beat);
    }

    private static boolean hasNotes(TGMeasure measure) {
        for (TGBeat beat : measure.getBeats()) for (int voiceIndex = 0; voiceIndex < 2; voiceIndex++) if (!beat.getVoice(voiceIndex).getNotes().isEmpty()) return true;
        return false;
    }

    private static List<ChordEvent> cleanRhythmMeasure(TGMeasure measure) {
        List<ChordEvent> events = new ArrayList<>();
        String previous = null;
        long measureStart = TGDuration.toPreciseTime(measure.getHeader().getStart());
        for (TGBeat beat : measure.getBeats()) {
            String original = beat.getText() != null ? beat.getText().getValue() : null;
            String chord = soundingChord(original);
            if (chord != null && !chord.equals(previous)) {
                TGText text = beat.getText();
                text.setValue(chord);
                events.add(new ChordEvent(beat.getPreciseStart() - measureStart, chord, playedShape(original, chord)));
                previous = chord;
            } else if (beat.getText() != null) {
                beat.getText().setValue("");
            }
        }
        return events;
    }

    private static int removeDeadNotes(TGSong song) {
        int removed = 0;
        for (int trackIndex = 0; trackIndex < song.countTracks(); trackIndex++) {
            TGTrack track = song.getTrack(trackIndex);
            for (int measureIndex = 0; measureIndex < track.countMeasures(); measureIndex++) {
                TGMeasure measure = track.getMeasure(measureIndex);
                for (TGBeat beat : measure.getBeats()) {
                    for (int voiceIndex = 0; voiceIndex < 2; voiceIndex++) {
                        TGVoice voice = beat.getVoice(voiceIndex);
                        for (TGNote note : new ArrayList<>(voice.getNotes())) {
                            if (note.getEffect().isDeadNote()) {
                                voice.removeNote(note);
                                removed++;
                            }
                        }
                        if (voice.getNotes().isEmpty()) voice.setEmpty(true);
                    }
                }
            }
        }
        return removed;
    }

    private static void clean(TGSong song) {
        TGFactory factory = new TGFactory();
        removeDeadNotes(song);
        TGTrack rhythm = null, bass = null, click = null;
        for (int trackIndex = 0; trackIndex < song.countTracks(); trackIndex++) {
            TGTrack track = song.getTrack(trackIndex);
            String name = track.getName().toLowerCase();
            if (name.contains("rhythm") || name.contains("backing")) rhythm = track;
            else if (name.contains("bass")) bass = track;
            else if (name.contains("click") || name.contains("count-in")) click = track;
        }
        List<List<ChordEvent>> chordMap = new ArrayList<>();
        for (int measureIndex = 0; measureIndex < song.countMeasureHeaders(); measureIndex++) {
            chordMap.add(rhythm != null ? cleanRhythmMeasure(rhythm.getMeasure(measureIndex)) : new ArrayList<>());
        }
        for (int trackIndex = 0; trackIndex < song.countTracks(); trackIndex++) {
            TGTrack track = song.getTrack(trackIndex);
            String name = track.getName().toLowerCase();
            if (track == rhythm) continue;
            for (int measureIndex = 0; measureIndex < track.countMeasures(); measureIndex++) {
                TGMeasure measure = track.getMeasure(measureIndex);
                for (TGBeat beat : measure.getBeats()) {
                    if (beat.getText() == null) continue;
                    String original = beat.getText().getValue();
                    String concise = name.contains("application") || name.contains("review") ? conciseReviewText(original)
                        : (name.contains("click") && original.toUpperCase().contains("COUNT-IN") ? "COUNT-IN" : null);
                    if (concise == null) beat.getText().setValue(""); else beat.getText().setValue(concise);
                }
            }
        }
        for (int i = 0; i < song.countMeasureHeaders(); i++) {
            TGMeasure rhythmMeasure = rhythm != null ? rhythm.getMeasure(i) : null;
            long start = TGDuration.toPreciseTime(song.getMeasureHeader(i).getStart());
            if (click != null && rhythmMeasure != null && hasNotes(rhythmMeasure) && !hasNotes(click.getMeasure(i))) {
                long quarter = TGDuration.WHOLE_PRECISE_DURATION / 4;
                long measureLength = song.getMeasureHeader(i).getPreciseLength();
                for (long offset = 0; offset < measureLength; offset += quarter) {
                    addBeat(factory, click.getMeasure(i), start + offset, TGDuration.QUARTER, 1, 12, null);
                }
            }
            if (bass != null && rhythmMeasure != null && hasNotes(rhythmMeasure) && !hasNotes(bass.getMeasure(i))) {
                List<ChordEvent> events = chordMap.get(i);
                for (int eventIndex = 0; eventIndex < events.size(); eventIndex++) {
                    ChordEvent event = events.get(eventIndex);
                    long nextOffset = eventIndex + 1 < events.size() ? events.get(eventIndex + 1).offset()
                        : song.getMeasureHeader(i).getPreciseLength();
                    int duration = nextOffset - event.offset() <= TGDuration.WHOLE_PRECISE_DURATION / 2 ? TGDuration.HALF : TGDuration.WHOLE;
                    addBeat(factory, bass.getMeasure(i), start + event.offset(), duration, 4, bassFret(event.playedShape()), null);
                }
            }
        }
    }

    private static void report(String label, TGSong song) {
        System.out.println(label + " measures=" + song.countMeasureHeaders());
        for (int trackIndex = 0; trackIndex < song.countTracks(); trackIndex++) {
            TGTrack track = song.getTrack(trackIndex);
            int notes = 0, dead = 0, texts = 0, lastSounding = 0;
            long fingerprint = 1125899906842597L;
            for (int measureIndex = 0; measureIndex < track.countMeasures(); measureIndex++) {
                TGMeasure measure = track.getMeasure(measureIndex);
                boolean sounding = false;
                for (TGBeat beat : measure.getBeats()) {
                    if (beat.getText() != null && !beat.getText().getValue().trim().isEmpty()) texts++;
                    for (int voiceIndex = 0; voiceIndex < 2; voiceIndex++) {
                        for (TGNote note : beat.getVoice(voiceIndex).getNotes()) {
                            notes++; sounding = true;
                            if (note.getEffect().isDeadNote()) dead++;
                            fingerprint = 31 * fingerprint + measureIndex;
                            fingerprint = 31 * fingerprint + beat.getPreciseStart();
                            fingerprint = 31 * fingerprint + voiceIndex;
                            fingerprint = 31 * fingerprint + note.getString();
                            fingerprint = 31 * fingerprint + note.getValue();
                        }
                    }
                }
                if (sounding) lastSounding = measureIndex + 1;
            }
            System.out.println("  track=" + track.getName() + " notes=" + notes + " dead=" + dead
                + " texts=" + texts + " last=" + lastSounding + " fingerprint=" + fingerprint);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("usage: input.tg output.tg");
        TGFactory factory = new TGFactory();
        TGSong song = read(Path.of(args[0]), factory);
        report("before", song);
        clean(song);
        report("after", song);
        write(Path.of(args[1]), song, factory);
        report("reopened", read(Path.of(args[1]), factory));
    }
}
