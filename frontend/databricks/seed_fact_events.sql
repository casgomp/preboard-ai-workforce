-- fact_events seed (PLAN_PR15 B5/R2). Not part of seed_data.sql's INSERT OVERWRITE
-- pattern for the same reason question_misses is kept out of it: OVERWRITE wipes
-- every table it touches on every re-run, which would destroy this table's whole
-- purpose (a running history of changes) right along with any misses logged since
-- the demo started. Run once, by hand, after seed_data.sql and setup_tables.sql.
-- Safe-ish to re-run — plain INSERT appends rather than overwriting, so a second
-- run doubles these six rows rather than corrupting anything; just don't do it
-- mid-demo if you care about the feed's exact contents.
--
-- Timestamps are spread across each employee's countdown (current_timestamp()
-- minus an interval), not bunched at one moment — a flat cluster would make the
-- candidate dashboard's "recent changes" feed (B5) look like nothing happened
-- until five minutes ago, which is the opposite of the story it exists to tell.
INSERT INTO fact_events (event_id, employee_id, fact_key, previous_value, new_value, source_system, event_timestamp) VALUES
('EVT-E001-01','E001','employee_account',NULL,'READY','Identity Management', current_timestamp() - INTERVAL 5 DAYS),
('EVT-E001-02','E001','software_access',NULL,'READY','Access Management', current_timestamp() - INTERVAL 4 DAYS),
('EVT-E001-03','E001','badge_status',NULL,'READY','Facilities Access', current_timestamp() - INTERVAL 3 DAYS),
('EVT-E001-04','E001','welcome_meeting',NULL,'READY','Manager Workspace', current_timestamp() - INTERVAL 2 DAYS),
('EVT-E001-05','E001','laptop_status',NULL,'READY','IT Asset Management', current_timestamp() - INTERVAL 1 DAYS),
('EVT-E002-01','E002','badge_status','READY','DELAYED','Facilities Access', current_timestamp() - INTERVAL 1 DAYS);
