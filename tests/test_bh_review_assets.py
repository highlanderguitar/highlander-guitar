from pathlib import Path
import zipfile
from highlander_render.db.review_assets import _tg_xml

def test_comparison_tg_has_five_named_tracks():
    event={"string_number":2,"fret":5,"duration":0.5}
    tracks=[(name,[event],"review") for name in ("Original source excerpt","Extracted lick","Generated alternate fingering","Approved application examples","Review notes")]
    xml=_tg_xml(tracks)
    assert xml.count("<TGTrack ") == 5
    for name,_,_ in tracks: assert name in xml

def test_tg_notes_are_playable_string_fret_pairs():
    event={"string_number":3,"fret":7,"duration":0.5}
    xml=_tg_xml([("Guitar",[event],"")])
    assert 'note string="3" value="7"' in xml
