-- PostgreSQL schema for durable Guardian storage.
-- Take a verified pg_dump backup before applying. All statements are additive.
BEGIN;

CREATE TABLE IF NOT EXISTS guardian_state (
    id INTEGER PRIMARY KEY,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS guardian_logs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(16) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_guardian_logs_created_at ON guardian_logs(created_at);
CREATE INDEX IF NOT EXISTS ix_guardian_logs_level ON guardian_logs(level);
CREATE INDEX IF NOT EXISTS ix_guardian_logs_event_type ON guardian_logs(event_type);

CREATE TABLE IF NOT EXISTS guardian_issues (
    issue_id VARCHAR(120) PRIMARY KEY,
    status VARCHAR(32) NOT NULL,
    severity VARCHAR(24) NOT NULL,
    detected_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_guardian_issues_status ON guardian_issues(status);
CREATE INDEX IF NOT EXISTS ix_guardian_issues_severity ON guardian_issues(severity);
CREATE INDEX IF NOT EXISTS ix_guardian_issues_detected_at ON guardian_issues(detected_at);

CREATE TABLE IF NOT EXISTS guardian_patches (
    patch_id VARCHAR(120) PRIMARY KEY,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_guardian_patches_status ON guardian_patches(status);
CREATE INDEX IF NOT EXISTS ix_guardian_patches_created_at ON guardian_patches(created_at);

CREATE TABLE IF NOT EXISTS guardian_worker_heartbeats (
    worker_id VARCHAR(120) PRIMARY KEY,
    last_seen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    status VARCHAR(24) NOT NULL,
    last_cycle_at TIMESTAMP WITHOUT TIME ZONE NULL,
    details TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_guardian_worker_heartbeats_last_seen_at
    ON guardian_worker_heartbeats(last_seen_at);


-- One-time import ledger for legacy JSON backup bundles.
CREATE TABLE IF NOT EXISTS guardian_import_ledger (
    bundle_sha256 VARCHAR(64) PRIMARY KEY,
    imported_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    counts_json TEXT NOT NULL
);

COMMIT;
