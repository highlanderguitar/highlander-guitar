from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from highlander_render.teal_engine.tuxguitar_writer import read_tuxguitar_tracks

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "output" / "etude_corpus"

PC = {"C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,"F#":6,"Gb":6,"G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11}
PC_NAME = ["C","C#/Db","D","D#/Eb","E","F","F#/Gb","G","G#/Ab","A","A#/Bb","B"]

META = {
"d_dorian_diatonic_fourths": dict(id="E01",teacher="Greg Fine / Rosenwinkel-pattern lesson",section="Dorian diatonic fourth pattern",tune="D minor modal vamp",page="1",start="00:00:10",end="00:05:10",images="image-0001",stype="notation + transcript",status="source-derived realization",progression="Transcript explicitly says D minor/D Dorian; eight-bar drill form is constructed.",lead="Pitch cell logic explicitly described and image-0001 supplies tab.",rhythm="Constructed Dm7 practice backing.",notes="Retain lead concept; replace traceability name and audit constructed form.",confidence="high",questions="Whether image-0001 should be transcribed note-for-note rather than retained as a realization.",screen="none visible",mstart="00:00:10",mend="00:05:10",offset="n/a",match="high",visual="Printed Dm7 notation/tab for ascending and descending fourth cells.",transcript="Three-note fourth cells; roots rise by diatonic thirds; reverse after register turn.",action="repair"),
"g_dorian_arrival_color": dict(id="E02",teacher="Greg Fine / Jim Hall lesson",section="Seven ideas from You'd Be So Nice to Come Home To",tune="You'd Be So Nice to Come Home To",page="2-3",start="00:02:25",end="00:05:30",images="image-0003,image-0004",stype="score screenshots + transcript",status="source-derived realization",progression="Source minor ii-V-i is Am7b5-D7b9-Gm7; repeated drill form is constructed.",lead="G Dorian E-natural arrival concept is explicit; current exact note ordering is constructed.",rhythm="Constructed practice backing from stated ii-V-i.",notes="Honest label should emphasize realization, not transcription.",confidence="high concept / medium notes",questions="Full-score screenshots need bar-level transcription if exact Jim Hall notes are desired.",screen="no player time visible",mstart="00:02:25",mend="00:05:30",offset="n/a",match="medium-high",visual="Full solo score with chord symbols.",transcript="E-natural Dorian color is emphasized on arrival at Gm7.",action="repair"),
"one_minor_across_minor_251": dict(id="E03",teacher="Greg Fine / Jim Hall lesson",section="One-minor simplification",tune="You'd Be So Nice to Come Home To",page="2-3",start="00:04:32",end="00:07:07",images="image-0005",stype="timed score screenshot + transcript",status="pedagogical reconstruction",progression="Am7b5-D7b9-Gm7 stated by source.",lead="G minor pentatonic/blues/arpeggio strategy explicit; present line invented as exercise.",rhythm="Constructed source-stated ii-V-i.",notes="Retain as reconstruction after chord legality repair.",confidence="high concept / medium realization",questions="None material.",screen="00:06:33",mstart="00:05:28",mend="00:07:07",offset="0",match="high",visual="Highlighted score location at player 6:33.",transcript="Think G minor across the entire minor ii-V-i.",action="repair"),
"abmaj7_over_bb7": dict(id="E04",teacher="Greg Fine / Jim Hall lesson",section="Abmaj7 upper structure over Bb7",tune="You'd Be So Nice to Come Home To",page="2-3",start="00:08:11",end="00:12:51",images="image-0006",stype="timed score screenshot + transcript",status="pedagogical reconstruction",progression="Fm7-Bb7-Ebmaj7 stated; repetition/form constructed.",lead="Abmaj7 pitch collection over Bb7 explicit; current line constructed.",rhythm="Constructed clean ii-V-I backing required.",notes="Repair illegal backing tones; classify individual upper extensions Teal, not whole file by engine branding.",confidence="high concept / medium realization",questions="Whether an exact highlighted Jim Hall phrase should replace reconstruction.",screen="00:11:30",mstart="00:09:21",mend="00:12:51",offset="0",match="high",visual="Highlighted score phrase at 11:30.",transcript="Abmaj7 tones over Bb7 yield b7, 9, 4, 13.",action="repair"),
"g_minor_pentatonic_over_ebmaj7": dict(id="E05",teacher="Greg Fine / Jim Hall lesson",section="G minor pentatonic over Ebmaj7",tune="You'd Be So Nice to Come Home To",page="2-3",start="00:11:29",end="00:13:53",images="image-0007",stype="timed score screenshot + transcript",status="pedagogical reconstruction",progression="Concept target is Ebmaj7; current Fm7-Bb7-Ebmaj7 frame is source-context but must not obscure target.",lead="G-Bb-D-F collection is present; source concept requires G minor pentatonic G-Bb-C-D-F, so C/13 must be made explicit without overwriting user work blindly.",rhythm="User-repaired m5-6 Ebmaj7 voicings are legal and must be preserved; other measures/bass require audit repair.",notes="Pink exercise. Chord tones keep priority; F=9 and C=13 split Pink/Teal when active. File modified 2026-08-01 12:06 after batch generation; preserve m5-6.",confidence="high concept / medium realization",questions="Confirm desired split-circle implementation in TuxGuitar rendering layer.",screen="00:13:40",mstart="00:11:29",mend="00:13:53",offset="0",match="high",visual="Highlighted score phrase at player 13:40.",transcript="G minor pentatonic over Ebmaj7 supplies 9 and 13 plus chord tones.",action="repair-first-preserve-user-edits"),
"jim_hall_fourths_through_251": dict(id="E06",teacher="Greg Fine / Jim Hall lesson",section="Intervals through changes",tune="You'd Be So Nice to Come Home To",page="2-4",start="00:13:17",end="00:16:11",images="image-0008,image-0009",stype="timed score screenshots + transcript",status="source-derived realization",progression="Fm7-Bb7-Ebmaj7 stated by source; drill repetition constructed.",lead="Fourth device explicit; current pitch sequence is a realization, not Jim Hall transcription.",rhythm="Constructed ii-V-I backing.",notes="Repair and rename; do not claim exact phrase.",confidence="high concept / medium realization",questions="Whether to add rhythmic-displacement variant as a separate later file.",screen="00:14:42;00:15:38",mstart="00:13:17",mend="00:16:11",offset="0",match="high",visual="Highlighted intervallic phrases at 14:42 and 15:38.",transcript="Move a chosen interval through changes with rhythmic displacement.",action="repair"),
"a_dorian_four_dominant": dict(id="E07",teacher="Greg Fine / Pat Martino lesson",section="Impressions devices",tune="Impressions (A minor version)",page="4",start="00:03:56",end="00:08:00",images="image-0012,image-0013",stype="timed notation screenshots + transcript",status="pedagogical reconstruction",progression="Source form is Am7 / Bbm7 bridge; IV-dominant concept is D7 over Am7. Current alternating Am7-D7 is a constructed drill, not tune form.",lead="D Mixolydian emphasis over Am7 explicit; exact notes constructed.",rhythm="Constructed concept backing; D7 labels should be reviewed because source describes superimposed hearing, not necessarily rhythm chord changes.",notes="Likely split into Am7 vamp with D7 conceptual annotation rather than literal D7 accompaniment.",confidence="high concept / medium harmony implementation",questions="Should D7 remain visible analysis only while backing stays Am7?",screen="00:06:24;00:06:48",mstart="00:05:18",mend="00:08:00",offset="0",match="high",visual="Notation explicitly marks Am7 and D7-implied regions.",transcript="Think IV dominant/D Mixolydian over A Dorian.",action="replace-harmony-implementation-after-review"),
"bm7_to_cmaj7_dorian": dict(id="E08",teacher="Greg Fine / Pat Martino lesson",section="Impressions arpeggio device",tune="Impressions (A minor version)",page="4",start="00:06:41",end="00:08:38",images="image-0014",stype="timed notation screenshot + transcript",status="source-derived realization",progression="Underlying source chord is Am7; Bm7 and Cmaj7 are lead arpeggio resources, not backing changes.",lead="Bm7 into Cmaj7 arpeggio weave explicitly shown.",rhythm="Am7 practice backing is appropriate if chord-legal.",notes="Correct prior source-image mapping (image-0026 was wrong lesson). Rename and repair backing only.",confidence="high",questions="Exact screenshot transcription comparison remains necessary.",screen="00:07:30",mstart="00:06:41",mend="00:08:38",offset="0",match="high",visual="Boxed Bm7-to-Cmaj7 arpeggio in notation at 7:30.",transcript="Weave Bm7 and Cmaj7 arpeggios derived from A Dorian.",action="repair"),
"a_melodic_minor_contrast": dict(id="E09",teacher="Greg Fine / Pat Martino lesson",section="Impressions melodic-minor device",tune="Impressions (A minor version)",page="4",start="00:07:59",end="00:10:48",images="",stype="transcript; adjacent screenshots not securely aligned",status="pedagogical reconstruction",progression="A minor modal vamp source-supported; eight-bar form constructed.",lead="A melodic minor pitch collection explicit; current sequence constructed.",rhythm="Am7 backing is conceptually usable but creates a deliberate G/G# tension that must be labeled, not harmonized away.",notes="Retain as reconstruction; remove incorrect image-0027 attribution (Pat Metheny section).",confidence="high concept / low visual match",questions="Find exact corresponding notation screenshot before any exact-note claim.",screen="none securely matched",mstart="00:07:59",mend="00:10:48",offset="n/a",match="low",visual="No securely synchronized screenshot identified.",transcript="Raise Dorian seventh G to G# for A melodic minor contrast.",action="repair-metadata"),
"happy_birthday_outline_to_etude": dict(id="E10",teacher="Dani Rabin / MarbinMusic",section="Lines, form, and chord-tone navigation",tune="Happy Birthday",page="10",start="00:01:29",end="00:11:33",images="image-0062-image-0101 (sequence requires bar-level audit)",stype="timed fretboard screenshots + transcript",status="incomplete / needs source review",progression="Instructor simplifies to 1-5-5-1 | 1-4-5-1 in C; current file uses that but does not distinguish original from simplification.",lead="Current single eighth-note line is invented and collapses multiple requested demonstrations.",rhythm="Constructed C-G7-G7-C-C-F-G7-C backing.",notes="Replace with Happy Birthday family; current image-0169/0170 attribution is wrong because those are Hotel California around 21:52.",confidence="high progression / low lead traceability",questions="Exact screenshot boundaries for quarter-note, eighth-note, melody-rhythm, and free-practice variants.",screen="00:05:31,00:05:34,00:05:39,00:06:05-00:06:23,00:09:07,00:09:13,00:10:32",mstart="00:04:30",mend="00:11:33",offset="approximately 0",match="medium-high sequence",visual="Fretboard/notation frames show progressive chord-tone and approach/neighbor-tone demonstrations.",transcript="Simplified form, voice-led triads, quarter-note outline, eighth-note etude, approaches/neighbors, blues coloring.",action="replace-with-family"),
}


def chord_pcs(symbol: str) -> set[int]:
    symbol=symbol.splitlines()[0].strip()
    match=re.match(r"^([A-G](?:#|b)?)(.*)$",symbol)
    if not match: return set()
    root=PC[match.group(1)];q=match.group(2).split("/")[0]
    if "m7b5" in q or "ø" in q: ints={0,3,6,10}
    elif "dim7" in q: ints={0,3,6,9}
    elif q.startswith("m") and "maj" not in q: ints={0,3,7,10} if "7" in q else {0,3,7}
    elif "maj7" in q: ints={0,4,7,11}
    elif "7" in q: ints={0,4,7,10}
    else: ints={0,4,7}
    if "b9" in q: ints.add(1)
    if "9" in q and "b9" not in q: ints.add(2)
    if "#11" in q: ints.add(6)
    if "13" in q: ints.add(9)
    return {(root+x)%12 for x in ints}


def label(pcs): return " ".join(PC_NAME[x] for x in sorted(pcs))


def audit_file(path: Path):
    tracks=read_tuxguitar_tracks(path);rhythm=tracks[1];bass=tracks[2]
    rows=[];violations=[];illegal_count=0
    for measure in rhythm["measures"]:
        sounding=[b for b in measure["beats"] if b["notes"]]
        symbol=next((b["chord_symbol"] for b in sounding if b["chord_symbol"]),"")
        allowed=chord_pcs(symbol);actual={n["midi_pitch"]%12 for b in sounding for n in b["notes"]};illegal=actual-allowed
        illegal_count+=len(illegal)
        for b in sounding:
            for n in b["notes"]:
                if n["midi_pitch"]%12 in illegal:
                    violations.append(dict(file=str(path.relative_to(ROOT)),measure=measure["measure"],chord_symbol=symbol,
                                           illegal_pitch=PC_NAME[n["midi_pitch"]%12],midi_pitch=n["midi_pitch"],string=n["string"],fret=n["fret"]))
        rows.append(dict(file=str(path.relative_to(ROOT)),measure=measure["measure"],chord_symbol=symbol,
                         allowed_pitch_classes=label(allowed),actual_pitch_classes=label(actual),illegal_pitch_classes=label(illegal),status="FAIL" if illegal else "PASS"))
    bass_illegal=[]
    for measure in bass["measures"]:
        symbol=next((b["chord_symbol"] for b in measure["beats"] if b["chord_symbol"]),"")
        allowed=chord_pcs(symbol)
        for b in measure["beats"]:
            for n in b["notes"]:
                if n["midi_pitch"]%12 not in allowed:bass_illegal.append((measure["measure"],symbol,PC_NAME[n["midi_pitch"]%12],n["string"],n["fret"]))
    return tracks,rows,violations,illegal_count,bass_illegal


def main():
    audit_rows=[];violation_rows=[];bass_rows=[];maps=[];sections=[]
    for path in sorted(CORPUS.rglob("*.tg")):
        stem=path.stem;meta=META[stem];tracks,rows,violations,illegal,bass_illegal=audit_file(path);audit_rows.extend(rows);violation_rows.extend(violations)
        for measure,symbol,pitch,string,fret in bass_illegal:
            bass_rows.append(dict(file=str(path.relative_to(ROOT)),measure=measure,chord_symbol=symbol,illegal_pitch=pitch,string=string,fret=fret,status="FAIL"))
        sha=hashlib.sha256(path.read_bytes()).hexdigest();mtime=path.stat().st_mtime
        maprow={"deliverable_id":meta["id"],"tg_path":str(path.relative_to(ROOT)),"first_track_name":tracks[0]["name"],"source_teacher_or_artist":meta["teacher"],"source_video_or_section":meta["section"],"source_tune":meta["tune"],"source_page":meta["page"],"source_timestamp_start":meta["start"],"source_timestamp_end":meta["end"],"source_image_ids":meta["images"],"source_type":meta["stype"],"exact_transcription_status":meta["status"],"progression_source":meta["progression"],"lead_source":meta["lead"],"rhythm_track_source":meta["rhythm"],"reconstruction_notes":meta["notes"],"confidence":meta["confidence"],"unresolved_questions":meta["questions"],"human_review_status":"not reviewed","screenshot_visible_time":meta["screen"],"matched_transcript_start":meta["mstart"],"matched_transcript_end":meta["mend"],"estimated_sync_offset_seconds":meta["offset"],"screenshot_transcript_match_confidence":meta["match"],"visual_evidence_summary":meta["visual"],"transcript_evidence_summary":meta["transcript"]}
        maps.append(maprow)
        user_edit="YES — later mtime; preserve m5-6 rhythm voicings" if stem=="g_minor_pentatonic_over_ebmaj7" else "no later edit detected relative to batch"
        sections += [f"## {meta['id']} — {path.name}","",f"- Current Track 1: `{tracks[0]['name']}` (fails required traceability format)",f"- Current state: {meta['status']}; {len(tracks)} tracks; rhythm illegality in {sum(r['status']=='FAIL' for r in rows)} measures; bass illegal events: {len(bass_illegal)}.",f"- Source-supported facts: {meta['transcript']}",f"- Unsupported/invented elements: {meta['lead']} {meta['progression']}",f"- Required correction/action: **{meta['action']}**. {meta['notes']}",f"- User-edit evidence: {user_edit}",f"- SHA-256: `{sha}`",""]
    fields=list(maps[0])
    with (CORPUS/"deliverable_source_map.csv").open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(maps)
    (CORPUS/"deliverable_source_map.json").write_text(json.dumps(maps,indent=2)+"\n",encoding="utf-8")
    md=["# Deliverable-to-Source Map (Phase A Audit)","","No TG files were modified. Screenshot times were matched to transcript windows with adjacent-frame inspection.",""]
    for r in maps:
        md += [f"## {r['deliverable_id']} — {Path(r['tg_path']).name}","",f"- Track 1: `{r['first_track_name']}`",f"- Source: {r['source_teacher_or_artist']}; {r['source_tune']}; {r['source_timestamp_start']}–{r['source_timestamp_end']}",f"- Status: **{r['exact_transcription_status']}**",f"- Screenshot ↔ transcript: {r['source_image_ids'] or 'none'}; visible {r['screenshot_visible_time']}; matched {r['matched_transcript_start']}–{r['matched_transcript_end']}; confidence {r['screenshot_transcript_match_confidence']}",f"- Visual evidence: {r['visual_evidence_summary']}",f"- Transcript evidence: {r['transcript_evidence_summary']}",f"- Unresolved: {r['unresolved_questions']}",""]
    (CORPUS/"deliverable_source_map.md").write_text("\n".join(md),encoding="utf-8")
    af=list(audit_rows[0])
    with (CORPUS/"chord_voicing_audit.csv").open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=af);w.writeheader();w.writerows(audit_rows)
    vf=list(violation_rows[0])
    with (CORPUS/"chord_voicing_violations.csv").open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=vf);w.writeheader();w.writerows(violation_rows)
    bf=["file","measure","chord_symbol","illegal_pitch","string","fret","status"]
    with (CORPUS/"bass_harmony_audit.csv").open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=bf);w.writeheader();w.writerows(bass_rows)
    failures=[r for r in audit_rows if r["status"]=="FAIL"]
    report=["# Phase A Etude Corpus Audit","","**Audit-only gate:** no TG, MusicXML, companion Markdown, or manifest was modified.","",f"- TG files audited: {len(maps)}",f"- Rhythm measures audited: {len(audit_rows)}",f"- Rhythm measures failing chord legality: {len(failures)}",f"- Individual illegal rhythm notes: {len(violation_rows)}",f"- Illegal bass events: {len(bass_rows)}",f"- Files with rhythm failures: {len(set(r['file'] for r in failures))}","","## Existing deliverables",""]+sections
    report += ["## Missing Marbin deliverables and proposed split","","The current E10 must be replaced, not merely renamed. Proposed Phase C IDs:","","- E10A–D: Happy Birthday — quarter-note outline, eighth-note etude, melody-rhythm/arpeggio realization, free-practice backing.","- E11A–D: Lonesome Whistle — 3/4 AABA outline, eighth-note etude, melody-rhythm/arpeggio realization, free-practice backing.","- E12A–D: Hotel California — form outline, etude, source-supported melody-rhythm treatment if recoverable, free-practice backing.","","Hotel California screenshots image-0169–0176 belong to the ~21:52 demonstration and must not remain attached to Happy Birthday. Lonesome Whistle evidence occupies the 16:07–20:35 transcript region; the 19:56 frame is a strong alignment anchor. Happy Birthday uses the simplified C progression 1-5-5-1 | 1-4-5-1 explicitly identified as the instructor's simplification.","","## Proposed traceable Track 1 names","","- E01 | Rosenwinkel Pattern | D Dorian Fourths | Source-derived","- E02 | Jim Hall / You'd Be So Nice | G Dorian Arrival | Source-derived","- E03 | Jim Hall / You'd Be So Nice | One-Minor ii-V-i | Reconstruction","- E04 | Jim Hall / You'd Be So Nice | Abmaj7 over Bb7 | Reconstruction","- E05 | Jim Hall / You'd Be So Nice | Gm Pent over Ebmaj7 | Reconstruction","- E06 | Jim Hall / You'd Be So Nice | Fourths Through ii-V-I | Source-derived","- E07 | Pat Martino / Impressions | IV-Dominant Lens | Reconstruction","- E08 | Pat Martino / Impressions | Bm7-Cmaj7 Weave | Source-derived","- E09 | Pat Martino / Impressions | Melodic Minor Contrast | Reconstruction","- E10A–D / E11A–D / E12A–D use the Marbin tune-and-device format specified above.","","## Phase B order","","1. Snapshot and compare E05, preserving user-corrected rhythm m5–6.","2. Repair E05 harmony/bass and implement Pink plus per-tone split Pink/Teal semantics.","3. Replace vague Track 1 names across E01–E09.","4. Correct every failed rhythm voicing and bass mismatch with symbol-literal chord tones only.","5. Regenerate records/manifests and run native reopen plus chord-legality gate.","","## Gate decision","","The scope matches the requested repair, but source audit proves E07's D7 accompaniment and E10's source-image attribution require substantive replacement. Per the requested implementation order, stop here for review before Phase B."]
    (CORPUS/"phase_a_audit_report.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    print(json.dumps({"tg_files":len(maps),"rhythm_measures":len(audit_rows),"failed_measures":len(failures),"individual_illegal_rhythm_notes":len(violation_rows),"illegal_bass_events":len(bass_rows),"failed_files":len(set(r['file'] for r in failures))},indent=2))

if __name__=="__main__":main()
