from pathlib import Path

from highlander_render.db.core import connect, migrate
from highlander_render.db.phrase_graph import seed_phrase_graph


def test_phrase_graph_migration_and_seed_are_ordered_and_idempotent(tmp_path: Path):
    database = tmp_path / "phrase.sqlite3"
    assert migrate(database) == 5
    assert migrate(database) == 0
    first = seed_phrase_graph(database)
    second = seed_phrase_graph(database)
    assert first == second
    assert first == {
        "phrase_corpora": 1,
        "phrases": 7,
        "phrase_realizations": 16,
        "phrase_musical_dna": 7,
        "phrase_relationships": 7,
    }
    with connect(database) as db:
        objects = {row[0] for row in db.execute("SELECT name FROM sqlite_schema")}
        assert {"phrases", "phrase_musical_dna", "phrase_relationships", "setlist_phrase_candidates"} <= objects
        assert db.execute("SELECT COUNT(*) FROM phrases WHERE user_approval='pending'").fetchone()[0] == 7
