-- Layer 2: Feature extraction tables
-- Idempotent — safe to run multiple times.

-- -----------------------------------------------------------------
-- feature_runs: tracks each Layer 2 pipeline execution
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feature_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_normalization_run_id UUID,
    status          TEXT NOT NULL DEFAULT 'started',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    code_version    TEXT,
    config_hash     TEXT,
    feature_schema_version TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feature_runs_status
    ON feature_runs (status);

CREATE INDEX IF NOT EXISTS idx_feature_runs_source
    ON feature_runs (source_normalization_run_id);

-- -----------------------------------------------------------------
-- feature_assets: one row per derived-feature Parquet file
-- -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feature_assets (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_run_id              UUID REFERENCES feature_runs(id),
    source_canonical_asset_id   UUID,
    season                      INT NOT NULL,
    event_name                  TEXT NOT NULL,
    session_type                TEXT NOT NULL,
    driver_code                 TEXT,
    asset_type                  TEXT NOT NULL,
    storage_path                TEXT NOT NULL,
    file_format                 TEXT NOT NULL DEFAULT 'parquet',
    checksum                    TEXT NOT NULL,
    row_count                   INT,
    feature_schema_version      TEXT NOT NULL,
    config_hash                 TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feature_assets_run
    ON feature_assets (feature_run_id);

CREATE INDEX IF NOT EXISTS idx_feature_assets_source
    ON feature_assets (source_canonical_asset_id);

CREATE INDEX IF NOT EXISTS idx_feature_assets_lookup
    ON feature_assets (source_canonical_asset_id, feature_schema_version, config_hash);
