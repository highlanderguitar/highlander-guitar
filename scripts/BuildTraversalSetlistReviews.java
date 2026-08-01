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
import app.tuxguitar.song.models.TGNote;
import app.tuxguitar.song.models.TGSong;
import app.tuxguitar.song.models.TGString;
import app.tuxguitar.song.models.TGText;
import app.tuxguitar.song.models.TGTrack;
import app.tuxguitar.song.models.TGVoice;

public class BuildTraversalSetlistReviews {
    private record Review(String folder, String file, int tuneMeasure, int sourceMeasure,
                          int transpose, int targetMidi, String label) {}

    private static final Review[] REVIEWS = {
        new Review("walls_of_time", "walls-of-time", 14, 10, 2, 67, "TRAVERSAL VIA 5"),
        new Review("i_feel_the_blues_movin_in", "i-feel-the-blues-movin-in", 10, 1, 7, 67, "TRAVERSAL UP 3"),
        new Review("dig_a_hole_in_the_meadow", "dig-a-hole-in-the-meadow", 3, 1, 0, 60, "TRAVERSAL UP 3"),
        new Review("sarafina", "sarafina", 14, 10, 9, 62, "TRAVERSAL VIA 5"),
        new Review("perfume_powder_and_lead", "perfume-powder-and-lead", 2, 1, 7, 67, "TRAVERSAL UP 3"),
        new Review("rank_strangers", "rank-strangers", 42, 12, 7, 60, "TRAVERSAL DOMINANT"),
        new Review("dear_old_dixie", "dear-old-dixie", 20, 12, 7, 60, "TRAVERSAL DOMINANT"),
        new Review("somehow_tonight", "somehow-tonight", 8, 10, 2, 67, "FROM 3 > TRAVERSAL"),
        new Review("cant_you_hear_me_calling", "cant-you-hear-me-calling", 14, 10, 2, 67, "FROM 3 > TRAVERSAL"),
        new Review("farewell_blues", "farewell-blues", 5, 12, 9, 62, "TRAVERSAL DOMINANT"),
        new Review("trail_of_tears", "trail-of-tears", 13, 12, 11, 64, "TRAVERSAL > MINOR TARGET"),
        new Review("bright_sunny_south", "bright-sunny-south", 6, 1, 2, 62, "TRAVERSAL SUS REVIEW"),
        new Review("sitting_on_top_of_the_world", "sitting-on-top-of-the-world", 7, 10, 2, 67, "TRAVERSAL VIA 5"),
        new Review("southern_flavor", "southern-flavor", 7, 12, 11, 64, "TRAVERSAL > MINOR TARGET")
    };

    private static TGSong read(Path path, TGFactory factory) throws Exception {
        var handle = new TGSongReaderHandle(); handle.setFactory(factory);
        try (var input = new FileInputStream(path.toFile())) {
            handle.setInputStream(input); new TGSongReaderImpl().read(handle);
        }
        return handle.getSong();
    }

    private static void write(Path path, TGSong song, TGFactory factory) throws Exception {
        var handle = new TGSongWriterHandle(); handle.setFactory(factory); handle.setSong(song);
        try (var output = new FileOutputStream(path.toFile())) {
            handle.setOutputStream(output); new TGSongWriterImpl().write(handle);
        }
    }

    private static List<TGString> strings(TGFactory factory) {
        int[] tuning={64,59,55,50,45,40}; List<TGString> strings=new ArrayList<>();
        for(int i=0;i<tuning.length;i++){ TGString s=factory.newString(); s.setNumber(i+1); s.setValue(tuning[i]); strings.add(s); }
        return strings;
    }

    private static TGTrack reviewTrack(TGFactory factory, TGSong song) {
        TGChannel channel=factory.newChannel(); channel.setChannelId(71); channel.setProgram((short)25);
        channel.setVolume((short)105); channel.setBalance((short)64); channel.setName("BH Traversal Review"); song.addChannel(channel);
        TGTrack track=factory.newTrack(); track.setNumber(song.countTracks()+1); track.setSong(song);
        track.setName("BH Traversal Review"); track.setChannelId(71); track.setMaxFret(17); track.setStrings(strings(factory));
        for(int i=0;i<song.countMeasureHeaders();i++) track.addMeasure(factory.newMeasure(song.getMeasureHeader(i)));
        song.addTrack(track); return track;
    }

