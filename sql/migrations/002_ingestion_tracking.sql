ALTER TABLE tunes ADD COLUMN import_status TEXT NOT NULL DEFAULT 'canonical'
  CHECK(import_status IN ('canonical','accepted','provisional','proposed','archived','external','needs_review'));
ALTER TABLE systems ADD COLUMN import_status TEXT NOT NULL DEFAULT 'canonical'
  CHECK(import_status IN ('canonical','accepted','provisional','proposed','archived','external','needs_review'));
ALTER TABLE teachable_moments ADD COLUMN import_status TEXT NOT NULL DEFAULT 'canonical'
  CHECK(import_status IN ('canonical','accepted','provisional','proposed','archived','external','needs_review'));
ALTER TABLE lenses ADD COLUMN import_status TEXT NOT NULL DEFAULT 'canonical'
  CHECK(import_status IN ('canonical','accepted','provisional','proposed','archived','external','needs_review'));
ALTER TABLE learner_needs ADD COLUMN import_status TEXT NOT NULL DEFAULT 'canonical'
  CHECK(import_status IN ('canonical','accepted','provisional','proposed','archived','external','needs_review'));
ALTER TABLE content_items ADD COLUMN import_status TEXT NOT NULL DEFAULT 'canonical'
  CHECK(import_status IN ('canonical','accepted','provisional','proposed','archived','external','needs_review'));

CREATE TABLE import_file_log (
  id INTEGER PRIMARY KEY, repository_path TEXT NOT NULL UNIQUE, content_hash TEXT NOT NULL,
  disposition TEXT NOT NULL CHECK(disposition IN ('imported','skipped','needs_review')),
  reason TEXT NOT NULL, imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE review_candidates (
  id INTEGER PRIMARY KEY, entity_type TEXT NOT NULL, entity_slug TEXT NOT NULL,
  reason TEXT NOT NULL, source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'needs_review' CHECK(status IN ('needs_review','accepted','rejected')),
  UNIQUE(entity_type,entity_slug,reason)
);
CREATE TABLE play_this_candidate_details (
  content_item_id INTEGER PRIMARY KEY REFERENCES content_items(id) ON DELETE CASCADE,
  playable_seed TEXT NOT NULL, immediate_opening_action TEXT NOT NULL,
  likely_loop_ending TEXT NOT NULL, complete_script_exists INTEGER NOT NULL CHECK(complete_script_exists IN (0,1)),
  part_2_status TEXT NOT NULL CHECK(part_2_status IN ('none','proposed','complete')),
  source_evidence TEXT NOT NULL
);

CREATE VIEW v_incomplete_play_this_candidates AS
SELECT ci.slug,ci.title,ln.name AS learner_need,pt.playable_seed,pt.immediate_opening_action,
       pt.likely_loop_ending,pt.complete_script_exists,pt.part_2_status,pt.source_evidence
FROM play_this_candidate_details pt JOIN content_items ci ON ci.id=pt.content_item_id
LEFT JOIN learner_needs ln ON ln.id=ci.learner_need_id
WHERE pt.complete_script_exists=0 OR pt.part_2_status='proposed';
CREATE VIEW v_needs_review_records AS
SELECT entity_type,entity_slug,reason,status FROM review_candidates WHERE status='needs_review';
