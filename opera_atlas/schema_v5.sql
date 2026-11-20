-- Version 5: append-only, manually verified performance status transitions.
CREATE TABLE performance_status_history (
    id INTEGER PRIMARY KEY,
    performance_id INTEGER NOT NULL REFERENCES performances(id),
    previous_status TEXT NOT NULL CHECK(previous_status IN
        ('announced','confirmed','postponed','cancelled')),
    new_status TEXT NOT NULL CHECK(new_status IN
        ('announced','confirmed','postponed','cancelled')),
    source_url TEXT NOT NULL CHECK(length(trim(source_url)) > 0),
    reason TEXT NOT NULL CHECK(length(trim(reason)) > 0),
    decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(previous_status != new_status)
);
CREATE INDEX idx_performance_status_history
    ON performance_status_history(performance_id, decided_at);
