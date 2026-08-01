CREATE TABLE phrase_corpora(
  id INTEGER PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  review_status TEXT NOT NULL
);

CREATE TABLE phrases(
  id INTEGER PRIMARY KEY,
  corpus_id INTEGER NOT NULL REFERENCES phrase_corpora(id),
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  family TEXT NOT NULL,
  source_path TEXT NOT NULL,
  source_hash TEXT,
  source_track TEXT,
  measure_start INTEGER,
  measure_end INTEGER,
  source_lick_version_id INTEGER REFERENCES lick_versions(id),
  phrase_kind TEXT NOT NULL,
  review_status TEXT NOT NULL,
  user_approval TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE phrase_realizations(
  id INTEGER PRIMARY KEY,
  phrase_id INTEGER NOT NULL REFERENCES phrases(id) ON DELETE CASCADE,
  slug TEXT UNIQUE NOT NULL,
  source_measure_start INTEGER NOT NULL,
  source_measure_end INTEGER NOT NULL,
  string_set TEXT NOT NULL,
  min_fret INTEGER NOT NULL,
  max_fret INTEGER NOT NULL,
  note_count INTEGER NOT NULL,
  is_source_fingering INTEGER NOT NULL DEFAULT 1,
  review_status TEXT NOT NULL
);

CREATE TABLE phrase_musical_dna(
  phrase_id INTEGER PRIMARY KEY REFERENCES phrases(id) ON DELETE CASCADE,
  phrase_length_beats REAL NOT NULL,
  note_count INTEGER NOT NULL,
  rhythmic_density REAL NOT NULL,
  start_degree TEXT,
  end_degree TEXT,
  primary_target TEXT,
  harmonic_function TEXT NOT NULL,
  phrase_role TEXT NOT NULL,
  register_label TEXT NOT NULL,
  contour TEXT NOT NULL,
  energy TEXT NOT NULL,
  chromatic_intensity TEXT NOT NULL,
  resolution_strength TEXT NOT NULL,
  continuation_required INTEGER NOT NULL,
  minimum_harmonic_duration REAL NOT NULL,
  preferred_harmonic_duration REAL NOT NULL,
  physical_travel TEXT NOT NULL,
  string_sets TEXT NOT NULL,
  fret_range TEXT NOT NULL,
  shift_count INTEGER NOT NULL,
  entry_opportunity TEXT NOT NULL,
  musical_preconditions TEXT NOT NULL,
  opportunity_window TEXT NOT NULL,
  preferred_predecessors TEXT NOT NULL,
  preferred_successors TEXT NOT NULL,
  compatible_endings TEXT NOT NULL,
  compatible_beginnings TEXT NOT NULL,
  genre_confidence TEXT NOT NULL,
  review_status TEXT NOT NULL
);

CREATE TABLE phrase_relationships(
  id INTEGER PRIMARY KEY,
  source_phrase_id INTEGER NOT NULL REFERENCES phrases(id),
  destination_phrase_id INTEGER NOT NULL REFERENCES phrases(id),
  relationship_type TEXT NOT NULL,
  harmonic_context TEXT NOT NULL,
  physical_route TEXT NOT NULL,
  entry_compatibility TEXT NOT NULL,
  exit_compatibility TEXT NOT NULL,
  rhythmic_compatibility TEXT NOT NULL,
  confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
  evidence TEXT NOT NULL,
  review_status TEXT NOT NULL,
  user_approval TEXT NOT NULL DEFAULT 'pending',
  UNIQUE(source_phrase_id,destination_phrase_id,relationship_type,harmonic_context)
);

CREATE TABLE setlist_phrase_candidates(
  id INTEGER PRIMARY KEY,
  tune_id INTEGER REFERENCES tunes(id),
  tune_slug TEXT NOT NULL,
  section_label TEXT,
  measure_number INTEGER NOT NULL,
  beat REAL NOT NULL,
  preceding_chord TEXT,
  active_chord TEXT NOT NULL,
  following_chord TEXT,
  phrase_id INTEGER NOT NULL REFERENCES phrases(id),
  opportunity_window TEXT NOT NULL,
  musical_preconditions TEXT NOT NULL,
  available_duration REAL NOT NULL,
  required_transposition INTEGER NOT NULL,
  chord_relative_transformation TEXT NOT NULL,
  entry_note TEXT,
  exit_note TEXT,
  target_note TEXT,
  compatible_next_phrase_id INTEGER REFERENCES phrases(id),
  best_bh5432_phrase_id INTEGER REFERENCES phrases(id),
  physical_route TEXT NOT NULL,
  maximum_fret INTEGER NOT NULL,
  confidence REAL NOT NULL CHECK(confidence BETWEEN 0 AND 1),
  restriction TEXT NOT NULL,
  review_status TEXT NOT NULL,
  user_approval TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE phrase_review_decisions(
  id INTEGER PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  decision TEXT NOT NULL,
  reviewer_notes TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE VIEW v_phrase_corpus_catalog AS
SELECT c.slug AS corpus,p.slug,p.name,p.family,p.phrase_kind,p.measure_start,p.measure_end,p.review_status,p.user_approval
FROM phrases p JOIN phrase_corpora c ON c.id=p.corpus_id;

CREATE VIEW v_phrase_musical_dna AS
SELECT p.slug,p.family,d.* FROM phrase_musical_dna d JOIN phrases p ON p.id=d.phrase_id;

CREATE VIEW v_phrase_relationship_graph AS
SELECT a.slug AS source_phrase,b.slug AS destination_phrase,r.relationship_type,r.harmonic_context,
       r.physical_route,r.entry_compatibility,r.exit_compatibility,r.rhythmic_compatibility,
       r.confidence,r.evidence,r.review_status,r.user_approval
FROM phrase_relationships r JOIN phrases a ON a.id=r.source_phrase_id JOIN phrases b ON b.id=r.destination_phrase_id;
