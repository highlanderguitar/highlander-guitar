PRAGMA foreign_keys = ON;

CREATE TABLE tunes (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','active','retired')),
  source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE structural_units (
  id INTEGER PRIMARY KEY, tune_id INTEGER NOT NULL REFERENCES tunes(id) ON DELETE CASCADE,
  slug TEXT NOT NULL, title TEXT NOT NULL, sequence INTEGER NOT NULL CHECK(sequence > 0),
  description TEXT, UNIQUE(tune_id,slug), UNIQUE(tune_id,sequence)
);
CREATE TABLE systems (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL, description TEXT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','active','retired')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE system_occurrences (
  id INTEGER PRIMARY KEY, system_id INTEGER NOT NULL REFERENCES systems(id) ON DELETE RESTRICT,
  structural_unit_id INTEGER NOT NULL REFERENCES structural_units(id) ON DELETE CASCADE,
  location_label TEXT, evidence TEXT, UNIQUE(system_id,structural_unit_id,location_label)
);
CREATE TABLE teachable_moments (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL, description TEXT NOT NULL,
  system_id INTEGER REFERENCES systems(id) ON DELETE SET NULL,
  structural_unit_id INTEGER REFERENCES structural_units(id) ON DELETE SET NULL,
  source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','active','deferred','retired')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE lenses (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL,
  authority TEXT NOT NULL CHECK(authority IN ('highlander','external','synthesis'))
);
CREATE TABLE teachable_moment_lenses (
  teachable_moment_id INTEGER NOT NULL REFERENCES teachable_moments(id) ON DELETE CASCADE,
  lens_id INTEGER NOT NULL REFERENCES lenses(id) ON DELETE RESTRICT,
  relationship_type TEXT NOT NULL CHECK(relationship_type IN ('active','referenced','prerequisite','deferred')),
  notes TEXT, PRIMARY KEY(teachable_moment_id,lens_id,relationship_type)
);
CREATE TABLE learner_needs (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL
);
CREATE TABLE content_items (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
  content_type TEXT NOT NULL CHECK(content_type IN ('play_this','lesson','article','exercise','reference')),
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','planned','ready','published','retired')),
  tune_id INTEGER REFERENCES tunes(id) ON DELETE SET NULL,
  learner_need_id INTEGER REFERENCES learner_needs(id) ON DELETE RESTRICT,
  source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT,
  renderer_path TEXT, visual_plan TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE content_teachable_moments (
  content_item_id INTEGER NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
  teachable_moment_id INTEGER NOT NULL REFERENCES teachable_moments(id) ON DELETE RESTRICT,
  sequence INTEGER NOT NULL CHECK(sequence > 0),
  PRIMARY KEY(content_item_id,teachable_moment_id), UNIQUE(content_item_id,sequence)
);
CREATE TABLE play_this_scripts (
  id INTEGER PRIMARY KEY, content_item_id INTEGER NOT NULL UNIQUE REFERENCES content_items(id) ON DELETE CASCADE,
  opening_text TEXT NOT NULL CHECK(opening_text LIKE 'PLAY THIS%'),
  body_text TEXT NOT NULL, closing_hook TEXT NOT NULL CHECK(length(trim(closing_hook)) > 0),
  learner_need_id INTEGER NOT NULL REFERENCES learner_needs(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','review','ready','published')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE play_this_layers (
  id INTEGER PRIMARY KEY, content_item_id INTEGER NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
  part_number INTEGER NOT NULL CHECK(part_number BETWEEN 1 AND 3), title TEXT NOT NULL,
  independent_content_item_id INTEGER REFERENCES content_items(id) ON DELETE RESTRICT,
  independent_script_id INTEGER REFERENCES play_this_scripts(id) ON DELETE RESTRICT,
  is_independently_playable INTEGER NOT NULL DEFAULT 0 CHECK(is_independently_playable IN (0,1)),
  is_independently_loopable INTEGER NOT NULL DEFAULT 0 CHECK(is_independently_loopable IN (0,1)),
  UNIQUE(content_item_id,part_number),
  CHECK(part_number = 1 OR (is_independently_playable=1 AND is_independently_loopable=1 AND independent_content_item_id IS NOT NULL AND independent_script_id IS NOT NULL))
);
CREATE TABLE content_relationships (
  id INTEGER PRIMARY KEY,
  from_content_item_id INTEGER NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
  to_content_item_id INTEGER NOT NULL REFERENCES content_items(id) ON DELETE RESTRICT,
  relationship_type TEXT NOT NULL CHECK(relationship_type IN ('prerequisite','part_2','part_3','references','extends','returns_to_seed')),
  sequence INTEGER, notes TEXT, UNIQUE(from_content_item_id,to_content_item_id,relationship_type),
  CHECK(from_content_item_id <> to_content_item_id)
);
CREATE TABLE visual_assets (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, asset_type TEXT NOT NULL,
  content_item_id INTEGER REFERENCES content_items(id) ON DELETE CASCADE,
  teachable_moment_id INTEGER REFERENCES teachable_moments(id) ON DELETE CASCADE,
  repository_path TEXT, status TEXT NOT NULL DEFAULT 'missing' CHECK(status IN ('missing','planned','ready','verified')),
  provenance_source_id INTEGER REFERENCES sources(id) ON DELETE RESTRICT,
  CHECK(content_item_id IS NOT NULL OR teachable_moment_id IS NOT NULL)
);
CREATE TABLE exercises (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
  content_item_id INTEGER REFERENCES content_items(id) ON DELETE CASCADE,
  teachable_moment_id INTEGER REFERENCES teachable_moments(id) ON DELETE CASCADE,
  instructions TEXT NOT NULL, tab_path TEXT, notation_path TEXT, audio_path TEXT, backing_track_path TEXT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','ready','retired')),
  CHECK(content_item_id IS NOT NULL OR teachable_moment_id IS NOT NULL)
);
CREATE TABLE sources (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
  source_type TEXT NOT NULL, authority_level TEXT NOT NULL CHECK(authority_level IN ('canonical','highlander','external','synthesis','unresolved')),
  citation TEXT NOT NULL, repository_path TEXT UNIQUE, content_hash TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE source_claims (
  id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  claim_text TEXT NOT NULL, claim_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'unreviewed' CHECK(status IN ('unreviewed','accepted','rejected','conflict')),
  is_canonical INTEGER NOT NULL DEFAULT 0 CHECK(is_canonical IN (0,1)),
  conflicts_with_claim_id INTEGER REFERENCES source_claims(id) ON DELETE RESTRICT,
  teachable_moment_id INTEGER REFERENCES teachable_moments(id) ON DELETE SET NULL,
  UNIQUE(source_id,claim_text)
);

CREATE INDEX idx_structural_units_tune ON structural_units(tune_id);
CREATE INDEX idx_occurrences_system ON system_occurrences(system_id);
CREATE INDEX idx_tm_system ON teachable_moments(system_id);
CREATE INDEX idx_tm_lenses_lens ON teachable_moment_lenses(lens_id);
CREATE INDEX idx_content_tune ON content_items(tune_id);
CREATE INDEX idx_content_tm_moment ON content_teachable_moments(teachable_moment_id);
CREATE INDEX idx_relationship_to ON content_relationships(to_content_item_id);
CREATE INDEX idx_claims_status ON source_claims(status);

CREATE VIEW v_teachable_moment_lenses AS
SELECT tm.slug AS teachable_moment_slug, tm.title AS teachable_moment, l.slug AS lens_slug,
       l.name AS lens, tml.relationship_type, tml.notes
FROM teachable_moment_lenses tml
JOIN teachable_moments tm ON tm.id=tml.teachable_moment_id JOIN lenses l ON l.id=tml.lens_id;

CREATE VIEW v_play_this_readiness AS
SELECT ci.slug, ci.title, ci.status,
       CASE WHEN ps.id IS NOT NULL THEN 1 ELSE 0 END AS has_script,
       CASE WHEN ps.opening_text LIKE 'PLAY THIS%' THEN 1 ELSE 0 END AS valid_opening,
       CASE WHEN ps.learner_need_id IS NOT NULL THEN 1 ELSE 0 END AS has_closing_need,
       CASE WHEN COUNT(ctm.teachable_moment_id)>0 THEN 1 ELSE 0 END AS has_ordered_moments,
       CASE WHEN ci.visual_plan IS NOT NULL THEN 1 ELSE 0 END AS has_visual_plan,
       CASE WHEN ci.renderer_path IS NOT NULL THEN 1 ELSE 0 END AS has_renderer
FROM content_items ci LEFT JOIN play_this_scripts ps ON ps.content_item_id=ci.id
LEFT JOIN content_teachable_moments ctm ON ctm.content_item_id=ci.id
WHERE ci.content_type='play_this' GROUP BY ci.id;

CREATE VIEW v_content_curriculum_graph AS
SELECT a.slug AS from_slug, a.title AS from_title, cr.relationship_type,
       b.slug AS to_slug, b.title AS to_title, cr.sequence, cr.notes
FROM content_relationships cr JOIN content_items a ON a.id=cr.from_content_item_id
JOIN content_items b ON b.id=cr.to_content_item_id;
CREATE VIEW v_missing_scripts AS SELECT slug,title FROM content_items ci WHERE content_type='play_this' AND NOT EXISTS (SELECT 1 FROM play_this_scripts s WHERE s.content_item_id=ci.id);
CREATE VIEW v_missing_visual_plans AS SELECT slug,title FROM content_items WHERE content_type='play_this' AND visual_plan IS NULL;
CREATE VIEW v_missing_renderer_implementations AS SELECT slug,title,renderer_path FROM content_items WHERE content_type='play_this' AND renderer_path IS NULL;
CREATE VIEW v_missing_exercise_assets AS
SELECT slug,title,CASE WHEN tab_path IS NULL THEN 1 ELSE 0 END AS missing_tab,
 CASE WHEN notation_path IS NULL THEN 1 ELSE 0 END AS missing_notation,
 CASE WHEN audio_path IS NULL THEN 1 ELSE 0 END AS missing_audio,
 CASE WHEN backing_track_path IS NULL THEN 1 ELSE 0 END AS missing_backing_track FROM exercises
WHERE tab_path IS NULL OR notation_path IS NULL OR audio_path IS NULL OR backing_track_path IS NULL;
CREATE VIEW v_part_chain_gaps AS
SELECT ci.slug,pl.part_number,pl.title FROM play_this_layers pl JOIN content_items ci ON ci.id=pl.content_item_id
WHERE pl.part_number>1 AND (pl.independent_content_item_id IS NULL OR pl.independent_script_id IS NULL OR pl.is_independently_playable=0 OR pl.is_independently_loopable=0);
CREATE VIEW v_external_claim_conflicts AS
SELECT s.slug AS source_slug,s.title AS source,sc.claim_text,sc.status,sc.conflicts_with_claim_id
FROM source_claims sc JOIN sources s ON s.id=sc.source_id WHERE s.authority_level='external' AND sc.status IN ('unreviewed','conflict');
CREATE VIEW v_tune_system_reuse AS
SELECT sys.slug AS system_slug,sys.name AS system,COUNT(DISTINCT su.tune_id) AS tune_count,COUNT(so.id) AS occurrence_count
FROM systems sys LEFT JOIN system_occurrences so ON so.system_id=sys.id
LEFT JOIN structural_units su ON su.id=so.structural_unit_id GROUP BY sys.id;
CREATE VIEW v_learner_need_coverage AS
SELECT ln.slug,ln.name,COUNT(ci.id) AS content_count FROM learner_needs ln
LEFT JOIN content_items ci ON ci.learner_need_id=ln.id GROUP BY ln.id;
CREATE VIEW v_missing_play_this_concepts AS
SELECT tm.slug,tm.title FROM teachable_moments tm
WHERE tm.status='active' AND NOT EXISTS (SELECT 1 FROM content_teachable_moments ctm JOIN content_items ci ON ci.id=ctm.content_item_id WHERE ctm.teachable_moment_id=tm.id AND ci.content_type='play_this');
CREATE VIEW v_source_provenance AS
SELECT s.slug,s.title,s.source_type,s.authority_level,s.citation,s.repository_path,s.content_hash,
 COUNT(sc.id) AS claim_count FROM sources s LEFT JOIN source_claims sc ON sc.source_id=s.id GROUP BY s.id;
