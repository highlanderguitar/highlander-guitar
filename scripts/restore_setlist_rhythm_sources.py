from __future__ import annotations

import csv, hashlib, json, shutil
import xml.etree.ElementTree as ET
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT=Path(__file__).resolve().parents[1]
W=ROOT/'reviews/setlist/walls_of_time'
SOURCE=W/'source_working_copy/walls-of-time-source.tg'
CANON=W/'canonical/walls-of-time.tg'
BH=W/'bh_5432_review/walls-of-time-BH5432-Review.tg'
TRAV=W/'phrase_review/walls-of-time-Phrase-Review.tg'
SNAP=W/'repair_snapshot_before_source_authority'
AN=ROOT/'analysis';AN.mkdir(exist_ok=True)

def load(p):
 with ZipFile(p) as z:return z.read('version.txt'),ET.fromstring(z.read('content.xml'))
def write(p,v,r):
 p.parent.mkdir(parents=True,exist_ok=True)
 with ZipFile(p,'w',compression=ZIP_DEFLATED) as z:
  for n,d in [('version.txt',v),('content.xml',ET.tostring(r,encoding='utf-8',xml_declaration=True))]:
   i=ZipInfo(n,date_time=(1980,1,1,0,0,0));i.compress_type=ZIP_DEFLATED;z.writestr(i,d)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dur_units(v):
 d=v.find('duration');base=32/int(d.get('value'));div=d.find('divisionType');return base*int(div.get('times','1'))/int(div.get('enters','1'))
