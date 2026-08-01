CREATE TABLE source_roots (
  id INTEGER PRIMARY KEY, root_key TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
  root_kind TEXT NOT NULL CHECK(root_kind IN ('external_library','repository_relative')),
  configured_path TEXT NOT NULL, resolved_absolute_path TEXT,
  is_repository_relative INTEGER NOT NULL CHECK(is_repository_relative IN (0,1)),
  is_machine_local INTEGER NOT NULL CHECK(is_machine_local IN (0,1)),
  is_writable INTEGER NOT NULL DEFAULT 0 CHECK(is_writable IN (0,1)),
  is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
  tracked_in_git INTEGER NOT NULL DEFAULT 0 CHECK(tracked_in_git IN (0,1)),
  availability_status TEXT NOT NULL CHECK(availability_status IN ('available','unavailable','inaccessible','unverified')),
  last_verified_at TEXT, notes TEXT
);
CREATE TABLE source_inventory_runs (
  id INTEGER PRIMARY KEY, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, completed_at TEXT,
  mode TEXT NOT NULL CHECK(mode IN ('fast','full')), status TEXT NOT NULL CHECK(status IN ('running','complete','failed')),
  roots_scanned INTEGER NOT NULL DEFAULT 0, files_seen INTEGER NOT NULL DEFAULT 0,
  new_files INTEGER NOT NULL DEFAULT 0, changed_files INTEGER NOT NULL DEFAULT 0,
  missing_files INTEGER NOT NULL DEFAULT 0, unchanged_files INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE source_files (
  id INTEGER PRIMARY KEY, source_root_id INTEGER NOT NULL REFERENCES source_roots(id) ON DELETE RESTRICT,
  relative_path TEXT NOT NULL, normalized_path TEXT NOT NULL, resolved_absolute_path TEXT,
  extension TEXT NOT NULL, media_type TEXT NOT NULL, file_size INTEGER NOT NULL CHECK(file_size>=0),
  modified_time TEXT NOT NULL, current_sha256 TEXT, likely_content_type TEXT NOT NULL,
  exact_musical_data INTEGER NOT NULL CHECK(exact_musical_data IN (0,1)),
  parse_support_status TEXT NOT NULL CHECK(parse_support_status IN ('supported','partial','unsupported')),
  provenance TEXT NOT NULL, copyright_status TEXT NOT NULL DEFAULT 'unknown',
  review_status TEXT NOT NULL DEFAULT 'unreviewed' CHECK(review_status IN ('unreviewed','needs_review','accepted','rejected')),
  missing_status TEXT NOT NULL DEFAULT 'present' CHECK(missing_status IN ('present','missing','unresolved')),
  first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(source_root_id,normalized_path)
);
CREATE TABLE source_file_hashes (
  id INTEGER PRIMARY KEY, source_file_id INTEGER NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
  sha256 TEXT NOT NULL, file_size INTEGER NOT NULL, modified_time TEXT NOT NULL,
  inventory_run_id INTEGER NOT NULL REFERENCES source_inventory_runs(id) ON DELETE RESTRICT,
  observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(source_file_id,sha256)
);
CREATE TABLE source_inventory_events (
  id INTEGER PRIMARY KEY, inventory_run_id INTEGER NOT NULL REFERENCES source_inventory_runs(id) ON DELETE CASCADE,
  source_file_id INTEGER REFERENCES source_files(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL CHECK(event_type IN ('new','changed','missing','unchanged','duplicate','unsupported','root_unavailable')),
  details TEXT NOT NULL
);
CREATE TABLE source_packages (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL, package_type TEXT NOT NULL,
  preferred_exact_file_id INTEGER REFERENCES source_files(id) ON DELETE SET NULL,
  preferred_visual_file_id INTEGER REFERENCES source_files(id) ON DELETE SET NULL,
  preferred_audio_file_id INTEGER REFERENCES source_files(id) ON DELETE SET NULL,
  confidence TEXT NOT NULL CHECK(confidence IN ('high','medium','low')),
  review_status TEXT NOT NULL CHECK(review_status IN ('proposed','needs_review','accepted','rejected'))
);
CREATE TABLE source_package_files (
  source_package_id INTEGER NOT NULL REFERENCES source_packages(id) ON DELETE CASCADE,
  source_file_id INTEGER NOT NULL REFERENCES source_files(id) ON DELETE RESTRICT,
  relationship_type TEXT NOT NULL, PRIMARY KEY(source_package_id,source_file_id)
);
CREATE TABLE source_parse_attempts (
  id INTEGER PRIMARY KEY, source_file_id INTEGER NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
  source_hash TEXT NOT NULL, parser_name TEXT NOT NULL, status TEXT NOT NULL, attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  details TEXT
);
CREATE TABLE source_extraction_candidates (
  id INTEGER PRIMARY KEY, source_package_id INTEGER NOT NULL REFERENCES source_packages(id) ON DELETE CASCADE,
  candidate_type TEXT NOT NULL, readiness TEXT NOT NULL CHECK(readiness IN ('ready','partial','blocked','needs_review')),
  reason TEXT NOT NULL, source_hash TEXT, review_status TEXT NOT NULL DEFAULT 'needs_review'
);

CREATE INDEX idx_source_files_hash ON source_files(current_sha256);
CREATE INDEX idx_source_files_extension ON source_files(extension);
CREATE VIEW v_source_roots AS SELECT root_key,display_name,root_kind,configured_path,resolved_absolute_path,availability_status,last_verified_at FROM source_roots;
CREATE VIEW v_source_file_inventory AS
SELECT r.root_key,f.relative_path,f.extension,f.media_type,f.file_size,f.modified_time,f.current_sha256,
 f.likely_content_type,f.exact_musical_data,f.parse_support_status,f.review_status,f.missing_status
FROM source_files f JOIN source_roots r ON r.id=f.source_root_id;
CREATE VIEW v_exact_musical_data_files AS SELECT * FROM v_source_file_inventory WHERE exact_musical_data=1;
CREATE VIEW v_unsupported_source_files AS SELECT * FROM v_source_file_inventory WHERE parse_support_status='unsupported';
CREATE VIEW v_missing_source_files AS SELECT * FROM v_source_file_inventory WHERE missing_status<>'present';
CREATE VIEW v_changed_source_files AS
SELECT r.root_key,f.relative_path,e.event_type,e.details,run.id AS inventory_run_id,run.completed_at
FROM source_inventory_events e JOIN source_inventory_runs run ON run.id=e.inventory_run_id
JOIN source_files f ON f.id=e.source_file_id JOIN source_roots r ON r.id=f.source_root_id
WHERE e.event_type='changed' AND run.id=(SELECT MAX(id) FROM source_inventory_runs);
CREATE VIEW v_duplicate_source_hashes AS
SELECT current_sha256,COUNT(*) AS file_count,GROUP_CONCAT(relative_path,' | ') AS files
FROM source_files WHERE current_sha256 IS NOT NULL GROUP BY current_sha256 HAVING COUNT(*)>1;
CREATE VIEW v_proposed_source_packages AS
SELECT p.slug,p.title,p.package_type,p.confidence,p.review_status,COUNT(pf.source_file_id) AS file_count
FROM source_packages p LEFT JOIN source_package_files pf ON pf.source_package_id=p.id GROUP BY p.id;
CREATE VIEW v_unresolved_package_groupings AS SELECT * FROM v_proposed_source_packages WHERE review_status='needs_review';
CREATE VIEW v_source_parse_support AS SELECT root_key,extension,parse_support_status,COUNT(*) AS file_count FROM v_source_file_inventory GROUP BY root_key,extension,parse_support_status;
CREATE VIEW v_extraction_readiness AS
SELECT p.slug,p.title,c.candidate_type,c.readiness,c.reason,c.review_status FROM source_extraction_candidates c JOIN source_packages p ON p.id=c.source_package_id;
CREATE VIEW v_stale_source_extractions AS
SELECT r.root_key,f.relative_path,a.parser_name,a.source_hash,f.current_sha256
FROM source_parse_attempts a JOIN source_files f ON f.id=a.source_file_id JOIN source_roots r ON r.id=f.source_root_id
WHERE a.source_hash<>f.current_sha256;
