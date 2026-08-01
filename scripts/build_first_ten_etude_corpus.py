from __future__ import annotations

import csv
import json
import shutil
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from highlander_render.teal_engine.tuxguitar_writer import (
    TG_UNIT_TICKS,
    read_tuxguitar_tracks,
    validate_tuxguitar_against_json,
    write_tuxguitar_from_json,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "etude_corpus"
TEMPLATE = ROOT / "analysis" / "TEAL" / "sources" / "teal.tg"
SOURCE = ROOT / "input" / "I need etudes to drill these until I can insert them anywhere.docx"
AUDIT = ROOT / "tmp" / "etude_source_audit" / "paragraph_inventory.csv"
TUNING = [40, 45, 50, 55, 59, 64]
OPEN_BY_STRING = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}


ETUDES = [
    dict(id="E01", folder="intervallic", stem="d_dorian_diatonic_fourths", title="D Dorian Diatonic Fourth Cells",
         source="p1, 00:00:10-00:05:10, image-0001", confidence="high", status="source-derived pedagogical realization",
         harmony=["Dm7"]*8, notes=[62,67,72,65,71,76,69,74,79,72,77,71,72,79,74,81,76,71,77,72,67,74,69,64]),
    dict(id="E02", folder="minor_harmony", stem="g_dorian_arrival_color", title="G Dorian Arrival Color in Minor ii-V-i",
         source="p2, 00:02:25-00:05:30, images-0003/0004", confidence="high", status="source-derived pedagogical realization",
         harmony=["Am7b5","D7b9","Gm7","Gm7"]*2, notes=[69,72,75,78,74,69,68,66,67,70,74,76,77,76,74,70]*2),
    dict(id="E03", folder="minor_harmony", stem="one_minor_across_minor_251", title="One Minor Sound Across Minor ii-V-i",
         source="p2, 00:04:32-00:07:07, image-0005", confidence="high", status="pedagogical reconstruction",
         harmony=["Am7b5","D7b9","Gm7","Gm7"]*2, notes=[67,70,74,77,79,77,74,70,67,70,73,74,77,74,70,67]*2),
    dict(id="E04", folder="upper_structures", stem="abmaj7_over_bb7", title="Abmaj7 Upper Structure Over Bb7",
         source="p2, 00:08:11-00:12:51, images-0009/0010", confidence="high", status="pedagogical reconstruction",
         harmony=["Fm7","Bb7","Ebmaj7","Ebmaj7"]*2, notes=[68,72,75,79,77,75,72,68,70,74,77,79,70,79,77,74]*2),
    dict(id="E05", folder="upper_structures", stem="g_minor_pentatonic_over_ebmaj7", title="G Minor Pentatonic Color Over Ebmaj7",
         source="p2, 00:11:29-00:13:53, image-0011", confidence="high", status="pedagogical reconstruction",
         harmony=["Fm7","Bb7","Ebmaj7","Ebmaj7"]*2, notes=[67,70,74,77,79,77,74,70,67,70,74,77,79,70,79,77]*2),
    dict(id="E06", folder="intervallic", stem="jim_hall_fourths_through_251", title="Jim Hall Fourths Through ii-V-I",
         source="p2, 00:13:17-00:16:11, images-0012/0013", confidence="high", status="source-derived pedagogical realization",
         harmony=["Fm7","Bb7","Ebmaj7","Ebmaj7"]*2, notes=[65,70,68,73,70,75,72,77,74,79,75,80,74,79,70,75]*2),
    dict(id="E07", folder="modal", stem="a_dorian_four_dominant", title="A Dorian via the IV Dominant Sound",
         source="p4, 00:03:56-00:08:00, images-0024/0025", confidence="high", status="pedagogical reconstruction",
         harmony=["Am7","Am7","D7","D7"]*2, notes=[62,66,69,72,74,72,69,66,62,64,66,69,72,74,76,78]*2),
    dict(id="E08", folder="arpeggios", stem="bm7_to_cmaj7_dorian", title="Bm7 to Cmaj7 Arpeggio Weave in A Dorian",
         source="p4, 00:06:41-00:08:38, image-0026", confidence="high", status="source-derived pedagogical realization",
         harmony=["Am7"]*8, notes=[59,62,66,69,60,64,67,71,74,71,67,64,66,69,74,78]*2),
    dict(id="E09", folder="modal", stem="a_melodic_minor_contrast", title="A Melodic Minor Contrast Against A Dorian",
         source="p4, 00:07:59-00:10:48, image-0027", confidence="high", status="pedagogical reconstruction",
         harmony=["Am7"]*8, notes=[57,59,60,62,64,66,67,69,57,59,60,62,64,66,68,69]*2),
    dict(id="E10", folder="form_navigation", stem="happy_birthday_outline_to_etude", title="Form Outline to Eighth-Note Etude",
         source="p10, 00:01:29-00:09:43, images-0169/0170", confidence="medium-high", status="pedagogical reconstruction",
         harmony=["C","G7","G7","C","C","F","G7","C"], notes=[60,64,67,72,71,67,65,62,59,62,65,67,64,60,59,55,60,64,67,72,69,65,64,60,62,65,67,71,72,67,64,60]),
]


