-- ==========================================================================
-- Layer 1 Schema — Canonical Data / Normalization
-- Run this in the Supabase SQL Editor.
-- All statements are idempotent (IF NOT EXISTS).
-- ==========================================================================

-- --------------------------------------------------------------------------
-- normalization_runs: tracks each Layer 1 normalization execution
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS normalization_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_ingestion_run_id UUID REFERENCES ingestion_runs(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'started'
                        CHECK (status IN ('started', 'success', 'failed')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    code_version    TEXT,
    config_hash     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_norm_runs_source
    ON normalization_runs(source_ingestion_run_id);
CREATE INDEX IF NOT EXISTS idx_norm_runs_status
    ON normalization_runs(status);

-- --------------------------------------------------------------------------
-- canonical_assets: metadata for each canonical dataset produced by Layer 1
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS canonical_assets (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    normalization_run_id  UUID REFERENCES normalization_runs(id) ON DELETE CASCADE,
    source_asset_id       UUID REFERENCES raw_data_assets(id) ON DELETE SET NULL,
    season                INTEGER NOT NULL,
    event_name            TEXT NOT NULL,
    session_type          TEXT NOT NULL,
    driver_code           TEXT,
    asset_type            TEXT NOT NULL,
    storage_path          TEXT NOT NULL,
    file_format           TEXT NOT NULL DEFAULT 'parquet',
    checksum              TEXT NOT NULL,
    row_count             INTEGER,
    schema_version        TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_canon_assets_run
    ON canonical_assets(normalization_run_id);
CREATE INDEX IF NOT EXISTS idx_canon_assets_source
    ON canonical_assets(source_asset_id);
CREATE INDEX IF NOT EXISTS idx_canon_assets_lookup
    ON canonical_assets(season, event_name, session_type, driver_code, asset_type);
CREATE INDEX IF NOT EXISTS idx_canon_assets_schema
    ON canonical_assets(schema_version);
