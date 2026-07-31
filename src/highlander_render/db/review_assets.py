from __future__ import annotations

import csv
import json
import struct
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .core import DEFAULT_DB_PATH, REPO_ROOT, connect
from .licks import OPEN_MIDI, package_info

REVIEW_ROOT = REPO_ROOT / "reviews" / "bh_5432"
ANALYSIS = REPO_ROOT / "analysis"
EXPORTS = REPO_ROOT / "exports" / "database"


def _source_paths(db_path: Path):
    info = package_info(db_path)
    mx = next(f for f in info["files"] if f["extension"] == ".musicxml")
    tg = next(f for f in info["files"] if f["extension"] == ".tg")
    return Path(mx["resolved_absolute_path"]) / mx["relative_path"], Path(tg["resolved_absolute_path"]) / tg["relative_path"]


def _measure_inventory(mx_path: Path, tg_path: Path):
    root = ET.parse(mx_path).getroot()
    part_names = {p.get("id"): p.findtext("part-name") for p in root.findall("./part-list/score-part")}
    annotations = {}
    with zipfile.ZipFile(tg_path) as z:
        tgroot = ET.fromstring(z.read("content.xml"))
    for track_index, track in enumerate(tgroot.findall(".//TGTrack"), 1):
        for measure_index, measure in enumerate(track.findall("TGMeasure"), 1):
            texts = [t.text or "" for t in measure.findall(".//text") if (t.text or "").strip()]
            if texts: annotations[(track_index, measure_index)] = " | ".join(texts)
    rows = []
    for track_index, part in enumerate(root.findall("part"), 1):
        divisions = 1
        for measure in part.findall("measure"):
            number = int(measure.get("number"))
            attrs = measure.find("attributes")
            if attrs is not None: divisions = int(attrs.findtext("divisions", str(divisions)))
            notes = measure.findall("note")
            chosen_staff = "2" if any(n.findtext("staff") == "2" for n in notes) else "1"
            selected = [n for n in notes if n.findtext("staff", "1") == chosen_staff]
            sounding, rests, pitches, frets, durations = [], 0, [], [], []
            for n in selected:
                d = int(n.findtext("duration", "0")) / divisions
                durations.append(d)
                if n.find("rest") is not None: rests += 1; continue
                p=n.find("pitch"); step=p.findtext("step"); alter=int(p.findtext("alter","0")); octave=int(p.findtext("octave"))
                pitches.append(f"{step}{'#' if alter==1 else 'b' if alter==-1 else ''}{octave}")
                tech=n.find("./notations/technical")
                frets.append(f"{tech.findtext('string')}/{tech.findtext('fret')}" if tech is not None else "")
                sounding.append(n)
            imported = track_index == 1 and number in (1,2,3)
            rows.append({"track":part_names.get(part.get("id"),part.get("id")),"track_index":track_index,"measure":number,
                         "source_start_event":1 if selected else 0,"source_end_event":len(selected),"sounding_note_count":len(sounding),
                         "rest_count":rests,"duration_quarters":sum(durations),"pitch_sequence":" ".join(pitches),
                         "string_fret_sequence":" ".join(frets),"annotation":annotations.get((track_index,number),""),
                         "imported":imported,"family":{1:"bh-5432-five",2:"bh-5432-four",3:"bh-5432-three"}.get(number,"") if imported else "",
                         "reason":"initial proof extraction" if imported else "accounted; not extracted pending boundary/pattern review",
                         "duplicated":"possible staff representation only","instructional_scaffolding":bool(annotations.get((track_index,number))),
                         "accompaniment":"unknown","needs_review":not imported})
    return rows


def _version_data(db, slug):
    notes=[dict(r) for r in db.execute("SELECT * FROM lick_version_notes WHERE version_id=(SELECT id FROM lick_versions WHERE slug=?) ORDER BY event_index",(slug,))]
    fingerings={}
    for f in db.execute("SELECT * FROM lick_fingerings WHERE version_id=(SELECT id FROM lick_versions WHERE slug=?)",(slug,)):
        fingerings[f["source_or_generated"]]=[dict(r) for r in db.execute("SELECT fn.string_number,fn.fret,n.sounding_midi,n.written_pitch,n.duration FROM lick_fingering_notes fn JOIN lick_version_notes n ON n.id=fn.note_id WHERE fn.fingering_id=? ORDER BY n.event_index",(f["id"],))]
    return notes,fingerings


