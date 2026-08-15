# Layer 3 Physics Inference

Layer 3 consumes only Layer 2 feature assets from `data/interim/features` and writes physics artifacts to `data/processed/physics`. It does not download FastF1 data, mutate Layer 0/1/2 assets, simulate races, optimize strategy, or choose tyres.

## Models

### Aerodynamic Drag

Equation:

```text
F_drag = 0.5 * rho * CdA * v^2
```

The fitted parameter is `effective_drag_parameter` (`CdA`, m^2). `Cd` and frontal area are not separately identifiable from these observations. The estimator uses coastdown-like samples: finite speed/longitudinal acceleration, minimum speed, low throttle when available, non-braking, and negative longitudinal acceleration.

### Downforce

Equation:

```text
F_downforce = 0.5 * rho * ClA * v^2
```

The fitted parameter is `effective_downforce_parameter` (`ClA`, m^2). This runs only when lateral acceleration data has sufficient high-load samples. It is an effective lateral-capacity proxy, not independently measured `Cl` or frontal area.

### Longitudinal Force

Equation:

```text
m*a = F_drive - F_drag - F_rolling - F_other
F_rolling = Crr * m * g
```

The output is `effective_drive_force` and `effective_wheel_power`. It does not claim true engine power, drivetrain efficiency, or torque curve recovery. Rolling resistance is recorded as an assumed/configured coefficient unless upstream data can identify it.

### Tyres

Degradation is a controlled linear descriptive model:

```text
lap_time = baseline + degradation * tyre_age + controls + residual
```

Controls are included when Layer 2 provides them, such as lap number, average speed, throttle fraction, brake fraction, DRS fraction, or track status. The output is an estimated descriptive coefficient, not a causal tyre parameter.

Grip is reported as an effective lateral-grip proxy from high observed lateral acceleration. Aerodynamic load, banking, kerbs, and driver margin are not separated.

### Cornering

When radius is available:

```text
a_lat = v^2 / R
```

If radius is unavailable, telemetry-derived speed and lateral acceleration are used only for an effective radius consistency proxy. Official corner numbers are not inferred from Layer 2 heuristic corners.

## Assumptions And Provenance

Constants are configured in `configs/physics.yaml` and carry provenance: `observed`, `configured`, `assumed`, or `estimated`. Defaults such as air density, vehicle mass, gravity, and rolling resistance are not presented as observed F1-specific measurements.

## Diagnostics And Acceptance

Each model records sample counts, row exclusions, residuals, RMSE, MAE, R-squared where meaningful, residual mean/std, warnings, and convergence status. Status can be `accepted`, `warning`, `rejected`, `insufficient_data`, or `failed`; thresholds live in `configs/physics.yaml`.

## Outputs

Per driver:

```text
data/processed/physics/{season}/{event_slug}/{session_type}/{driver_code}/
  aero_parameters.json
  longitudinal_parameters.json
  tyre_parameters.json
  cornering_parameters.json
  model_diagnostics.json
  predictions.parquet
  residuals.parquet
  metadata.json
```

Session summary:

```text
data/processed/physics/{season}/{event_slug}/{session_type}/session_physics_summary.json
```

Large prediction and residual datasets are stored as Parquet. Supabase stores run metadata, asset metadata, and parameter estimates only.
