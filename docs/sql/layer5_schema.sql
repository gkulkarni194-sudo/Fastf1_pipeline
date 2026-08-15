-- Layer 5: Strategy Optimization Schema

CREATE TABLE IF NOT EXISTS strategy_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_simulation_context_id UUID,
    status VARCHAR(50) NOT NULL,
    algorithm VARCHAR(50) NOT NULL,
    objective VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    config_hash VARCHAR(64) NOT NULL,
    strategy_schema_version VARCHAR(10) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS strategy_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_run_id UUID NOT NULL REFERENCES strategy_runs(id) ON DELETE CASCADE,
    asset_type VARCHAR(50) NOT NULL,
    storage_path TEXT NOT NULL,
    file_format VARCHAR(10) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    row_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS strategy_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_run_id UUID NOT NULL REFERENCES strategy_runs(id) ON DELETE CASCADE,
    strategy_hash VARCHAR(64) NOT NULL,
    rank INTEGER NOT NULL,
    objective_score FLOAT NOT NULL,
    race_time FLOAT,
    mean_race_time FLOAT,
    std_race_time FLOAT,
    p05_race_time FLOAT,
    p50_race_time FLOAT,
    p95_race_time FLOAT,
    is_pareto_optimal BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS strategy_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_hash VARCHAR(64) UNIQUE NOT NULL,
    strategy_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
