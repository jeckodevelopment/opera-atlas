-- Version 6: non-destructive discrepancies between successive source snapshots.
CREATE TABLE IF NOT EXISTS source_snapshot_deltas (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    source_url TEXT NOT NULL,
    production_id INTEGER NOT NULL REFERENCES productions(id),
    old_external_ids TEXT NOT NULL CHECK(json_valid(old_external_ids)),
    new_external_ids TEXT NOT NULL CHECK(json_valid(new_external_ids)),
    state TEXT NOT NULL DEFAULT 'open' CHECK(state IN ('open','acknowledged')),
    detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TEXT,
    acknowledged_reason TEXT,
    UNIQUE(source_id,source_url,production_id,old_external_ids,new_external_ids)
);
CREATE INDEX IF NOT EXISTS idx_source_snapshot_deltas_state
    ON source_snapshot_deltas(state,source_id);
