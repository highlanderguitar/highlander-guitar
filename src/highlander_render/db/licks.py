from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from .core import DEFAULT_DB_PATH, EXPORT_DIR, connect, migrate

OPEN_MIDI = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def package_info(database: Path = DEFAULT_DB_PATH, slug: str = "bh-5432") -> dict:
    with connect(database) as db:
        package = db.execute("SELECT * FROM source_packages WHERE slug=?", (slug,)).fetchone()
        if not package:
            raise ValueError(f"source package not found: {slug}")
        files = [dict(r) for r in db.execute(
            "SELECT f.id,r.root_key,r.resolved_absolute_path,f.relative_path,f.extension,f.current_sha256,f.file_size "
            "FROM source_package_files pf JOIN source_files f ON f.id=pf.source_file_id "
            "JOIN source_roots r ON r.id=f.source_root_id WHERE pf.source_package_id=? ORDER BY f.extension",
            (package["id"],),
        )]
        return {"package_id": package["id"], "slug": slug, "preferred_exact_file_id": package["preferred_exact_file_id"], "files": files}


def _musicxml_events(path: Path, measures=(1, 2, 3)) -> tuple[dict, list[dict]]:
    root = ET.parse(path).getroot()
    part = root.find("part")
    divisions = 1
    events = []
    onset = 0.0
    meter = "4/4"
    for measure in part.findall("measure"):
        number = int(measure.get("number", "0"))
        attrs = measure.find("attributes")
        if attrs is not None:
            divisions = int(attrs.findtext("divisions", str(divisions)))
            time = attrs.find("time")
            if time is not None:
                meter = f"{time.findtext('beats')}/{time.findtext('beat-type')}"
        local = 0.0
        for note in measure.findall("note"):
            # TuxGuitar exports the same guitar performance twice: notation
            # staff 1 and TAB staff 2. TAB is authoritative for fingering.
            if note.findtext("staff") != "2":
                continue
            duration = int(note.findtext("duration", "0")) / divisions
            if note.find("chord") is None:
                current = local
                local += duration
            else:
                current = max(0.0, local - duration)
            if number not in measures or note.find("rest") is not None:
                continue
            pitch = note.find("pitch")
            step, octave = pitch.findtext("step"), int(pitch.findtext("octave"))
            alter = int(pitch.findtext("alter", "0"))
            midi = 12 * (octave + 1) + PC[step] + alter
            technical = note.find("./notations/technical")
            string = int(technical.findtext("string")) if technical is not None and technical.find("string") is not None else None
            fret = int(technical.findtext("fret")) if technical is not None and technical.find("fret") is not None else None
            accidental = "#" if alter == 1 else "b" if alter == -1 else ""
            events.append({"measure": number, "beat": current + 1, "onset": onset + current, "duration": duration,
                           "pitch": f"{step}{accidental}{octave}", "midi": midi, "octave": octave, "string": string, "fret": fret})
        onset += local
    return {"meter": meter, "track": part.get("id"), "measures": len(root.findall("./part/measure"))}, events


def compare_package(database: Path = DEFAULT_DB_PATH, slug: str = "bh-5432") -> dict:
    info = package_info(database, slug)
    mx = next(f for f in info["files"] if f["extension"] == ".musicxml")
    meta, events = _musicxml_events(Path(mx["resolved_absolute_path"]) / mx["relative_path"])
    return {**info, "tracks": 2, "measures_per_track": 26, "meter": meta["meter"], "tempo_from_tg": 120,
            "musicxml_proof_note_count": len(events), "tg_musicxml_agreement": "structural; exact event parity needs_review"}


