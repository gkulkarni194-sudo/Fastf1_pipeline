# Layer 4: Simulation and Scenario Engine

Layer 4 answers "What happens under this scenario?". It runs deterministic and Monte Carlo simulations utilizing the physical parameters estimated in Layer 3 and the observed metrics from Layer 2.

## Scenario Definition

Simulations are driven by an immutable JSON `Scenario` definition which includes:
- Target session and driver (`season`, `event`, `session_type`, `driver_code`)
- Race parameters (`total_laps`, `starting_fuel_kg`)
- Strategy (`tyre_strategy`, `pit_stops`)
- Weather (`weather`)

## Components

- **SimulationEngine (`f1_pipeline.simulation.engine`)**: Core orchestrator of the lap-by-lap simulation loop.
- **MonteCarloRunner (`f1_pipeline.simulation.monte_carlo`)**: Wraps the deterministic engine to run N iterations, sampling parameter distributions.
- **Vehicle Models**: `LongitudinalModel` and `LateralModel` built on the parameters estimated in Layer 3 (CdA, ClA).
- **Environment Models**: `FuelModel`, `WeatherModel`, `TrackEvolutionModel` define lap-by-lap modifiers to lap time.
- **Tyre Models**: `TyreDegradationModel` and `TyreGripModel` apply compound-specific performance deltas based on stint age.

## Usage

```bash
python scripts/run_layer4_simulation.py --scenario data/scenarios/2024_bahrain_r_ver.json
```

Use `--monte-carlo` to run an ensemble simulation with sampled uncertainties.
