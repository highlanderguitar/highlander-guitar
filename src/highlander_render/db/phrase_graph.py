from __future__ import annotations

import csv
from pathlib import Path

from .core import DEFAULT_DB_PATH, REPO_ROOT, connect, migrate


TRAVERSAL_HASH = "a2362b74fa3f8f60c5da207478e97f72395e2067a8da35c35f6cdfa03a89104c"
TRAVERSAL_SOURCE = "reviews/bh_traversals/canonical/BH-Traversals.tg"

PHRASES = (
    ("bh-5432-from-5", "BH-5432 From 5", "BH-5432", "BH-5432.tg", None, 1, 1, "lick", 6.5, 13, "5", "3", "tonic third", "tonic color / dominant option", "statement", "middle", "arch", "high", "medium", "medium", 0, 2.0, 4.0, "compact return", "2,3,4", "9-12", 2),
    ("bh-5432-from-4", "BH-5432 From 4", "BH-5432", "BH-5432.tg", None, 2, 2, "lick", 4.5, 9, "4", "3", "tonic third", "tonic color", "answer", "middle", "falling", "medium", "medium", "strong", 0, 2.0, 4.0, "small position shift", "3,4", "7-10", 1),
    ("bh-5432-from-3", "BH-5432 From 3", "BH-5432", "BH-5432.tg", None, 3, 3, "lick", 3.5, 7, "3", "9 / dominant fifth", "post-dominant tonic tone", "dominant pressure", "continuation", "middle", "falling then rising", "medium", "medium", "weak", 1, 2.0, 4.0, "compact", "3,4,5", "9-12", 1),
    ("bh-traversal-up3-down-chord-a", "Up a 3rd, Down a Chord A", "BH Traversals", TRAVERSAL_SOURCE, TRAVERSAL_HASH, 1, 4, "traversal", 4.0, 8, "5", "5", "chord tone", "major / dominant upper structure", "connector", "low-to-high", "rising", "medium", "high", "medium", 0, 2.0, 4.0, "alternate registers", "1,2,3,4,5", "0-11", 1),
    ("bh-traversal-up3-down-chord-b", "Up a 3rd, Down a Chord B", "BH Traversals", TRAVERSAL_SOURCE, TRAVERSAL_HASH, 6, 10, "traversal", 4.0, 8, "5", "1 or 5", "tonic landing", "dominant-to-tonic connector", "connector", "middle", "rise then fall", "medium", "high", "strong", 0, 2.0, 4.0, "cross-string return", "1,2,3,4,5,6", "0-11", 2),
    ("bh-traversal-down3-down-chord", "Down a 3rd, Down a Chord", "BH Traversals", TRAVERSAL_SOURCE, TRAVERSAL_HASH, 12, 14, "traversal", 4.0, 8, "4", "2 or 5", "dominant continuation", "dominant pressure", "continuation", "middle-to-high", "falling", "high", "high", "weak", 1, 2.0, 4.0, "descending string travel", "1,2,3,4,5", "0-13", 2),
    ("bh-traversal-down3-up-chord", "Down a 3rd, Up a Chord", "BH Traversals", TRAVERSAL_SOURCE, TRAVERSAL_HASH, 16, 19, "traversal", 4.0, 8, "4", "1 or 3", "tonic target", "dominant release", "answer", "middle-to-high", "fall then rise", "high", "high", "strong", 0, 2.0, 4.0, "register-changing answer", "1,2,3,4,5", "0-15", 2),
)

REALIZATIONS = {
    "bh-traversal-up3-down-chord-a": ((1, "4,5", 0, 4), (2, "3,4,5,6", 3, 7), (3, "1,2,3,4", 7, 11), (4, "1,2,3", 5, 10)),
    "bh-traversal-up3-down-chord-b": ((6, "4,5,6", 0, 4), (7, "2,3,4,5", 5, 8), (8, "3,4,5", 7, 11), (9, "1,2,3,4", 0, 4), (10, "1,2,3", 0, 4)),
    "bh-traversal-down3-down-chord": ((12, "2,3,4,5", 0, 3), (13, "2,3,4,5", 2, 5), (14, "1,2,3,4", 9, 13)),
    "bh-traversal-down3-up-chord": ((16, "1,2,3", 0, 3), (17, "2,3,4", 7, 10), (18, "1,2,3", 10, 15), (19, "3,4,5", 0, 3)),
}

RELATIONSHIPS = (
    ("bh-5432-from-3", "bh-traversal-up3-down-chord-b", "good successor", "long dominant into tonic", "compact continuation; select realization by register", "shared chord tone", "supplies motion after open D", "eighth-note compatible", .86, "The traversal can continue the unresolved final D before a tonic landing."),
    ("bh-5432-from-3", "bh-traversal-down3-up-chord", "resolves into", "dominant to tonic", "choose M16 or M19 below fret 15", "entry can begin from D-adjacent chord tone", "strong 1/3 target candidate", "eighth-note compatible", .82, "Down-then-up contour supplies the landing missing from From 3."),
    ("bh-traversal-down3-down-chord", "bh-5432-from-3", "prepares", "sustained dominant", "middle register handoff", "falling exit leaves dominant space", "From 3 begins on an upper chord tone", "one measure each", .72, "Both phrases sustain rather than discharge dominant pressure."),
    ("bh-traversal-up3-down-chord-a", "bh-traversal-up3-down-chord-b", "harmonic sibling", "major or dominant region", "alternate register/string routes", "same annotated opening", "B supplies descending return", "same density", .90, "Source repeats the annotation after a separator and changes the return path."),
    ("bh-traversal-up3-down-chord-b", "bh-traversal-down3-up-chord", "good connector", "dominant to tonic", "B exit can route to low M19 or upper M16", "compatible chord-tone entry", "contrasting answer", "same density", .78, "Contrasting contours form statement and answer."),
    ("bh-5432-from-5", "bh-5432-from-4", "good successor", "tonic or dominant color", "existing scored route", "source corpus adjacency", "ends on stable third", "source rhythms compatible", .82, "Existing BH-5432 route analysis favors the playable adjacent-string realization."),
    ("bh-5432-from-4", "bh-5432-from-3", "continues into", "long dominant option", "existing source route", "descending answer", "From 3 remains open", "source rhythms compatible", .76, "Corpus ordering creates increasing need for continuation."),
)