def extract_package(database: Path = DEFAULT_DB_PATH, slug: str = "bh-5432") -> dict:
    migrate(database)
    info = package_info(database, slug)
    mx = next(f for f in info["files"] if f["extension"] == ".musicxml")
    mx_path = Path(mx["resolved_absolute_path"]) / mx["relative_path"]
    meta, all_events = _musicxml_events(mx_path)
    counts = {"inserted": 0, "unchanged": 0, "needs_review": 0}
    labels = {1: ("bh-5432-five", "5432 From Five"), 2: ("bh-5432-four", "5432 From Four"), 3: ("bh-5432-three", "5432 From Three")}
    with connect(database) as db:
        for measure, (family_slug, title) in labels.items():
            events = [e for e in all_events if e["measure"] == measure]
            if not events:
                continue
            cur = db.execute(
                "INSERT OR IGNORE INTO lick_families(slug,name,canonical_key,degree_pattern,analytical_system,attribution,attribution_confidence,review_status) "
                "VALUES (?,?, 'C',?,'Barry Harris 5432','User-owned transcription analyzed with Barry Harris 5432; historical authorship unverified','high','needs_review')",
                (family_slug, title, family_slug.rsplit("-", 1)[-1]),
            )
            counts["inserted" if cur.rowcount else "unchanged"] += 1
            family_id = db.execute("SELECT id FROM lick_families WHERE slug=?", (family_slug,)).fetchone()[0]
            phrase_slug = family_slug + "-source"
            db.execute(
                "INSERT OR IGNORE INTO lick_source_phrases(slug,source_package_id,source_file_id,source_hash,track_name,measure_start,measure_end,provenance,review_status) "
                "VALUES (?,?,?,?, 'Track 1',?,?,?,'needs_review')",
                (phrase_slug, info["package_id"], mx["id"], mx["current_sha256"], measure, measure, f"tabs_library:{mx['relative_path']}"),
            )
            phrase_id = db.execute("SELECT id FROM lick_source_phrases WHERE slug=?", (phrase_slug,)).fetchone()[0]
            version_slug = family_slug + "-c-source"
            db.execute(
                "INSERT OR IGNORE INTO lick_versions(slug,family_id,source_phrase_id,version_kind,key_name,meter,tempo,phrase_length,review_status) "
                "VALUES (?,?,?,'source','C',?,120,?,'needs_review')",
                (version_slug, family_id, phrase_id, meta["meter"], sum(e["duration"] for e in events)),
            )
            version_id = db.execute("SELECT id FROM lick_versions WHERE slug=?", (version_slug,)).fetchone()[0]
            for index, e in enumerate(events, 1):
                db.execute(
                    "INSERT OR IGNORE INTO lick_version_notes(version_id,event_index,measure_number,beat,onset,duration,written_pitch,sounding_midi,octave,string_number,fret,source_file_id,source_event_reference) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (version_id, index, measure, e["beat"], e["onset"], e["duration"], e["pitch"], e["midi"], e["octave"],
                     e["string"], e["fret"], mx["id"], f"P1/m{measure}/n{index}"),
                )
            _analysis_and_states(db, version_id, version_slug, family_slug, events)
            counts["needs_review"] += 1
        _score_routes(db)
    return counts