def _tg_xml(tracks, tempo=60):
    headers="".join(f'<TGMeasureHeader><timeSignature denominator="4" numerator="4"/><tempo>{tempo}</tempo></TGMeasureHeader>' for _ in range(4))
    channels="".join(f"<TGChannel><id>{i}</id><bank>0</bank><program>25</program><volume>127</volume><balance>64</balance><chorus>0</chorus><reverb>0</reverb><phaser>0</phaser><tremolo>0</tremolo><name>Guitar</name></TGChannel>" for i in range(1,len(tracks)+1))
    track_xml=[]
    for idx,(name,events,text) in enumerate(tracks,1):
        beats=[]
        tick=2882880
        for i,e in enumerate(events):
            duration=max(float(e.get("duration",0.5)),0.125)
            denom=round(4/duration)
            label=f"<text>{escape(text)}</text>" if i==0 and text else ""
            beats.append(f'<TGBeat><preciseStart>{tick}</preciseStart>{label}<voice><duration value="{denom}"><divisionType enters="1" times="1"/></duration><note string="{e["string_number"]}" value="{e["fret"]}" velocity="95"/></voice><voice empty="true"><duration value="4"><divisionType enters="1" times="1"/></duration></voice></TGBeat>')
            tick += int(duration*2882880)
        measures=f"<TGMeasure><clef>treble</clef><keySignature>0</keySignature>{''.join(beats)}</TGMeasure>"+("<TGMeasure><TGBeat><preciseStart>14414400</preciseStart><voice empty=\"false\"><duration value=\"1\"><divisionType enters=\"1\" times=\"1\"/></duration></voice></TGBeat></TGMeasure>"*3)
        track_xml.append(f'<TGTrack maxFret="29"><name>{escape(name)}</name><channelId>{idx}</channelId><color B="0" G="0" R="0"/><TGString>64</TGString><TGString>59</TGString><TGString>55</TGString><TGString>50</TGString><TGString>45</TGString><TGString>40</TGString><TGLyric from="1"/>{measures}</TGTrack>')
    return f'<?xml version="1.0" encoding="UTF-8" standalone="no"?><TuxGuitarFile><TGVersion major="2" minor="0" revision="1"/><TGSong><name>BH-5432 Review</name>{channels}{headers}{"".join(track_xml)}</TGSong></TuxGuitarFile>'


def _write_tg(path, tracks, tempo=60):
    path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("version.txt","TuxGuitar file format 2.0")
        z.writestr("content.xml",_tg_xml(tracks,tempo))


def _write_musicxml(path,title,events):
    divisions=480
    notes=[]
    for e in events:
        midi=e["sounding_midi"]; octave=midi//12-1; pc=midi%12
        names=[("C",0),("C",1),("D",0),("D",1),("E",0),("F",0),("F",1),("G",0),("G",1),("A",0),("A",1),("B",0)]
        step,alter=names[pc]
        notes.append(f"<note><pitch><step>{step}</step>{f'<alter>{alter}</alter>' if alter else ''}<octave>{octave}</octave></pitch><duration>{int(float(e['duration'])*divisions)}</duration><voice>1</voice><type>eighth</type><staff>1</staff><notations><technical><string>{e['string_number']}</string><fret>{e['fret']}</fret></technical></notations></note>")
    xml=f'''<?xml version="1.0" encoding="UTF-8"?><score-partwise version="4.0"><work><work-title>{escape(title)}</work-title></work><part-list><score-part id="P1"><part-name>Guitar</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>{divisions}</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes><direction><sound tempo="60"/></direction>{''.join(notes)}</measure></part></score-partwise>'''
    path.write_text(xml,encoding="utf-8")


def _vlq(n):
    b=[n&127]; n>>=7
    while n: b.append((n&127)|128); n>>=7
    return bytes(reversed(b))


