# F1 Strategy Simulator API

This document details the REST API for the F1 Strategy Simulator pipeline (Layer 6).

## Base URL
`/api/v1/`

## Philosophy
- **Asynchronous Execution:** Layers 4 and 5 (Simulation and Optimization) are computationally heavy. They use a standard Job API (`POST` to queue, `GET` to poll status).
- **Stateless Integration:** The frontend should never speak directly to PostgreSQL/Supabase.
- **Errors:** Handled universally via `f1_pipeline.api.middleware.errors`, yielding a standard `{"error": {"code": "...", "message": "..."}}` envelope.

## Endpoints

### Metadata & Discovery
- `GET /health` : API Liveness
- `GET /health/dependencies` : DB/Pipeline check
- `GET /seasons` : List of processed seasons
- `GET /events?season={s}` : Events in season
- `GET /sessions?season={s}&event={e}`
- `GET /drivers?season={s}&event={e}`

### Physics (Layer 3)
- `GET /physics/parameters?season={s}&event={e}&session={ses}&driver={d}` : Fetches derived aero/tyre parameters.

### Simulation (Layer 4)
- `POST /simulations` : Submits a job. Returns `{ "job_id": "...", "status": "queued" }`
- `GET /simulations/{job_id}` : Returns job status `queued|running|completed|failed`
- `GET /simulations/{job_id}/results` : Fetches simulation results.

### Optimization (Layer 5)
- `POST /optimizations` : Submits a strategy optimization job.
- `GET /optimizations/{job_id}` : Polls job status.
- `GET /optimizations/{job_id}/results` : Fetches best strategy.

### Experiments
- `GET /experiments/{id}` : Traces an optimization down to raw Layer 0 inputs for full reproducibility.