    private static int[] realize(int midi, int previousString, int previousFret) {
        int[] tuning={64,59,55,50,45,40}; int[] best=null; int scoreBest=Integer.MAX_VALUE;
        for(int octave=-2;octave<=2;octave++) for(int string=1;string<=6;string++) {
            int fret=midi+12*octave-tuning[string-1]; int limit=string==1?17:15;
            if(fret<0||fret>limit) continue;
            int score=Math.abs(fret-previousFret)+2*Math.abs(string-previousString)+8*Math.abs(octave)+(string==1?3:0);
            if(score<scoreBest){scoreBest=score;best=new int[]{string,fret};}
        }
        if(best==null) throw new IllegalArgumentException("No acoustic-safe fingering for "+midi);
        return best;
    }

    private static void copyPhrase(TGFactory factory, TGMeasure source, TGMeasure target, int transpose, String label) {
        long sourceStart=TGDuration.toPreciseTime(source.getHeader().getStart());
        long targetStart=TGDuration.toPreciseTime(target.getHeader().getStart());
        int previousString=4,previousFret=5; boolean first=true; int[] tuning={64,59,55,50,45,40};
        for(TGBeat sourceBeat:source.getBeats()) {
            TGBeat beat=factory.newBeat(); beat.setPreciseStart(targetStart+sourceBeat.getPreciseStart()-sourceStart);
            if(first){TGText text=factory.newText();text.setValue(label);beat.setText(text);first=false;}
            TGVoice voice=beat.getVoice(0); voice.getDuration().copyFrom(sourceBeat.getVoice(0).getDuration());
            for(TGNote sourceNote:sourceBeat.getVoice(0).getNotes()) {
                int midi=tuning[sourceNote.getString()-1]+sourceNote.getValue()+transpose;
                int[] location=realize(midi,previousString,previousFret); previousString=location[0];previousFret=location[1];
                TGNote note=factory.newNote();note.setString(location[0]);note.setValue(location[1]);note.setVelocity(86);note.setVoice(voice);voice.addNote(note);
            }
            voice.setEmpty(voice.getNotes().isEmpty()); target.addBeat(beat);
        }
    }

    private static void target(TGFactory factory, TGMeasure measure, int midi) {
        TGBeat beat=factory.newBeat();beat.setPreciseStart(TGDuration.toPreciseTime(measure.getHeader().getStart()));
        TGText text=factory.newText();text.setValue("TARGET");beat.setText(text);
        TGVoice voice=beat.getVoice(0);voice.getDuration().setValue(TGDuration.WHOLE);
        int[] location=realize(midi,3,5);TGNote note=factory.newNote();note.setString(location[0]);note.setValue(location[1]);note.setVelocity(82);note.setVoice(voice);voice.addNote(note);voice.setEmpty(false);measure.addBeat(beat);
    }

    public static void main(String[] args) throws Exception {
        if(args.length!=2) throw new IllegalArgumentException("usage: repository-root traversal-source.tg");
        Path root=Path.of(args[0]); TGFactory factory=new TGFactory(); TGSong traversal=read(Path.of(args[1]),factory);
        for(Review review:REVIEWS){
            Path input=root.resolve("reviews/setlist").resolve(review.folder()).resolve("canonical").resolve(review.file()+".tg");
            TGSong song=read(input,factory); if(review.tuneMeasure()>song.countMeasureHeaders()) continue;
            TGTrack track=reviewTrack(factory,song); copyPhrase(factory,traversal.getTrack(0).getMeasure(review.sourceMeasure()-1),track.getMeasure(review.tuneMeasure()-1),review.transpose(),review.label());
            if(review.tuneMeasure()<song.countMeasureHeaders()) target(factory,track.getMeasure(review.tuneMeasure()),review.targetMidi());
            Path output=root.resolve("reviews/setlist").resolve(review.folder()).resolve("phrase_review").resolve(review.file()+"-Phrase-Review.tg");
            Files.createDirectories(output.getParent());write(output,song,factory);System.out.println(output);
        }
    }
}
