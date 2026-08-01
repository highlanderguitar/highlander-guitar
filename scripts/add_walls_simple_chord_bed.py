from __future__ import annotations

import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT=Path(__file__).resolve().parents[1]
FILES=[ROOT/'reviews/setlist/walls_of_time/bh_5432_review/walls-of-time-BH5432-Review.tg',ROOT/'reviews/setlist/walls_of_time/phrase_review/walls-of-time-Phrase-Review.tg']

def duration(voice):
 old=voice.find('duration')
 if old is not None:voice.remove(old)
 d=ET.SubElement(voice,'duration',value='1');ET.SubElement(d,'divisionType',enters='1',times='1')

def main():
 for path in FILES:
  with ZipFile(path) as z:version=z.read('version.txt');root=ET.fromstring(z.read('content.xml'))
  song=root.find('TGSong')
  for old in [t for t in song.findall('TGTrack') if t.findtext('name')=='Simple Chord Bed — Analysis Only']:song.remove(old)
  rhythm=next(t for t in song.findall('TGTrack') if t.findtext('name')=='Canonical Rhythm')
  bed=ET.SubElement(song,'TGTrack',maxFret=rhythm.get('maxFret','30'))
  for e in [deepcopy(x) for x in rhythm if x.tag not in {'TGMeasure'}]:bed.append(e)
  bed.find('name').text='Simple Chord Bed — Analysis Only'
  for measure in rhythm.findall('TGMeasure'):
   out=ET.SubElement(bed,'TGMeasure')
   for e in [deepcopy(x) for x in measure if x.tag not in {'TGBeat'}]:out.append(e)
   source=next((b for b in measure.findall('TGBeat') if b.find('chord') is not None and b.findall('./voice/note')),None)
   if source is not None:
    b=deepcopy(source)
    for voice in b.findall('voice'):duration(voice)
    out.append(b)
  content=ET.tostring(root,encoding='utf-8',xml_declaration=True)
  with ZipFile(path,'w',compression=ZIP_DEFLATED) as z:
   for n,d in [('version.txt',version),('content.xml',content)]:
    i=ZipInfo(n,date_time=(1980,1,1,0,0,0));i.compress_type=ZIP_DEFLATED;z.writestr(i,d)
if __name__=='__main__':main()
