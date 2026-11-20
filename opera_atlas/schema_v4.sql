-- Migration 4: operational audit trail for checked sources.
CREATE TABLE source_checks (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    url TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK(outcome IN
        ('success','not_modified','robots_blocked','robots_unavailable',
         'fetch_error','invalid_content','import_error')),
    status_code INTEGER,
    content_sha256 TEXT,
    bytes_received INTEGER CHECK(bytes_received IS NULL OR bytes_received >= 0),
    observed_count INTEGER,
    message TEXT,
    checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_source_checks_recent ON source_checks(source_id,checked_at DESC);