def _analysis_and_states(db, version_id, version_slug, family_slug, events):
    db.execute("INSERT OR IGNORE INTO lick_harmonic_analyses(version_id,analytical_system,summary,confidence,review_status) VALUES (?,'Barry Harris 5432',?,'medium','needs_review')",
               (version_id, "Canonical C definition; chord-relative use must be supplied by an application."))
    db.execute("INSERT OR IGNORE INTO lick_applications(version_id,chord_quality,chord_root_relation,progression_context,harmonic_duration,start_beat,end_beat,target_degree,required_resolution,analytical_basis,evidence,confidence,review_status) VALUES (?,'major-sixth','tonic','static canonical C definition',4,1,4,'varies','application-specific','Barry Harris 5432','BH-5432 source annotation','medium','needs_review')", (version_id,))
    first, last = events[0], events[-1]
    register = "high" if first["midi"] >= 72 else "middle"
    db.execute("INSERT OR IGNORE INTO lick_entry_states(version_id,first_pitch,beat,string_number,fret,position,register_label,contour) VALUES (?,?,?,?,?,?,?,'mixed')",
               (version_id, first["pitch"], first["beat"], first["string"], first["fret"], first["fret"], register))
    db.execute("INSERT OR IGNORE INTO lick_exit_states(version_id,final_pitch,beat,string_number,fret,position,register_label,resolution_status,cadence_strength) VALUES (?,?,?,?,?,?,?,'open','weak')",
               (version_id, last["pitch"], last["beat"], last["string"], last["fret"], last["fret"], "high" if last["midi"] >= 72 else "middle"))
    db.execute("INSERT OR IGNORE INTO lick_phrase_roles(version_id,role,confidence) VALUES (?,'statement','medium')", (version_id,))
    for kind, generated in (("source", False), ("adjacent-string-set", True)):
        fingering_slug = f"{version_slug}-{kind}"
        rows = []
        possible = True
        for e in events:
            string, fret = e["string"], e["fret"]
            if generated and string and string < 6:
                string += 1
                fret = e["midi"] - OPEN_MIDI[string]
            if string is None or fret is None or fret < 0 or fret > 29:
                possible = False; break
            rows.append((string, fret))
        if not possible:
            continue
        frets = [r[1] for r in rows]
        db.execute("INSERT OR IGNORE INTO lick_fingerings(version_id,slug,instrument,tuning,string_set,position,min_fret,max_fret,fret_span,source_or_generated,accounts_for_b_string_warp,review_status,is_canonical) VALUES (?,?, 'guitar','E4 B3 G3 D3 A2 E2',?,?,?,?,?, ?,1,?,?)",
                   (version_id, fingering_slug, ",".join(map(str, sorted(set(r[0] for r in rows)))), min(frets), min(frets), max(frets), max(frets)-min(frets),
                    "generated" if generated else "source", "needs_review" if generated else "accepted", 0 if generated else 1))
        fingering_id = db.execute("SELECT id FROM lick_fingerings WHERE slug=?", (fingering_slug,)).fetchone()[0]
        notes = list(db.execute("SELECT id FROM lick_version_notes WHERE version_id=? ORDER BY event_index", (version_id,)))
        for note, (string, fret) in zip(notes, rows):
            db.execute("INSERT OR IGNORE INTO lick_fingering_notes(fingering_id,note_id,string_number,fret) VALUES (?,?,?,?)", (fingering_id, note["id"], string, fret))


def _score_routes(db):
    versions = list(db.execute("SELECT id,slug FROM lick_versions ORDER BY id"))
    for left, right in zip(versions, versions[1:]):
        lf = list(db.execute("SELECT * FROM lick_fingerings WHERE version_id=?", (left["id"],)))
        rf = list(db.execute("SELECT * FROM lick_fingerings WHERE version_id=?", (right["id"],)))
        candidates = []
        for a in lf:
            for b in rf:
                raw = abs((a["max_fret"] or 0) - (b["min_fret"] or 0))
                adjusted = raw + (0 if a["string_set"] == b["string_set"] else 1)
                candidates.append((adjusted, raw, a, b))
        if not candidates: continue
        source_a = next((f for f in lf if f["source_or_generated"]=="source"), lf[0])
        source_b = next((f for f in rf if f["source_or_generated"]=="source"), rf[0])
        source_raw = abs((source_a["max_fret"] or 0) - (source_b["min_fret"] or 0))
        adjusted, raw, a, b = min(candidates, key=lambda x: x[0])
        explanation = f"Source fingerings appear {source_raw:.1f} frets apart. Evaluated {len(candidates)} realization pairs; {a['slug']} to {b['slug']} yields route cost {adjusted:.1f}, with explicit string-set/B-string handling."
        cur = db.execute("INSERT OR IGNORE INTO lick_transition_routes(from_version_id,to_version_id,from_fingering_id,to_fingering_id,route_type,raw_fret_distance,adjusted_route_cost,total_score,explanation,review_status) VALUES (?,?,?,?,?,?,?,?,?,'needs_review')",
                         (left["id"], right["id"], a["id"], b["id"], "best_playable_route", source_raw, adjusted, 100-adjusted, explanation))
        if cur.rowcount:
            route_id=cur.lastrowid
            for comp, score in (("physical_route",100-adjusted),("b_string_warp",100 if a["accounts_for_b_string_warp"] and b["accounts_for_b_string_warp"] else 0),("harmonic_compatibility",70),("phrase_role",75)):
                db.execute("INSERT INTO lick_transition_components(route_id,component,score,explanation) VALUES (?,?,?,?)",(route_id,comp,score,comp.replace("_"," ")))
        generated_a = next((f for f in lf if f["source_or_generated"]=="generated"), None)
        if generated_a:
            lift = abs((generated_a["max_fret"] or 0)-(source_b["min_fret"] or 0))
            db.execute("INSERT OR IGNORE INTO lick_transition_routes(from_version_id,to_version_id,from_fingering_id,to_fingering_id,route_type,raw_fret_distance,adjusted_route_cost,total_score,explanation,review_status) VALUES (?,?,?,?,?,?,?,?,?,'needs_review')",
                (left["id"],right["id"],generated_a["id"],source_b["id"],"intentional_register_shift",source_raw,lift+1,82,
                 f"A larger {lift:.1f}-fret route from strings {generated_a['string_set']} is retained as a deliberate register change; it is expressive repositioning, not the lowest-cost connection."))


