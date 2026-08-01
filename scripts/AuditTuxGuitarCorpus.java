import java.io.FileInputStream;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import app.tuxguitar.io.base.TGSongReaderHandle;
import app.tuxguitar.io.tg.TGSongReaderImpl;
import app.tuxguitar.song.factory.TGFactory;
import app.tuxguitar.song.models.TGBeat;
import app.tuxguitar.song.models.TGMeasure;
import app.tuxguitar.song.models.TGNote;
import app.tuxguitar.song.models.TGSong;
import app.tuxguitar.song.models.TGTrack;

public class AuditTuxGuitarCorpus {
    private static TGSong read(Path path) throws Exception {
        var handle = new TGSongReaderHandle();
        handle.setFactory(new TGFactory());
        try (var input = new FileInputStream(path.toFile())) {
            handle.setInputStream(input);
            new TGSongReaderImpl().read(handle);
        }
        return handle.getSong();
    }

    private static String safe(String value) {
        return value == null ? "" : value.replace("\r", " ").replace("\n", " ").trim();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("usage: source.tg");
        TGSong song = read(Path.of(args[0]));
        System.out.println("file=" + args[0] + " title=" + safe(song.getName())
            + " tracks=" + song.countTracks() + " headers=" + song.countMeasureHeaders());
        for (int trackIndex = 0; trackIndex < song.countTracks(); trackIndex++) {
            TGTrack track = song.getTrack(trackIndex);
            System.out.println("TRACK " + (trackIndex + 1) + " name=" + safe(track.getName())
                + " measures=" + track.countMeasures() + " strings=" + track.stringCount());
            for (int measureIndex = 0; measureIndex < track.countMeasures(); measureIndex++) {
                TGMeasure measure = track.getMeasure(measureIndex);
                List<String> texts = new ArrayList<>();
                List<String> notes = new ArrayList<>();
                for (TGBeat beat : measure.getBeats()) {
                    if (beat.getText() != null && !safe(beat.getText().getValue()).isEmpty()) {
                        texts.add(beat.getPreciseStart() + ":" + safe(beat.getText().getValue()));
                    }
                    for (int voiceIndex = 0; voiceIndex < 2; voiceIndex++) {
                        for (TGNote note : beat.getVoice(voiceIndex).getNotes()) {
                            notes.add(beat.getPreciseStart() + ":s" + note.getString() + "f" + note.getValue()
                                + (note.getEffect().isDeadNote() ? "X" : ""));
                        }
                    }
                }
                String marker = measure.getHeader().hasMarker() ? safe(measure.getHeader().getMarker().getTitle()) : "";
                System.out.println("  M" + (measureIndex + 1) + " meter="
                    + measure.getHeader().getTimeSignature().getNumerator() + "/"
                    + measure.getHeader().getTimeSignature().getDenominator().getValue()
                    + " marker=[" + marker + "] texts=" + texts + " notes=" + notes);
            }
        }
    }
}