def _write_midi(path,events,tempo):
    division=480; data=bytearray(b"\x00\xff\x51\x03"+int(60000000/tempo).to_bytes(3,"big"))
    for e in events:
        data+=_vlq(0)+bytes([0x90,e["sounding_midi"],90])
        data+=_vlq(int(float(e["duration"])*division))+bytes([0x80,e["sounding_midi"],0])
    data+=b"\x00\xff\x2f\x00"
    path.write_bytes(b"MThd"+struct.pack(">IHHH",6,0,1,division)+b"MTrk"+struct.pack(">I",len(data))+data)


def _write_pdf(path,title,notes,source,generated):
    c=canvas.Canvas(str(path),pagesize=letter); y=750
    c.setFont("Helvetica-Bold",16); c.drawString(54,y,title); y-=28
    c.setFont("Helvetica",9)
    lines=["Source measure and event boundaries are listed below.",
           "Notes: "+" ".join(n["written_pitch"] for n in notes),
           "Durations: "+" ".join(str(n["duration"]) for n in notes),
           "Source TAB: "+" ".join(f'{e["string_number"]}/{e["fret"]}' for e in source),
           "Generated TAB: "+" ".join(f'{e["string_number"]}/{e["fret"]}' for e in generated),
           "Status: source fingering accepted technically; generated fingering needs_review.",
           "Approval: [ ] accept family [ ] revise boundary [ ] reject",
           "Generated fingering: [ ] accept [ ] revise [ ] reject"]
    for line in lines:
        for chunk in [line[i:i+105] for i in range(0,len(line),105)]: c.drawString(54,y,chunk); y-=14
        y-=4
    c.save()


