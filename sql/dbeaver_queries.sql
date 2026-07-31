-- PLAY THIS READINESS
SELECT * FROM v_play_this_readiness ORDER BY title;

-- CURRICULUM GRAPH
SELECT * FROM v_content_curriculum_graph ORDER BY from_title, relationship_type, sequence;

-- TEACHABLE-MOMENT LENSES (there is deliberately no global primary lens)
SELECT * FROM v_teachable_moment_lenses ORDER BY teachable_moment, relationship_type, lens;

-- MISSING CONTENT AND ASSETS
SELECT * FROM v_missing_scripts;
SELECT * FROM v_missing_visual_plans;
SELECT * FROM v_missing_renderer_implementations;
SELECT * FROM v_missing_exercise_assets;
SELECT * FROM v_missing_play_this_concepts;

-- PART 2 / PART 3 INDEPENDENCE GAPS
SELECT * FROM v_part_chain_gaps;

-- PROVENANCE AND EXTERNAL CLAIM CONFLICTS
SELECT * FROM v_source_provenance ORDER BY authority_level, title;
SELECT * FROM v_external_claim_conflicts ORDER BY source, claim_text;

-- REUSABLE SYSTEMS AND LEARNER-NEED COVERAGE
SELECT * FROM v_tune_system_reuse ORDER BY tune_count DESC, system;
SELECT * FROM v_learner_need_coverage ORDER BY content_count, name;

-- DATABASE HEALTH
PRAGMA foreign_keys;
PRAGMA foreign_key_check;
PRAGMA integrity_check;

-- SOURCE ROOTS AND FILE INVENTORY
SELECT * FROM v_source_roots ORDER BY root_key;
SELECT * FROM v_source_file_inventory ORDER BY root_key, relative_path;
SELECT * FROM v_exact_musical_data_files ORDER BY root_key, relative_path;
SELECT * FROM v_duplicate_source_hashes ORDER BY file_count DESC;
SELECT * FROM v_proposed_source_packages ORDER BY title;
SELECT * FROM v_unresolved_package_groupings ORDER BY title;
SELECT * FROM v_source_parse_support ORDER BY root_key, extension;
SELECT * FROM v_missing_source_files;
SELECT * FROM v_changed_source_files;
SELECT * FROM v_stale_source_extractions;