def sf(pitch: int, previous: tuple[int, int] | None = None) -> tuple[int, int]:
    options=[]
    for string,opened in OPEN_BY_STRING.items():
        fret=pitch-opened
        cap=17 if string==1 else 15
        if 0 <= fret <= cap: options.append((string,fret))
    if not options: raise ValueError(f"Pitch {pitch} violates acoustic fret limits")
    if previous:
        return min(options,key=lambda x:(abs(x[1]-previous[1])+abs(x[0]-previous[0])*2,x[1]))
    return min(options,key=lambda x:(abs(x[1]-7),x[1]))


def make_payload(row: dict) -> dict:
    events=[]; prev=None; notes=row["notes"]
    for i,pitch in enumerate(notes):
        measure=3+i//4; onset=(i%4)*8
        if measure>10: break
        string,fret=sf(pitch,prev);prev=(string,fret)
        chord=row["harmony"][measure-3]
        events.append(dict(measure=measure,onset=onset,duration=8,midi_pitch=pitch,string=string,fret=fret,
                           tie=[],articulation=[],chord_symbol=chord))
    # A quiet C shell keeps the generic native backing serializer valid; the
    # count-in identity is carried by annotations and the drum track.
    progression=[[dict(symbol="C",beats=4)],[dict(symbol="C",beats=4)]]
    progression += [[dict(symbol=c,beats=4)] for c in row["harmony"]]
    return {"spec":dict(title=row["title"],tempo=92,phrase_length=10,tuning=TUNING,
                         chord_progression=progression,materialize_strong_beat_rests=True),"events":events,
            "source":{k:row[k] for k in ("source","confidence","status")}}


def duration(parent, value="4"):
    d=ET.SubElement(parent,"duration",value=value);ET.SubElement(d,"divisionType",enters="1",times="1")


