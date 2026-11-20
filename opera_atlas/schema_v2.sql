-- Migration 2: stable source identities and explicit human review of conflicts.
CREATE TABLE source_events (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    external_id TEXT NOT NULL CHECK(length(trim(external_id)) > 0),
    performance_id INTEGER REFERENCES performances(id),
    last_fingerprint TEXT NOT NULL CHECK(length(last_fingerprint) > 0),
    state TEXT NOT NULL DEFAULT 'linked' CHECK(state IN ('linked','review')),
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, external_id)
);
CREATE INDEX idx_source_events_performance ON source_events(performance_id);

CREATE TABLE reconciliation_reviews (
    id INTEGER PRIMARY KEY,
    source_event_id INTEGER NOT NULL REFERENCES source_events(id),
    reason TEXT NOT NULL CHECK(reason IN ('changed_identity','ambiguous_match')),
    proposed_production_id INTEGER NOT NULL REFERENCES productions(id),
    proposed_venue_id INTEGER NOT NULL REFERENCES venues(id),
    proposed_start TEXT NOT NULL,
    observed_fingerprint TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'open' CHECK(state IN ('open','resolved')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    UNIQUE(source_event_id, observed_fingerprint, proposed_production_id, proposed_venue_id, proposed_start)
);
