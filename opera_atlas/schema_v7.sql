-- Migration 7: source observations lacking validated time/venue.
-- Staging is not the public performance catalog.
CREATE TABLE staged_recite (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    production_url TEXT NOT NULL,
    work_title TEXT NOT NULL,
    venue_name TEXT NOT NULL,
    city TEXT NOT NULL,
    local_date TEXT NOT NULL CHECK(length(local_date)=10),
    evidence_fingerprint TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'needs_time'
        CHECK(state IN ('needs_time','ready_for_review','discarded')),
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id,production_url,work_title,venue_name,city,local_date)
);
CREATE INDEX idx_staged_recite_state ON staged_recite(state,source_id);