def generate_review_assets(database=DEFAULT_DB_PATH):
    mx,tg=_source_paths(database); rows=_measure_inventory(mx,tg)
    ANALYSIS.mkdir(exist_ok=True); EXPORTS.mkdir(parents=True,exist_ok=True); REVIEW_ROOT.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0])
    with (EXPORTS/"bh_5432_measure_inventory.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    md=["# BH-5432 complete source map","",f"All {len(rows)} track-measures are accounted for.","","| Track | M | Notes | Rests | Pitches | Annotation | Imported | Decision |","|---|---:|---:|---:|---|---|---|---|"]
    md += [f"| {r['track']} | {r['measure']} | {r['sounding_note_count']} | {r['rest_count']} | {r['pitch_sequence']} | {r['annotation']} | {r['family'] or 'no'} | {r['reason']} |" for r in rows]
    (ANALYSIS/"bh_5432_complete_source_map.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    manifest={"package":"bh-5432","status":"needs_review","decisions":[]}
    with connect(database) as db:
        versions=list(db.execute("SELECT slug FROM lick_versions ORDER BY id"))
        for vr in versions:
            slug=vr["slug"]; notes,fings=_version_data(db,slug); source=fings["source"]; generated=fings["generated"]
            folder=REVIEW_ROOT/slug; folder.mkdir(exist_ok=True)
            original=[{**e,"duration":notes[i]["duration"]} for i,e in enumerate(source)]
            alternate=[{**e,"duration":notes[i]["duration"]} for i,e in enumerate(generated)]
            _write_tg(folder/f"{slug}.tg",[("Source excerpt",original,"Original source excerpt")],60)
            _write_musicxml(folder/f"{slug}.musicxml",slug,original)
            _write_midi(folder/f"{slug}_60bpm.mid",original,60); _write_midi(folder/f"{slug}_120bpm.mid",original,120)
            _write_pdf(folder/f"{slug}.pdf",slug,notes,source,generated)
            tracks=[("Original source excerpt",original,"Source"),("Extracted lick",original,"Extracted database events"),("Generated alternate fingering",alternate,"NEEDS REVIEW"),("Approved application examples",original,"Application is proposed, not approved"),("Review notes",original[:1],"Approve/revise/reject in manifest")]
            _write_tg(folder/f"{slug}_comparison.tg",tracks,60)
            manifest["decisions"].append({"entity":"lick_family","slug":slug.rsplit("-c-source",1)[0],"decision":"pending","boundary":"pending","family_name":"pending","degree_pattern":"pending","source_fingering":"pending","generated_fingering":"pending","analysis":"pending","application":"pending","entry_state":"pending","exit_state":"pending"})
        routes=list(db.execute("SELECT r.*,a.slug AS a,b.slug AS b FROM lick_transition_routes r JOIN lick_versions a ON a.id=r.from_version_id JOIN lick_versions b ON b.id=r.to_version_id ORDER BY r.id"))
        for r in routes:
            an,af=_version_data(db,r["a"]); bn,bf=_version_data(db,r["b"])
            origin=af["generated" if r["route_type"]=="intentional_register_shift" else "source"]
            dest=bf["source" if r["route_type"]=="intentional_register_shift" else ("generated" if "generated" in r["explanation"] else "source")]
            origin=[{**e,"duration":an[i]["duration"]} for i,e in enumerate(origin)]
            dest=[{**e,"duration":bn[i]["duration"]} for i,e in enumerate(dest)]
            _write_tg(REVIEW_ROOT/f"transition_{r['id']}_{r['route_type']}.tg",[("Origin",origin,r["a"]),("Destination",dest,r["explanation"])],60)
            _write_midi(REVIEW_ROOT/f"transition_{r['id']}_60bpm.mid",origin+dest,60)
            manifest["decisions"].append({"entity":"transition_route","id":r["id"],"decision":"pending","notes":r["explanation"]})
    (REPO_ROOT/"reviews").mkdir(exist_ok=True)
    (REPO_ROOT/"reviews"/"bh_5432_musical_acceptance.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    _write_reports(rows)
    return {"track_measures":len(rows),"families":3,"transition_tg":4,"review_root":str(REVIEW_ROOT)}


def _write_reports(rows):
    (ANALYSIS/"bh_5432_phrase_boundary_review.md").write_text("""# BH-5432 phrase boundary review

Measures 1–3 of Track 1 were selected only because their TG annotations explicitly identify starting degrees five, four, and three. They are compact instructional examples/cells, not yet accepted complete licks. Their boundaries are measure boundaries from the first extractor and require human confirmation; adjacent measures may belong musically.
""",encoding="utf-8")
    annotations="\n".join(f"- Track {r['track_index']} m{r['measure']}: {r['annotation']}" for r in rows if r["annotation"])
    (ANALYSIS/"bh_5432_canonical_pattern_audit.md").write_text(f"""# BH-5432 canonical pattern audit

- From five: present and extracted (Track 1, m1).
- From four: present and extracted (Track 1, m2).
- From three: present and extracted (Track 1, m3).
- From two: not established by the first three extracted measures; other annotated material requires human review before extraction.
- Other starts: present in the remaining instructional material but not classified automatically.

## Source annotations
{annotations}
""",encoding="utf-8")
    (ANALYSIS/"bh_5432_harmonic_application_review.md").write_text("""# BH-5432 harmonic application review

Source facts: pitches, rhythm, 4/4, 120 BPM, track labels, annotations, and TAB fingering. The files contain no harmony elements.

User doctrine: the canonical definition is in C and changes with the active chord. Current “major-sixth/static C” applications are review placeholders, not complete musical applications. Chord-relative transformation, active-chord selection, structural targets, and resolution rules remain decisions for the user.
""",encoding="utf-8")
    (ANALYSIS/"bh_5432_chord_relative_demonstration.md").write_text("""# Chord-relative demonstration (review only)

| Mode | Active harmony | What remains constant | What changes |
|---|---|---|---|
| Canonical definition | C | canonical family/degree identity | nothing |
| Fixed transposition | D | interval/degree path | every pitch rises two semitones |
| Chord-relative realization | changing progression | family identity and rhythmic version | pitches, chord-relative degrees, fingering, and target tones |

No progression is promoted here because the source contains no harmony and no tracked canonical BH-5432 progression was found in this branch.
""",encoding="utf-8")
    (ANALYSIS/"bh_5432_unresolved_questions.md").write_text("""# BH-5432 unresolved questions

1. Confirm whether Track 1 measures 1–3 are complete licks or instructional cells.
2. Identify and name any “from two” material in the remaining measures.
3. Define the guitar/banjo relationship.
4. Approve or revise each generated adjacent-string-set fingering in TuxGuitar.
5. Supply the canonical chord-relative test progression and transformation rules.
6. Approve or reject each physical transition and its musical purpose.
""",encoding="utf-8")