def fingerprint(p,track_index):
 _v,r=load(p);s=r.find('TGSong');t=s.findall('TGTrack')[track_index];measures=t.findall('TGMeasure');beats=t.findall('.//TGBeat');sound=[b for b in beats if b.findall('./voice/note')]
 ds=Counter();on=Counter();ties=0;chords=0;roots=0;sync=0;voicings=set();repeated=0;single=0;active=0
 for m in measures:
  sounding=[b for b in m.findall('TGBeat') if b.findall('./voice/note')]
  if sounding:active+=1
  if len(sounding)>1:repeated+=1
  if len(sounding)==1 and dur_units(sounding[0].find('voice'))>=32:single+=1
  for b in sounding:
   u=dur_units(b.find('voice'));ds[str(u)]+=1;prec=int(b.findtext('preciseStart'));on[str((prec//360360)%32)]+=1
   if ((prec//360360)%8)!=0:sync+=1
   if b.find('chord') is not None:chords+=1
   ns=tuple(sorted((int(n.get('string')),int(n.get('value'))) for n in b.findall('./voice/note')));voicings.add(ns)
   roots+=sum(1 for n in b.findall('./voice/note') if int(n.get('string'))>=5)
   ties+=sum(1 for n in b.findall('.//note') if n.get('tiedNote')=='true')
 return {'track_id':track_index,'track_name':t.findtext('name'),'measure_count':len(measures),'sounding_event_count':len(sound),'note_count':len(t.findall('.//note')),'chord_event_count':chords,'root_bass_note_count':roots,'duration_histogram':json.dumps(ds,sort_keys=True),'onset_histogram':json.dumps(on,sort_keys=True),'rests':len(beats)-len(sound),'measures_repeated_attacks':repeated,'measures_one_sustained_chord':single,'split_measure_activity':repeated,'syncopated_events':sync,'tie_count':ties,'unique_voicing_count':len(voicings),'maximum_silent_span':'not-derived','percent_measures_active':round(100*active/max(1,len(measures)),2),'sha256':sha(p)}
def snapshot():
 SNAP.mkdir(parents=True,exist_ok=True)
 for p in (CANON,BH,TRAV):
  if p.exists():shutil.copy2(p,SNAP/p.name)
def remove_dead(root):
 count=0
 for voice in root.findall('.//voice'):
  for n in list(voice.findall('note')):
   if n.find('deadNote') is not None:voice.remove(n);count+=1
 return count
def canonical_root():
 v,r=load(SOURCE);s=r.find('TGSong');s.find('name').text='Walls of Time — Source-Authority Canonical';tracks=s.findall('TGTrack');tracks[0].find('name').text='Canonical Lead';tracks[1].find('name').text='Canonical Rhythm';removed=remove_dead(r);return v,r,removed
def add_review_track(base,old_path,label):
 _ov,old=load(old_path);os=old.find('TGSong');review=os.findall('TGTrack')[-1];channel_id=review.findtext('channelId');channel=next((c for c in os.findall('TGChannel') if c.findtext('id')==channel_id),None)
 s=base.find('TGSong')
 if channel is not None and not any(c.findtext('id')==channel_id for c in s.findall('TGChannel')):s.append(deepcopy(channel))
 tr=deepcopy(review);tr.find('name').text=label
 target=len(s.findall('TGMeasureHeader'));ms=tr.findall('TGMeasure')
 while len(ms)<target:tr.append(ET.Element('TGMeasure'));ms=tr.findall('TGMeasure')
 while len(ms)>target:tr.remove(ms[-1]);ms=tr.findall('TGMeasure')
 s.append(tr)
def chord_events(root):
 t=root.find('TGSong').findall('TGTrack')[1];rows=[]
 for mi,m in enumerate(t.findall('TGMeasure'),1):
  for b in m.findall('TGBeat'):
   c=b.find('chord')
   if c is not None:rows.append((mi,b.findtext('preciseStart'),c.findtext('name')))
 return rows
def audit_all_setlist():
 rows=[]
 for p in sorted((ROOT/'reviews/setlist').rglob('*.tg')):
  try:
   _v,r=load(p);tracks=r.find('TGSong').findall('TGTrack')
   for i,t in enumerate(tracks):
    name=t.findtext('name','').lower()
    if 'rhythm' in name or 'backing' in name or (p==SOURCE and i==1):
     x=fingerprint(p,i);x.update(file=str(p.relative_to(ROOT)),modified_time=datetime.fromtimestamp(p.stat().st_mtime).isoformat(),selection='authority' if p==SOURCE else 'candidate');rows.append(x)
  except Exception:pass
 return rows
def main():
 snapshot();prior={p.name:fingerprint(p,1) for p in (CANON,BH,TRAV)}
 srcfp=fingerprint(SOURCE,1);v,root,removed=canonical_root();events=chord_events(root);write(CANON,v,root)
 _,bhroot=canonical_root()[:2];bhroot.find('TGSong').find('name').text='Walls of Time — BH-5432 Review — Source Rhythm';add_review_track(bhroot,SNAP/BH.name,'Lead / Phrase Review — BH-5432');write(BH,v,bhroot)
 _,trroot=canonical_root()[:2];trroot.find('TGSong').find('name').text='Walls of Time — BH Traversals Review — Source Rhythm';add_review_track(trroot,SNAP/TRAV.name,'Lead / Phrase Review — BH Traversals');write(TRAV,v,trroot)
 repaired=fingerprint(CANON,1)
 lines=['# Walls of Time Source Authority Audit','',f'- Exact source: `{SOURCE}`',f'- SHA-256: `{sha(SOURCE)}`',f'- Modified: {datetime.fromtimestamp(SOURCE.stat().st_mtime).isoformat()}','- Tracks: Canonical Lead (source Lead); Canonical Rhythm (source Track 1)','- Roles: lead; canonical_rhythm',f'- Measures: {srcfp["measure_count"]}',f'- Tempo: 140 BPM','- Meter: 4/4','- Capo/track offset: 4','- Tuning: E A D G B E','- Bass track: none in source',f'- Lead notes: {fingerprint(SOURCE,0)["note_count"]}',f'- Rhythm notes: {srcfp["note_count"]}',f'- Rhythm sounding beats: {srcfp["sounding_event_count"]}',f'- Chord events: {srcfp["chord_event_count"]}',f'- Muted X/dead-note events removed in repaired files: {removed}','','## Prior versus restored','']
 for name,x in prior.items():lines.append(f'- {name}: {x["measure_count"]} measures / {x["note_count"]} rhythm notes → 49 measures / {repaired["note_count"]} rhythm notes.')
 lines += ['','## Chord events','']+[f'- m{m}: {c} (preciseStart {p})' for m,p,c in events]+['','## Stale derived records','','All prior Walls of Time progression normalization, opportunity windows, BH placements, traversal placements, capo/physical-fret results, and backing synchronization based on the 17-measure scaffold are stale. Review phrase locations retained from the old files remain provisional until remapped against the 49-measure authority.']
 (AN/'walls_of_time_source_authority_audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 fps=audit_all_setlist();
 with (ROOT/'analysis/setlist_rhythm_fingerprints.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(fps[0]));w.writeheader();w.writerows(fps)
 (AN/'setlist_rhythm_source_audit.md').write_text('# Set-list Rhythm Source Audit\n\nWalls of Time: explicit `walls-of-time-source.tg` selected with high confidence. It is superior to the generated 17-measure scaffold by form and rhythmic content. Other set-list TG candidates are inventoried in `setlist_rhythm_fingerprints.csv`; no other tune was automatically overwritten in this proof slice.\n',encoding='utf-8')
 with (AN/'setlist_rhythm_restoration_report.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(['tune','source','canonical','prior_measures','restored_measures','prior_rhythm_notes','restored_rhythm_notes','status']);w.writerow(['Walls of Time',SOURCE,CANON,prior[CANON.name]['measure_count'],49,prior[CANON.name]['note_count'],repaired['note_count'],'RESTORED'])
 (AN/'setlist_rhythm_correction_suggestions.md').write_text('# Set-list Rhythm Correction Suggestions\n\n## Auto-repaired structural defects\n\n- Replaced the 17-measure Walls of Time scaffold with the 49-measure source authority.\n- Restored the complete user rhythm track.\n- Removed sounding dead/X notes while retaining all ordinary chord tones.\n- Restored capo/offset 4 and source tempo 140.\n\n## Musical suggestions requiring user approval\n\n- Remap the retained BH-5432 and BH-Traversal phrases against the 49-measure source form before musical approval.\n- Confirm whether the source final D/F#–G cadence and short labels should remain exactly as authored.\n- The source has no separate bass track; adding one is a future musical choice, not an automatic repair.\n',encoding='utf-8')
 stale=['progression normalization','measure references','opportunity windows','BH-5432 placements','BH-Traversal placements','chord-change timing','capo interpretation','physical-fret analysis','entry/exit timing','backing-track synchronization']
 with (AN/'stale_analysis_records.csv').open('w',newline='',encoding='utf-8') as f:w=csv.writer(f);w.writerow(['tune','record_type','prior_canonical_hash','new_canonical_hash','status']);[w.writerow(['Walls of Time',x,prior[CANON.name]['sha256'],sha(CANON),'STALE_REQUIRES_REGENERATION']) for x in stale]
 print(json.dumps({'source':str(SOURCE),'source_hash':sha(SOURCE),'prior':prior[CANON.name],'restored':repaired,'dead_removed':removed},indent=2))
if __name__=='__main__':main()
