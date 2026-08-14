-- Layer 3: Physics inference and modeling tables
-- Idempotent; safe to run multiple times in Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS physics_runs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_feature_run_id   UUID REFERENCES feature_runs(id) ON DELETE SET NULL,
    status                  TEXT NOT NULL DEFAULT 'started'
                                CHECK (status IN ('started', 'success', 'failed')),
    started_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at            TIMESTAMPTZ,
    error_message           TEXT,
    code_version            TEXT,
    config_hash             TEXT,
    physics_schema_version  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_physics_runs_status
    ON physics_runs(status);

CREATE INDEX IF NOT EXISTS idx_physics_runs_source
    ON physics_runs(source_feature_run_id);

CREATE TABLE IF NOT EXISTS physics_assets (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_feature_asset_id     UUID REFERENCES feature_assets(id) ON DELETE SET NULL,
    season                      INT NOT NULL,
    event_name                  TEXT NOT NULL,
    session_type                TEXT NOT NULL,
    driver_code                 TEXT,
    asset_type                  TEXT NOT NULL,
    storage_path                TEXT NOT NULL,
    file_format                 TEXT NOT NULL,
    checksum                    TEXT NOT NULL,
    row_count                   INT,
    physics_schema_version      TEXT NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_physics_assets_source
    ON physics_assets(source_feature_asset_id);

CREATE INDEX IF NOT EXISTS idx_physics_assets_lookup
    ON physics_assets(season, event_name, session_type, driver_code, asset_type);

CREATE TABLE IF NOT EXISTS physics_parameters (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    physics_run_id              UUID REFERENCES physics_runs(id) ON DELETE CASCADE,
    parameter_name              TEXT NOT NULL,
    value                       DOUBLE PRECISION,
    unit                        TEXT NOT NULL,
    standard_error              DOUBLE PRECISION,
    confidence_interval_low     DOUBLE PRECISION,
    confidence_interval_high    DOUBLE PRECISION,
    model_name                  TEXT NOT NULL,
    model_version               TEXT NOT NULL,
    sample_count                INT,
    status                      TEXT NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_physics_parameters_run
    ON physics_parameters(physics_run_id);
