import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.file.Path;

import app.tuxguitar.io.base.TGSongReaderHandle;
import app.tuxguitar.io.base.TGSongWriterHandle;
import app.tuxguitar.io.tg.TGFileFormatDetectorImpl;
import app.tuxguitar.io.tg.TGSongReaderImpl;
import app.tuxguitar.io.tg.TGSongWriterImpl;
import app.tuxguitar.song.factory.TGFactory;
import app.tuxguitar.song.models.TGBeat;
import app.tuxguitar.song.models.TGMeasure;
import app.tuxguitar.song.models.TGSong;
import app.tuxguitar.song.models.TGTrack;

public class TuxGuitarNativeProbe {
    private record Summary(
        int tracks, int measures, int notes,
        String trackNames, String tunings, String fingerings,
        String durations, String headers, String channels
    ) {}

    private static TGSong read(Path path) throws Exception {
        try (var detectStream = new FileInputStream(path.toFile())) {
            if (new TGFileFormatDetectorImpl().getFileFormat(detectStream) == null) {
                throw new IllegalStateException("native format detector rejected file");
            }
        }
        var handle = new TGSongReaderHandle();
        handle.setFactory(new TGFactory());
        try (var input = new FileInputStream(path.toFile())) {
            handle.setInputStream(input);
            new TGSongReaderImpl().read(handle);
        }
        return handle.getSong();
    }

    private static Summary summarize(TGSong song) {
        int measures = 0;
        int notes = 0;
        var trackNames = new StringBuilder();
        var tunings = new StringBuilder();
        var fingerings = new StringBuilder();
        var durations = new StringBuilder();
        var headers = new StringBuilder();
        var channels = new StringBuilder();
        song.getMeasureHeaders().forEachRemaining(header -> headers
            .append(header.getTimeSignature().getNumerator()).append('/')
            .append(header.getTimeSignature().getDenominator().getValue()).append('@')
            .append(header.getTempo().getQuarterValue()).append(','));
        song.getChannels().forEachRemaining(channel -> channels
            .append(channel.getChannelId()).append(':')
            .append(channel.getBank()).append(':')
            .append(channel.getProgram()).append(','));
        for (int trackIndex = 0; trackIndex < song.countTracks(); trackIndex++) {
            TGTrack track = song.getTrack(trackIndex);
            trackNames.append(track.getName()).append('|');
            track.getStrings().forEach(
                string -> tunings.append(string.getNumber()).append(':')
                    .append(string.getValue()).append(',')
            );
            tunings.append('|');
            measures += track.countMeasures();
            for (int measureIndex = 0; measureIndex < track.countMeasures(); measureIndex++) {
                TGMeasure measure = track.getMeasure(measureIndex);
                for (TGBeat beat : measure.getBeats()) {
                    for (int voice = 0; voice < TGBeat.MAX_VOICES; voice++) {
                        notes += beat.getVoice(voice).getNotes().size();
                        var duration = beat.getVoice(voice).getDuration();
                        durations.append(duration.getValue()).append(':')
                            .append(duration.isDotted()).append(':')
                            .append(duration.isDoubleDotted()).append(':')
                            .append(duration.getDivision().getEnters()).append('/')
                            .append(duration.getDivision().getTimes()).append(',');
                        beat.getVoice(voice).getNotes().forEach(
                            note -> fingerings.append(note.getString()).append('/')
                                .append(note.getValue()).append(',')
                        );
                    }
                }
            }
        }
        return new Summary(
            song.countTracks(), measures, notes,
            trackNames.toString(), tunings.toString(), fingerings.toString(),
            durations.toString(), headers.toString(), channels.toString()
        );
    }

    private static void write(Path path, TGSong song) throws Exception {
        var handle = new TGSongWriterHandle();
        handle.setFactory(new TGFactory());
        handle.setSong(song);
        try (var output = new FileOutputStream(path.toFile())) {
            handle.setOutputStream(output);
            new TGSongWriterImpl().write(handle);
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 1 || args.length > 2) {
            throw new IllegalArgumentException("usage: input.tg [native-saved-copy.tg]");
        }
        Path input = Path.of(args[0]);
        Summary opened = summarize(read(input));
        System.out.printf(
            "native_parser_accepted=true tracks=%d measures=%d notes=%d fingerprint=%d%n",
            opened.tracks(), opened.measures(), opened.notes(), opened.hashCode()
        );
        if (args.length == 2) {
            Path saved = Path.of(args[1]);
            write(saved, read(input));
            Summary reopened = summarize(read(saved));
            boolean same = opened.equals(reopened);
            System.out.printf(
                "native_save=true reopen_verified=%s tracks=%d measures=%d notes=%d fingerprint=%d%n",
                same, reopened.tracks(), reopened.measures(), reopened.notes(),
                reopened.hashCode()
            );
            if (!same) {
                throw new IllegalStateException("native save/reopen changed structural counts");
            }
        }
    }
}
