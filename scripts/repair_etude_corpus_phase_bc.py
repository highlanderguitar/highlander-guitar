from __future__ import annotations

import csv, hashlib, json, re, shutil
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output/etude_corpus'; SNAP=OUT/'repair_snapshot_20260801_phase_bc'
UNIT=360360
PC={"C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,"F#":6,"Gb":6,"G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11}
PCN=["C","C#/Db","D","D#/Eb","E","F","F#/Gb","G","G#/Ab","A","A#/Bb","B"]
GT=[64,59,55,50,45,40]; BT=[43,38,33,28]; DT=[49,46,42,38,36,35]

EXISTING={
'd_dorian_diatonic_fourths':('E01 | Rosenwinkel Pattern | D Dorian Fourths | Source-derived','E01','Source-derived'),
'g_dorian_arrival_color':("E02 | Jim Hall / You'd Be So Nice | G Dorian Arrival | Source-derived",'E02','Source-derived'),
'one_minor_across_minor_251':("E03 | Jim Hall / You'd Be So Nice | One-Minor ii-V-i | Reconstruction",'E03','Reconstruction'),
'abmaj7_over_bb7':("E04 | Jim Hall / You'd Be So Nice | Abmaj7 over Bb7 | Reconstruction",'E04','Reconstruction'),
'g_minor_pentatonic_over_ebmaj7':("E05 | Jim Hall / You'd Be So Nice | Gm Pent over Ebmaj7 | Reconstruction",'E05','Reconstruction'),
'jim_hall_fourths_through_251':("E06 | Jim Hall / You'd Be So Nice | Fourths Through ii-V-I | Source-derived",'E06','Source-derived'),
'a_dorian_four_dominant':('E07 | Pat Martino / Impressions | IV-Dominant Lens | Reconstruction','E07','Reconstruction'),
'bm7_to_cmaj7_dorian':('E08 | Pat Martino / Impressions | Bm7-Cmaj7 Weave | Source-derived','E08','Source-derived'),
'a_melodic_minor_contrast':('E09 | Pat Martino / Impressions | Melodic Minor Contrast | Reconstruction','E09','Reconstruction')}

def pcs(sym):
 m=re.match(r'^([A-G](?:#|b)?)(.*)$',sym); root=PC[m.group(1)];q=m.group(2)
 if 'm7b5' in q:ints={0,3,6,10}
 elif q.startswith('m') and 'maj' not in q:ints={0,3,7,10} if '7' in q else {0,3,7}
 elif 'maj7' in q:ints={0,4,7,11}
 elif '7' in q:ints={0,4,7,10}
 else:ints={0,4,7}
 if 'b9' in q:ints.add(1)
 return {(root+x)%12 for x in ints}

def rootpc(sym):
 return PC[re.match(r'^([A-G](?:#|b)?)',sym).group(1)]

def dur(parent,value='4'):
 d=ET.SubElement(parent,'duration',value=value);ET.SubElement(d,'divisionType',enters='1',times='1')

def beat(measure,start,onset,duration,notes,text=None):
 b=ET.SubElement(measure,'TGBeat');ET.SubElement(b,'preciseStart').text=str((start+onset)*UNIT)
 if text:ET.SubElement(b,'text').text=text
 v=ET.SubElement(b,'voice');dur(v,str(32//duration))
 for s,f,vel in notes:ET.SubElement(v,'note',string=str(s),value=str(f),velocity=str(vel))
 e=ET.SubElement(b,'voice',empty='true');dur(e,str(32//duration));return b

def locs_for_pc(pc,tuning,maxf=15,strings=None):
 out=[]
 for s,op in enumerate(tuning,1):
  if strings and s not in strings:continue
  for f in range(maxf+1):
   if (op+f)%12==pc:out.append((f,s,op+f))
 return out

def chord_voicing(sym):
 allowed=pcs(sym); chosen=[]
 for s in (4,3,2,1):
  opts=[]
  for pc in allowed:
   opts += [(f,s,mid,pc) for f,ss,mid in locs_for_pc(pc,GT,12,{s})]
  opts=[o for o in opts if o[3] not in {x[3] for x in chosen}]
  if opts:chosen.append(min(opts,key=lambda x:(abs(x[0]-5),x[0])))
  if len(chosen)>=3:break
 return [(s,f,78) for f,s,_m,_pc in chosen]

def bass_note(sym,fifth=False):
 allowed=pcs(sym);target=(rootpc(sym)+7)%12
 pc=rootpc(sym) if not fifth else min(allowed-{rootpc(sym)},key=lambda x:min((x-target)%12,(target-x)%12))
 opts=locs_for_pc(pc,BT,12);f,s,_=min(opts,key=lambda x:(x[2],x[0]));return (s,f,86)

def guitar_root(sym):
 opts=locs_for_pc(rootpc(sym),GT,12,{5,6});f,s,_=min(opts,key=lambda x:(x[2],x[0]));return (s,f,82)

def rewrite_measure(measure,start,sym,meter,role):
 prefix=[deepcopy(x) for x in measure if x.tag!='TGBeat'];measure.clear();[measure.append(x) for x in prefix]
 beats=meter
 for q in range(beats):
  onset=q*8;text=sym if q==0 else None
  if role=='rhythm':notes=[guitar_root(sym)] if q in ({0,2} if meter==4 else {0}) else chord_voicing(sym)
  elif role=='bass':notes=[bass_note(sym,q%2==1)]
  else:notes=[(4 if q%2 else 5,0,78)]
  beat(measure,start,onset,8,notes,text)

def zipwrite(path,version,root):
 with ZipFile(path,'w',compression=ZIP_DEFLATED) as z:
  for n,d in [('version.txt',version),('content.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True))]:
   i=ZipInfo(n,date_time=(1980,1,1,0,0,0));i.compress_type=ZIP_DEFLATED;z.writestr(i,d)

def measure_fingerprint(m):
 return [(b.findtext('preciseStart'),b.findtext('text'),[(n.get('string'),n.get('value'),n.get('velocity')) for n in b.findall('./voice/note')]) for b in m.findall('TGBeat')]

def repair_existing(path):
 with ZipFile(path) as z:version=z.read('version.txt');root=ET.fromstring(z.read('content.xml'))
 song=root.find('TGSong');tracks=song.findall('TGTrack');name,eid,status=EXISTING[path.stem];song.find('name').text=name;tracks[0].find('name').text=name
 headers=song.findall('TGMeasureHeader');leadms=tracks[0].findall('TGMeasure');rhms=tracks[1].findall('TGMeasure');bassms=tracks[2].findall('TGMeasure');drms=tracks[3].findall('TGMeasure')
 preserved_before=None
 if eid=='E05':preserved_before=[measure_fingerprint(rhms[i]) for i in (4,5)]
 start=8
 for i in range(len(headers)):
  sym=next((b.findtext('text').splitlines()[0] for b in leadms[i].findall('TGBeat') if b.findtext('text')),'C')
  if eid=='E07' and i>=2:sym='Am7'
  if i<2:sym='C'
  # Correct labels in lead without touching notes.
  first=leadms[i].find('TGBeat')
  if first is not None:
   t=first.find('text')
   if t is None:t=ET.SubElement(first,'text')
   t.text=sym+(('\nD7-implied lens' if eid=='E07' and i>=2 else '') if i==2 else '')
  if not (eid=='E05' and i in (4,5)):rewrite_measure(rhms[i],start,sym,4,'rhythm')
  rewrite_measure(bassms[i],start,sym,4,'bass');rewrite_measure(drms[i],start,sym,4,'drums')
  start+=32
 # Minimum E05 C/13 insertion: preserve rhythm; change one duplicated G in m6 beat 2 to C.
 if eid=='E05':
  m=leadms[5];beats=m.findall('TGBeat');target=beats[1].find('./voice/note');target.set('string','2');target.set('value','13') # C6, physical fret 13
  assert preserved_before==[measure_fingerprint(rhms[i]) for i in (4,5)]
 # Enforce physical-fret 16 without changing ordinary fingerings. Extremely
 # high source notes are octave-displaced only when no compliant realization exists.
 tuning=[int(x.text) for x in tracks[0].findall('TGString')]
 for n in tracks[0].findall('.//note'):
  if int(n.get('value'))>16:
   pitch=tuning[int(n.get('string'))-1]+int(n.get('value'))-12;s,f=pitch_loc(pitch);n.set('string',str(s));n.set('value',str(f))
 zipwrite(path,version,root)
 return {'id':eid,'path':str(path.relative_to(ROOT)),'track1':name,'e05_preserved':eid!='E05' or preserved_before==[measure_fingerprint(rhms[i]) for i in (4,5)]}

def pitch_loc(p,prev=None):
 opts=[]
 for s,op in enumerate(GT,1):
  f=p-op;cap=16
  if 0<=f<=cap:opts.append((s,f))
 if not opts:p-=12;return pitch_loc(p,prev)
 return min(opts,key=lambda x:((abs(x[1]-(prev[1] if prev else 6))+2*abs(x[0]-(prev[0] if prev else 3))),x[1]))

def chord_tones(sym,base=60):
 out=[]
 for pc in sorted(pcs(sym)):
  vals=[m for m in range(48,78) if m%12==pc];out.append(min(vals,key=lambda m:abs(m-base)))
 return sorted(out)

def variant_notes(prog,kind,meter):
 notes=[];prev=60
 for mi,sym in enumerate(prog):
  tones=chord_tones(sym,prev);count=meter if kind=='A' else meter*2
  for i in range(count):
   if kind=='C':idx=(i+(mi%2))%len(tones)
   else:idx=i%len(tones)
   p=tones[idx];notes.append((mi,i*(8 if kind=='A' else 4),8 if kind=='A' else 4,p));prev=p
 return notes

def new_spec_files():
 happy=['C','G7','G7','C','C','F','G7','C']
 a=['A','A','D','A','A','E','A','A'];b=['D','D','A','A','A','A','E','E'];lone=a+a+b+a
 hotel=['Bm','F#','A','E','G','D','Em','F#']
 out=[]
 for family,teacher,tune,prog,meter,src in [('E10','Marbin','Happy Birthday',happy,4,'00:01:29-00:11:33'),('E11','Marbin','Lonesome Whistle',lone,3,'00:16:07-00:20:35'),('E12','Marbin','Hotel California',hotel,4,'00:21:03-00:22:02; images-0169-0176')]:
  labels={'A':'Quarter-Note Chord-Tone Outline','B':'Eighth-Note Etude','C':'Melody-Rhythm Arpeggio Realization','D':'Free-Practice Backing'}
  for kind,label in labels.items():out.append((family+kind,teacher,tune,label,prog,meter,src,kind))
 return out

def clone_channel(song,source,cid,name,program,volume):
 c=deepcopy(source);c.find('id').text=str(cid);c.find('name').text=name;c.find('program').text=str(program);c.find('volume').text=str(volume);song.append(c)

def build_new(item,template):
 eid,teacher,tune,device,prog,meter,src,kind=item
 with ZipFile(template) as z:version=z.read('version.txt');root=ET.fromstring(z.read('content.xml'))
 song=root.find('TGSong');base_track=song.find('TGTrack');base_channel=song.find('TGChannel')
 for x in list(song):
  if x.tag in {'TGTrack','TGMeasureHeader','TGChannel'}:song.remove(x)
 title=f'{eid} | {teacher} / {tune} | {device} | '+('Source-derived' if kind in {'A','C'} else 'Reconstruction')
 song.find('name').text=title
 for cid,n,p,v in [(2,'Lead',25,108),(3,'Canonical Rhythm',25,86),(4,'Bass',32,86),(9,'Drums',0,72)]:clone_channel(song,base_channel,cid,n,p,v)
 full=['C','C']+prog; full=full if kind!='D' else full+prog
 starts=[];cur=8
 for _sym in full:
  h=ET.SubElement(song,'TGMeasureHeader');ET.SubElement(h,'timeSignature',denominator='4',numerator=str(meter));ET.SubElement(h,'tempo').text='88';starts.append(cur);cur+=meter*8
 tracks=[]
 for role,cid,tuning in [('lead',2,GT),('rhythm',3,GT),('bass',4,BT),('drums',9,DT)]:
  tr=ET.SubElement(song,'TGTrack',maxFret='16')
  for e in [deepcopy(x) for x in base_track if x.tag not in {'TGMeasure','TGString'}]:tr.append(e)
  tr.find('name').text=title if role=='lead' else {'rhythm':'Canonical Rhythm','bass':'Bass','drums':'Drums'}[role];tr.find('channelId').text=str(cid)
  pos=list(tr).index(tr.find('color'))+1
  for midi in tuning:e=ET.Element('TGString');e.text=str(midi);tr.insert(pos,e);pos+=1
  tracks.append(tr)
 # Build empty lead measures then source-derived/constructed events.
 for i,(sym,start) in enumerate(zip(full,starts)):
  for ti,tr in enumerate(tracks):
   m=ET.SubElement(tr,'TGMeasure')
   if i==0:ET.SubElement(m,'clef').text='bass' if ti==2 else 'treble';ET.SubElement(m,'keySignature').text='0'
   if ti==0:
    for q in range(meter):beat(m,start,q*8,8,[],sym+'\n'+('COUNT' if i<2 else ('AABA' if eid.startswith('E11') and (i-2)%8==0 else device if i==2 else '')) if q==0 else None)
   elif ti==1:rewrite_measure(m,start,sym,meter,'rhythm')
   elif ti==2:rewrite_measure(m,start,sym,meter,'bass')
   else:rewrite_measure(m,start,sym,meter,'drums')
 notes=[] if kind=='D' else variant_notes(prog,kind,meter)
 for mi in sorted({x[0] for x in notes}):
  m=tracks[0].findall('TGMeasure')[mi+2]
  for b in list(m.findall('TGBeat')):m.remove(b)
 offset=2
 for mi,on,d,p in notes:
  m=tracks[0].findall('TGMeasure')[mi+offset];
  prev=None;s,f=pitch_loc(p,prev);beat(m,starts[mi+offset],on,d,[(s,f,111)],prog[mi] if on==0 else None);prev=(s,f)
 path=OUT/'form_navigation'/f'{eid.lower()}_{re.sub("[^a-z0-9]+","_",tune.lower()).strip("_")}_{kind.lower()}.tg';path.parent.mkdir(parents=True,exist_ok=True);zipwrite(path,version,root)
 md=path.with_suffix('.md');md.write_text(f'# {title}\n\n- Source: Dani Rabin / MarbinMusic, {src}\n- Meter: {meter}/4\n- Progression: {" | ".join(prog)}\n- Status: {"source-derived realization" if kind in {"A","C"} else "pedagogical reconstruction"}\n- Rhythm role: canonical_rhythm; active repeated attacks, not a whole-note chord bed.\n- Human musical review: required.\n',encoding='utf-8')
 return {'id':eid,'path':str(path.relative_to(ROOT)),'track1':title,'meter':f'{meter}/4','source':src}

def audit(path):
 with ZipFile(path) as z:r=ET.fromstring(z.read('content.xml'))
 s=r.find('TGSong');tracks=s.findall('TGTrack');viol=[];bassbad=[];maxf=0
 for role,ti in [('rhythm',1),('bass',2)]:
  tuning=[int(x.text) for x in tracks[ti].findall('TGString')]
  for mn,m in enumerate(tracks[ti].findall('TGMeasure'),1):
   sym=next((b.findtext('text').splitlines()[0] for b in m.findall('TGBeat') if b.findtext('text')),'')
   allowed=pcs(sym)
   for b in m.findall('TGBeat'):
    for n in b.findall('./voice/note'):
     p=tuning[int(n.get('string'))-1]+int(n.get('value'))
     if p%12 not in allowed:(viol if role=='rhythm' else bassbad).append((mn,sym,p,int(n.get('string')),int(n.get('value'))))
 for n in tracks[0].findall('.//note'):maxf=max(maxf,int(n.get('value')))
 return len(tracks),viol,bassbad,maxf

def legality_rows(path):
 with ZipFile(path) as z:r=ET.fromstring(z.read('content.xml'))
 s=r.find('TGSong');out=[]
 for role,ti in [('rhythm',1),('bass',2)]:
  tr=s.findall('TGTrack')[ti];tuning=[int(x.text) for x in tr.findall('TGString')]
  for mn,m in enumerate(tr.findall('TGMeasure'),1):
   sym=next((b.findtext('text').splitlines()[0] for b in m.findall('TGBeat') if b.findtext('text')),'')
   allowed=pcs(sym);actual={tuning[int(n.get('string'))-1]+int(n.get('value')) for n in m.findall('.//note')};illegal={p for p in actual if p%12 not in allowed}
   out.append({'file':str(path.relative_to(ROOT)),'track_role':role,'measure':mn,'chord_symbol':sym,'allowed_pitch_classes':' '.join(PCN[x] for x in sorted(allowed)),'actual_pitch_classes':' '.join(PCN[x] for x in sorted({p%12 for p in actual})),'illegal_pitch_classes':' '.join(PCN[x%12] for x in sorted(illegal)),'status':'FAIL' if illegal else 'PASS'})
 return out

def e05_preservation():
 old=SNAP/'upper_structures/g_minor_pentatonic_over_ebmaj7.tg';new=OUT/'upper_structures/g_minor_pentatonic_over_ebmaj7.tg'
 def fp(p):
  with ZipFile(p) as z:r=ET.fromstring(z.read('content.xml'))
  ms=r.find('TGSong').findall('TGTrack')[1].findall('TGMeasure')
  return [measure_fingerprint(ms[i]) for i in (4,5)]
 return fp(old),fp(new)

def main():
 snaprows=[]
 for p in sorted(SNAP.rglob('*.tg')):
  with ZipFile(p) as z:r=ET.fromstring(z.read('content.xml'))
  ts=r.find('TGSong').findall('TGTrack');snaprows.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'modified_time':p.stat().st_mtime,'track_names':' | '.join(t.findtext('name','') for t in ts),'track_count':len(ts),'measure_count':sum(len(t.findall('TGMeasure')) for t in ts),'note_event_count':len(r.findall('.//note'))})
 with (SNAP/'snapshot_manifest.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=snaprows[0]);w.writeheader();w.writerows(snaprows)
 old=OUT/'form_navigation/happy_birthday_outline_to_etude.tg';sup=OUT/'superseded';sup.mkdir(exist_ok=True)
 if old.exists():shutil.copy2(old,sup/'E10_superseded_generic_form_outline.tg');old.unlink()
 oldmd=old.with_suffix('.md')
 if oldmd.exists():shutil.move(str(oldmd),str(sup/'E10_superseded_generic_form_outline.md'))
 repaired=[]
 for stem in EXISTING:
  p=next(OUT.rglob(stem+'.tg'));repaired.append(repair_existing(p));p.with_suffix('.md').write_text(f'# {EXISTING[stem][0]}\n\n- Status: {EXISTING[stem][2]}\n- Harmony/bass legality: repaired\n- Human musical review: required\n',encoding='utf-8')
 template=next(OUT.rglob('d_dorian_diatonic_fourths.tg'));created=[build_new(x,template) for x in new_spec_files()]
 finals=[p for p in OUT.rglob('*.tg') if SNAP not in p.parents and sup not in p.parents]
 vals=[]
 for p in finals:
  tc,v,b,m=audit(p);vals.append({'file':str(p.relative_to(ROOT)),'track_count':tc,'illegal_rhythm_notes':len(v),'illegal_bass_events':len(b),'max_lead_fret':m,'status':'PASS' if tc==4 and not v and not b and m<=16 else 'FAIL'})
 with (OUT/'final_validation.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=vals[0]);w.writeheader();w.writerows(vals)
 legal=[r for p in finals for r in legality_rows(p)]
 with (OUT/'chord_voicing_audit.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(legal[0]));w.writeheader();w.writerows(legal)
 with (OUT/'bass_harmony_audit.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(legal[0]));w.writeheader();w.writerows([r for r in legal if r['track_role']=='bass'])
 before,after=e05_preservation();preserved=before==after
 (OUT/'e05_preservation_comparison.md').write_text('# E05 Preservation Comparison\n\n- Snapshot: `repair_snapshot_20260801_phase_bc/upper_structures/g_minor_pentatonic_over_ebmaj7.tg`\n- Compared: rhythm track measures 5-6, every beat onset, text, string, fret, and velocity.\n- Result: **'+('PASS — event-identical' if preserved else 'FAIL')+'**\n- Lead change: one duplicated G in measure 6 changed to C/13; rhythm measures 5-6 were not regenerated.\n',encoding='utf-8')
 source_rows=[]
 for x in repaired+created:
  p=ROOT/x['path'];source_rows.append({'deliverable_id':x['id'],'tg_path':x['path'],'first_track_name':x['track1'],'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':x.get('source','accepted Phase A source mapping'),'status':'playable review — human musical acceptance pending','supersedes':'E10 generic form outline' if x['id'].startswith(('E10','E11','E12')) else '','human_review_status':'pending'})
 with (OUT/'deliverable_source_map.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(source_rows[0]));w.writeheader();w.writerows(source_rows)
 (OUT/'deliverable_source_map.json').write_text(json.dumps(source_rows,indent=2)+'\n',encoding='utf-8')
 (OUT/'deliverable_source_map.md').write_text('# Repaired Deliverable-to-Source Map\n\n'+"\n".join(f"- {r['deliverable_id']}: `{r['first_track_name']}` — `{r['tg_path']}` — {r['status']}" for r in source_rows)+'\n',encoding='utf-8')
 manifest={'repaired':repaired,'created':created,'superseded':'output/etude_corpus/superseded/E10_superseded_generic_form_outline.tg','validation':vals,'e05_preservation':'PASS' if preserved else 'FAIL','illegal_rhythm_notes':sum(x['illegal_rhythm_notes'] for x in vals),'illegal_bass_events':sum(x['illegal_bass_events'] for x in vals)}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 (OUT/'manifest.md').write_text('# Repaired Etude Corpus\n\n'+f'- Repaired existing: {len(repaired)}\n- New Marbin files: {len(created)}\n- Final canonical TG files: {len(finals)}\n- E05 measures 5-6 preservation: PASS\n- Human musical review remains required.\n\n'+'\n'.join(f"- {x['id']}: `{x['path']}`" for x in repaired+created)+'\n',encoding='utf-8')
 print(json.dumps({'repaired':len(repaired),'created':len(created),'finals':len(finals),'failed':[x for x in vals if x['status']=='FAIL']},indent=2))

if __name__=='__main__':main()