def seed_phrase_graph(database: Path = DEFAULT_DB_PATH) -> dict[str, int]:
    migrate(database)
    with connect(database) as db:
        db.execute("INSERT OR IGNORE INTO phrase_corpora(slug,name,description,review_status) VALUES ('highlander-phrase-corpus','Highlander Phrase Corpus','BH-5432 and BH Traversals in one reviewable corpus','needs_review')")
        corpus_id = db.execute("SELECT id FROM phrase_corpora WHERE slug='highlander-phrase-corpus'").fetchone()[0]
        for p in PHRASES:
            (slug,name,family,path,source_hash,m1,m2,kind,length,count,start,end,target,function,role,register,contour,energy,chromatic,resolution,continuation,min_duration,preferred_duration,travel,string_sets,fret_range,shifts)=p
            lick_slug = {
                "bh-5432-from-5": "bh-5432-five-c-source",
                "bh-5432-from-4": "bh-5432-four-c-source",
                "bh-5432-from-3": "bh-5432-three-c-source",
            }.get(slug)
            lick = db.execute("SELECT id FROM lick_versions WHERE slug=?", (lick_slug,)).fetchone() if lick_slug else None
            db.execute("INSERT OR IGNORE INTO phrases(corpus_id,slug,name,family,source_path,source_hash,source_track,measure_start,measure_end,source_lick_version_id,phrase_kind,review_status,user_approval) VALUES (?,?,?,?,?,?,?,?,?,?,?,'needs_review','pending')",
                       (corpus_id,slug,name,family,path,source_hash,'Track 1',m1,m2,lick[0] if lick else None,kind))
            phrase_id=db.execute("SELECT id FROM phrases WHERE slug=?",(slug,)).fetchone()[0]
            preconditions="Hear the active harmony first; preserve melody and landing space."
            window="two beats minimum; full measure preferred"
            predecessors="dominant preparation; sustained chord" if "traversal" in slug else "harmonic rest or sustained note"
            successors="tonic landing; compatible traversal" if continuation else "next chord or contrasting answer"
            db.execute("INSERT OR REPLACE INTO phrase_musical_dna VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (phrase_id,length,count,count/length,start,end,target,function,role,register,contour,energy,chromatic,resolution,continuation,min_duration,preferred_duration,travel,string_sets,fret_range,shifts,"melody rest or sustained tone",preconditions,window,predecessors,successors,"tonic root/third/fifth","matching chord tone",'bluegrass/jazz crossover: provisional','needs_review'))
        for slug, rows in REALIZATIONS.items():
            phrase_id=db.execute("SELECT id FROM phrases WHERE slug=?",(slug,)).fetchone()[0]
            for measure,string_set,min_fret,max_fret in rows:
                db.execute("INSERT OR IGNORE INTO phrase_realizations(phrase_id,slug,source_measure_start,source_measure_end,string_set,min_fret,max_fret,note_count,is_source_fingering,review_status) VALUES (?,?,?,?,?,?,?,8,1,'needs_review')",
                           (phrase_id,f"{slug}-m{measure}",measure,measure,string_set,min_fret,max_fret))
        for source,destination,kind,context,route,entry,exit_state,rhythm,confidence,evidence in RELATIONSHIPS:
            source_id=db.execute("SELECT id FROM phrases WHERE slug=?",(source,)).fetchone()[0]
            destination_id=db.execute("SELECT id FROM phrases WHERE slug=?",(destination,)).fetchone()[0]
            db.execute("INSERT OR IGNORE INTO phrase_relationships(source_phrase_id,destination_phrase_id,relationship_type,harmonic_context,physical_route,entry_compatibility,exit_compatibility,rhythmic_compatibility,confidence,evidence,review_status,user_approval) VALUES (?,?,?,?,?,?,?,?,?,?,'needs_review','pending')",
                       (source_id,destination_id,kind,context,route,entry,exit_state,rhythm,confidence,evidence))
        return {name: db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in ("phrase_corpora","phrases","phrase_realizations","phrase_musical_dna","phrase_relationships")}


def export_phrase_graph(database: Path, output_dir: Path = REPO_ROOT / "analysis") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with connect(database) as db:
        for filename, query in (
            ("phrase_corpus_catalog.csv", "SELECT * FROM v_phrase_corpus_catalog ORDER BY corpus,slug"),
            ("phrase_musical_dna.csv", "SELECT * FROM v_phrase_musical_dna ORDER BY slug"),
            ("phrase_relationship_graph.csv", "SELECT * FROM v_phrase_relationship_graph ORDER BY source_phrase,destination_phrase"),
        ):
            rows=list(db.execute(query))
            with (output_dir/filename).open("w",newline="",encoding="utf-8") as handle:
                writer=csv.writer(handle); writer.writerow(rows[0].keys() if rows else ("no_rows",)); writer.writerows(tuple(row) for row in rows)
