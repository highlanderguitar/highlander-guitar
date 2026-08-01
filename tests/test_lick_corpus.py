from pathlib import Path
import pytest
from highlander_render.db.core import connect
from highlander_render.db.licks import extract_package, transpose

def test_lick_schema_and_hard_constraints(tmp_path: Path):
    from highlander_render.db.core import migrate
    p=tmp_path/"x.sqlite3"; migrate(p)
    with connect(p) as db:
        names={r[0] for r in db.execute("select name from sqlite_schema")}
        assert {"lick_families","lick_source_phrases","lick_versions","lick_version_notes","lick_fingerings","lick_harmonic_analyses","lick_applications","lick_entry_states","lick_exit_states","lick_transition_routes"} <= names

def test_generated_fingering_cannot_be_canonical(tmp_path: Path):
    from highlander_render.db.core import migrate
    p=tmp_path/"x.sqlite3"; migrate(p)
    with connect(p) as db:
        with pytest.raises(Exception):
            db.execute("insert into lick_version_notes(version_id,event_index,measure_number,beat,onset,duration) values (99,1,1,1,0,0)")

def test_transposition_storage_requires_existing_version(tmp_path: Path):
    from highlander_render.db.core import migrate
    p=tmp_path/"x.sqlite3"; migrate(p)
    with pytest.raises(Exception): transpose(p,"missing",2)
