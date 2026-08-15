-- Layer 6: API and Job Management Schema

CREATE TABLE IF NOT EXISTS pipeline_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(50) NOT NULL, -- e.g., 'simulation', 'optimization'
    status VARCHAR(50) NOT NULL,   -- e.g., 'queued', 'running', 'completed', 'failed', 'cancelled'
    progress FLOAT DEFAULT 0.0,
    payload JSONB,
    result_reference UUID,         -- Reference to the output ID (e.g., simulation_run_id)
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_pipeline_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pipeline_jobs_updated_at ON pipeline_jobs;
CREATE TRIGGER trg_pipeline_jobs_updated_at
BEFORE UPDATE ON pipeline_jobs
FOR EACH ROW
EXECUTE FUNCTION update_pipeline_jobs_updated_at();
