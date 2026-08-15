# Frontend Integration Guide

This guide is for frontend developers integrating the UI with the F1 Strategy Simulator Python backend.

## Flow of Data

1. **Configuration Stage**
   - The UI mounts. Call `GET /api/v1/seasons` to populate a dropdown.
   - User selects a season. Call `GET /api/v1/events?season=X`.
   - User selects event, session, driver. Call `GET /api/v1/physics/parameters` to fetch the default car setups inferred from Layer 3.

2. **Simulation Stage**
   - User clicks "Run Simulation".
   - The UI constructs a `Scenario` object (JSON) and sends `POST /api/v1/simulations`.
   - The API returns a `job_id`.
   - **Important:** The UI must poll `GET /api/v1/simulations/{job_id}` every ~2 seconds.
   - Once `status == "completed"`, call `GET /api/v1/simulations/{job_id}/results`.

3. **Optimization Stage**
   - User clicks "Optimize Strategy".
   - UI sends constraints to `POST /api/v1/optimizations`.
   - Poll job ID.
   - Fetch results and render the Pareto frontier or timeline graph.

## Error Handling
Always check the `error` root key in non-2xx responses. Do not crash the UI on 500s; display the `error.message`.