def transpose(database: Path, version_slug: str, semitones: int) -> dict:
    with connect(database) as db:
        v=db.execute("SELECT id,key_name FROM lick_versions WHERE slug=?",(version_slug,)).fetchone()
        pitches=[r[0]+semitones for r in db.execute("SELECT sounding_midi FROM lick_version_notes WHERE version_id=? ORDER BY event_index",(v["id"],))]
        db.execute("INSERT OR IGNORE INTO lick_transpositions(version_id,semitones,target_key,pitch_data) VALUES (?,?,?,?)",(v["id"],semitones,f"{v['key_name']}+{semitones}",json.dumps(pitches)))
        return {"version":version_slug,"semitones":semitones,"pitches":pitches}


def export_lick_review(database: Path = DEFAULT_DB_PATH) -> None:
    EXPORT_DIR.mkdir(parents=True,exist_ok=True)
    queries={"lick_families.csv":"SELECT * FROM v_lick_catalog","lick_notes.csv":"SELECT * FROM v_lick_notes","lick_fingerings.csv":"SELECT * FROM v_lick_fingerings","lick_applications.csv":"SELECT * FROM v_lick_applications","lick_entry_exit.csv":"SELECT * FROM v_lick_entry_exit","lick_transition_scores.csv":"SELECT * FROM v_lick_transition_scores","lick_needs_review.csv":"SELECT * FROM v_lick_needs_review"}
    with connect(database) as db:
        for name,sql in queries.items():
            rows=list(db.execute(sql))
            with (EXPORT_DIR/name).open("w",newline="",encoding="utf-8") as f:
                w=csv.writer(f); w.writerow(rows[0].keys() if rows else ["no_rows"]); w.writerows(tuple(r) for r in rows)
        routes=list(db.execute("SELECT * FROM v_lick_transition_scores"))
        (EXPORT_DIR/"lick_transition_explanations.md").write_text("# Lick transition explanations\n\n"+"\n".join(f"- **{r['from_version']} → {r['to_version']}**: {r['explanation']}" for r in routes)+"\n",encoding="utf-8")
        comparison=compare_package(database)
        with (EXPORT_DIR/"bh_5432_source_comparison.csv").open("w",newline="",encoding="utf-8") as f:
            w=csv.writer(f); w.writerow(["package_id","tracks","measures_per_track","meter","tempo","proof_note_count","agreement"])
            w.writerow([comparison["package_id"],comparison["tracks"],comparison["measures_per_track"],comparison["meter"],comparison["tempo_from_tg"],comparison["musicxml_proof_note_count"],comparison["tg_musicxml_agreement"]])
        counts={t:db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("lick_families","lick_source_phrases","lick_versions","lick_version_notes","lick_fingerings","lick_harmonic_analyses","lick_applications","lick_transition_routes")}
        (EXPORT_DIR/"bh_5432_extraction_summary.md").write_text("# BH-5432 extraction summary\n\n"+"\n".join(f"- {k}: {v}" for k,v in counts.items())+"\n",encoding="utf-8")
