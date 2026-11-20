-- Migration 3: preserve the exact event URL for human review and relinking.
ALTER TABLE source_events ADD COLUMN source_url TEXT;
CREATE INDEX idx_reviews_state ON reconciliation_reviews(state);