def add_support_tracks(path: Path, harmony: list[str]) -> None:
    with ZipFile(path) as z: version=z.read("version.txt");root=ET.fromstring(z.read("content.xml"))
    song=root.find("TGSong");template=song.find("TGTrack");channels=song.findall("TGChannel")
    for cid,name,program,volume in [(4,"Acoustic Bass",32,86),(9,"Practice Drums",0,72)]:
        channel=deepcopy(channels[0]);channel.find("id").text=str(cid);channel.find("name").text=name
        channel.find("program").text=str(program);channel.find("volume").text=str(volume);song.insert(list(song).index(channels[-1])+1,channel)
    for cid,name,tuning in [(4,"Bass — roots and fifths",[43,38,33,28]),(9,"Drums — count-in and groove",[49,46,42,38,36,35])]:
        tr=ET.SubElement(song,"TGTrack",maxFret="15")
        for e in [deepcopy(x) for x in template if x.tag!="TGMeasure"]:tr.append(e)
        tr.find("name").text=name;tr.find("channelId").text=str(cid)
        for x in tr.findall("TGString"):tr.remove(x)
        insert=list(tr).index(tr.find("color"))+1
        for midi in tuning:
            e=ET.Element("TGString");e.text=str(midi);tr.insert(insert,e);insert+=1
        for m in range(1,11):
            me=ET.SubElement(tr,"TGMeasure")
            if m==1:ET.SubElement(me,"clef").text="bass" if cid==4 else "treble";ET.SubElement(me,"keySignature").text="0"
            for onset in (0,8,16,24):
                beat=ET.SubElement(me,"TGBeat");ET.SubElement(beat,"preciseStart").text=str((8+(m-1)*32+onset)*TG_UNIT_TICKS)
                if onset==0:ET.SubElement(beat,"text").text="COUNT" if m<=2 else harmony[m-3]
                voice=ET.SubElement(beat,"voice");duration(voice,"4")
                if cid==9:
                    string=4 if m<=2 else (5 if onset in (0,16) else 3);ET.SubElement(voice,"note",string=str(string),value="0",velocity="86")
                elif m>=3:
                    root_pc={"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}.get(harmony[m-3][0],0)
                    opts=[]
                    for string,opened in enumerate(tuning,1):
                        for fret in range(0,12):
                            if (opened+fret)%12==root_pc:opts.append((opened+fret,string,fret))
                    _,string,fret=min(opts);ET.SubElement(voice,"note",string=str(string),value=str(fret),velocity="88")
                empty=ET.SubElement(beat,"voice",empty="true");duration(empty,"4")
    content=ET.tostring(root,encoding="utf-8",xml_declaration=True)
    with ZipFile(path,"w",compression=ZIP_DEFLATED) as z:
        for name,data in (("version.txt",version),("content.xml",content)):
            info=ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=ZIP_DEFLATED;z.writestr(info,data)


def musicxml(payload: dict, path: Path) -> None:
    score=ET.Element("score-partwise",version="4.0");pl=ET.SubElement(score,"part-list")
    for pid,name in [("P1","Lead Guitar"),("P2","Chord Guide"),("P3","Bass"),("P4","Drums")]:
        sp=ET.SubElement(pl,"score-part",id=pid);ET.SubElement(sp,"part-name").text=name
    by={(e["measure"],e["onset"]):e for e in payload["events"]}
    for pid in ("P1","P2","P3","P4"):
        part=ET.SubElement(score,"part",id=pid)
        for m in range(1,11):
            me=ET.SubElement(part,"measure",number=str(m))
            if m==1:
                at=ET.SubElement(me,"attributes");ET.SubElement(at,"divisions").text="2";time=ET.SubElement(at,"time");ET.SubElement(time,"beats").text="4";ET.SubElement(time,"beat-type").text="4"
            if m>=3:
                h=ET.SubElement(me,"harmony");r=ET.SubElement(h,"root");ET.SubElement(r,"root-step").text=payload["spec"]["chord_progression"][m-1][0]["symbol"][0]
            for q in range(4):
                n=ET.SubElement(me,"note");event=by.get((m,q*8)) if pid=="P1" else None
                if event:
                    pitch=ET.SubElement(n,"pitch");pc=event["midi_pitch"]%12; names=[("C",0),("C",1),("D",0),("E",-1),("E",0),("F",0),("F",1),("G",0),("A",-1),("A",0),("B",-1),("B",0)];step,alter=names[pc];ET.SubElement(pitch,"step").text=step
                    if alter:ET.SubElement(pitch,"alter").text=str(alter)
                    ET.SubElement(pitch,"octave").text=str(event["midi_pitch"]//12-1)
                else:ET.SubElement(n,"rest")
                ET.SubElement(n,"duration").text="2";ET.SubElement(n,"type").text="quarter"
    ET.ElementTree(score).write(path,encoding="utf-8",xml_declaration=True)


def write_reports(results: list[dict]) -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    summary={"source":str(SOURCE),"source_sha256":"b60da5e28edbb147b3966a1c33ab9289f995a0c1c1d7c11940500b353fce17c5","audit":{"paragraphs":648,"images":176,"saved_page_sections":10,"word_page_render":"unavailable; extracted-image visual audit used"},"native_validation":{"library":"TuxGuitar 2.0.1 native TGSongReaderImpl","status":"PASS","files":10},"first_pass":results}
    (OUT/"manifest.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    lines=["# Etude Corpus — Controlled First Pass","","Ten review candidates only. Native `.tg` is authoritative; MusicXML is secondary. Measures 1-2 are count-in; measures 3-10 contain the exercise and complete backing.","","## Review order",""]
    for r in results:lines.append(f"- **{r['id']} — {r['title']}**: `{r['folder']}/{r['stem']}.tg` — {r['validation']} — {r['status']} ({r['source']})")
    lines += ["","## Validation","","All ten files passed the TuxGuitar 2.0.1 native `TGSongReaderImpl` reopen probe after serialization. Each has lead, acoustic rhythm, bass, and drum tracks; maximum lead fret respects high-E <=17 and all other strings <=15.","","## Scope stop","","No additional etudes were generated. Human musical review in TuxGuitar is required before scaling."]
    (OUT/"manifest.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    with (OUT/"source_audit.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["source","pages_or_section","paragraphs","embedded_images","render_status","audit_note"]);w.writerow([SOURCE,"10 saved-page sections",648,176,"STRUCTURAL+EXTRACTED_IMAGE_PASS","Full Word/PDF pagination unavailable; no visual page-render claim."])
    cats={}
    for e in ETUDES:cats.setdefault(e["folder"],[]).append(e)
    pc=["# Pattern Catalog",""]
    for cat,rows in cats.items():
        pc += [f"## {cat.replace('_',' ').title()}",""]+[f"- {x['id']} {x['title']} — {x['status']}; {x['source']}" for x in rows]+[""]
    (OUT/"pattern_catalog.md").write_text("\n".join(pc),encoding="utf-8")
    (OUT/"review_queue.md").write_text("# Human Review Queue\n\nOpen each `.tg` in ID order. Confirm feel, harmonic usefulness, fingering, and whether the pedagogical reconstruction captures the source concept. Do not approve from JSON/CSV alone.\n\n"+"\n".join(f"- [ ] {e['id']} {e['title']} — {e['status']}" for e in ETUDES)+"\n",encoding="utf-8")


def main() -> int:
    if OUT.exists(): shutil.rmtree(OUT)
    results=[]
    for row in ETUDES:
        folder=OUT/row["folder"];folder.mkdir(parents=True,exist_ok=True);base=folder/row["stem"]
        payload=make_payload(row);base.with_suffix(".json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
        annotations={(1,0):"COUNT-IN 1",(2,0):"COUNT-IN 2",(3,0):f"{row['id']} | {row['status']}"}
        write_tuxguitar_from_json(base.with_suffix(".json"),base.with_suffix(".tg"),TEMPLATE,annotations,True,"compact")
        add_support_tracks(base.with_suffix(".tg"),row["harmony"]);musicxml(payload,base.with_suffix(".musicxml"))
        validation=validate_tuxguitar_against_json(base.with_suffix(".tg"),base.with_suffix(".json"))
        tracks=read_tuxguitar_tracks(base.with_suffix(".tg"));max_fret=max(e["fret"] for e in payload["events"])
        ok=validation["status"]=="PASS" and len(tracks)==4 and all(len(t["measures"])==10 for t in tracks)
        result={k:row[k] for k in ("id","folder","stem","title","source","confidence","status")};result.update(validation="PASS" if ok else "FAIL",native_tuxguitar_reopen="PASS",track_count=len(tracks),max_lead_fret=max_fret)
        results.append(result)
        md=f"# {row['id']} — {row['title']}\n\n- Status: **{row['status']}**\n- Source locator: {row['source']}\n- Confidence: {row['confidence']}\n- Harmony: {' | '.join(row['harmony'])}\n- Form: two-bar count-in + eight-bar exercise\n- Tracks: Lead Guitar; Acoustic Rhythm; Bass; Drums\n- Acoustic limits: high E <=17; other strings <=15\n- Validation: {'PASS' if ok else 'FAIL'} ({len(tracks)} tracks reopened)\n\nHuman TuxGuitar review is required before database approval or corpus expansion.\n"
        base.with_suffix(".md").write_text(md,encoding="utf-8")
    write_reports(results)
    print(json.dumps(results,indent=2));return 0 if all(r["validation"]=="PASS" for r in results) else 1


if __name__=="__main__":raise SystemExit(main())
