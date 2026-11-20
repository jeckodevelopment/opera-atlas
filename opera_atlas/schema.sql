PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY CHECK (version > 0),
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    composer TEXT,
    title_normalized TEXT NOT NULL CHECK (length(trim(title_normalized)) > 0),
    genre TEXT NOT NULL DEFAULT 'opera',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_works_title ON works(title_normalized);

CREATE TABLE IF NOT EXISTS work_aliases (
    id INTEGER PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    alias TEXT NOT NULL CHECK (length(trim(alias)) > 0),
    alias_normalized TEXT NOT NULL,
    UNIQUE (work_id, alias_normalized)
);

CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    kind TEXT NOT NULL CHECK (kind IN ('theatre','foundation','festival','circuit','other')),
    official_url TEXT,
    UNIQUE (name, kind)
);

CREATE TABLE IF NOT EXISTS venues (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    municipality TEXT NOT NULL,
    province TEXT,
    region TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'IT',
    address TEXT,
    latitude REAL CHECK (latitude BETWEEN -90 AND 90),
    longitude REAL CHECK (longitude BETWEEN -180 AND 180),
    verification_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (verification_status IN ('pending','verified','inactive')),
    CHECK ((latitude IS NULL) = (longitude IS NULL)),
    UNIQUE (name, municipality, region)
);

CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    starts_on TEXT,
    ends_on TEXT,
    UNIQUE (organization_id, name)
);

CREATE TABLE IF NOT EXISTS productions (
    id INTEGER PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(id),
    name TEXT,
    season_id INTEGER REFERENCES seasons(id),
    production_key TEXT UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS production_organizations (
    production_id INTEGER NOT NULL REFERENCES productions(id) ON DELETE CASCADE,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    role TEXT NOT NULL DEFAULT 'organizer',
    PRIMARY KEY (production_id, organization_id, role)
);

CREATE TABLE IF NOT EXISTS performances (
    id INTEGER PRIMARY KEY,
    production_id INTEGER NOT NULL REFERENCES productions(id),
    venue_id INTEGER NOT NULL REFERENCES venues(id),
    starts_at TEXT NOT NULL CHECK (
        length(starts_at) = 25 AND
        substr(starts_at, 20, 1) IN ('+','-') AND
        substr(starts_at, 23, 1) = ':'
    ),
    timezone TEXT NOT NULL DEFAULT 'Europe/Rome',
    status TEXT NOT NULL DEFAULT 'announced'
        CHECK (status IN ('announced','confirmed','postponed','cancelled')),
    ticket_url TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (production_id, venue_id, starts_at)
);
CREATE INDEX IF NOT EXISTS idx_performances_time ON performances(starts_at);
CREATE INDEX IF NOT EXISTS idx_performances_venue ON performances(venue_id);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    official_url TEXT NOT NULL UNIQUE,
    calendar_url TEXT,
    source_kind TEXT NOT NULL DEFAULT 'html'
        CHECK (source_kind IN ('html','json','api','pdf','other')),
    access_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (access_status IN ('pending','approved','blocked','inactive')),
    checked_at TEXT,
    fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    external_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL CHECK (length(fingerprint) > 0),
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_id, external_id, fingerprint)
);

CREATE TABLE IF NOT EXISTS performance_sources (
    performance_id INTEGER NOT NULL REFERENCES performances(id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    source_url TEXT NOT NULL,
    PRIMARY KEY (performance_id, source_id, source_url)
);
