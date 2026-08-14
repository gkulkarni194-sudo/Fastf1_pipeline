from __future__ import annotations

import numpy as np
import pandas as pd

from f1_pipeline.physics.aero.drag_model import drag_force
from f1_pipeline.physics.aero.downforce_model import downforce
from f1_pipeline.physics.aero.estimator import estimate_drag, estimate_downforce
from f1_pipeline.physics.cornering.lateral_model import infer_corner_radius, lateral_acceleration_from_radius
from f1_pipeline.physics.diagnostics import regression_diagnostics
from f1_pipeline.physics.longitudinal.force_model import effective_wheel_power, longitudinal_force_balance
from f1_pipeline.physics.longitudinal.resistance_model import rolling_resistance_force
from f1_pipeline.physics.tyres.estimator import estimate_tyre_degradation
from f1_pipeline.physics.uncertainty import confidence_interval


def _config() -> dict:
    return {
        "constants": {
            "air_density": {"value": 1.225, "unit": "kg/m^3", "provenance": "assumed"},
            "vehicle_mass_reference": {"value": 800.0, "unit": "kg", "provenance": "assumed"},
            "gravity": {"value": 9.80665, "unit": "m/s^2", "provenance": "configured"},
            "rolling_resistance_reference": {"value": 0.012, "unit": "dimensionless", "provenance": "assumed"},
        },
        "fitting": {"confidence_level": 0.95},
        "filtering": {"min_speed_ms": 20.0, "coast_throttle_max": 5.0, "full_throttle_threshold": 95.0, "exclude_braking": True},
        "models": {
            "drag": {"min_samples": 20, "max_rmse": 100.0, "minimum_r_squared": 0.1, "cda_bounds": [0.1, 3.5]},
            "downforce": {"min_samples": 20, "cla_bounds": [0.1, 10.0]},
            "tyres": {"min_samples": 5, "max_rmse": 1.0, "minimum_r_squared": 0.1, "degradation_bounds": [-0.5, 1.5]},
        },
    }


def test_drag_equation() -> None:
    force = drag_force(np.array([50.0]), air_density=1.225, effective_drag_parameter=1.6)
    assert force[0] == pytest_approx(2450.0, 1e-9)


def test_downforce_equation() -> None:
    force = downforce(np.array([40.0]), air_density=1.25, effective_downforce_parameter=5.0)
    assert force[0] == 5000.0


def test_drag_estimator_recovers_known_cda() -> None:
    cfg = _config()
    speed = np.linspace(25.0, 75.0, 80)
    cda = 1.45
    mass = 800.0
    accel = -drag_force(speed, air_density=1.225, effective_drag_parameter=cda) / mass
    df = pd.DataFrame({"speed_ms": speed, "acceleration_longitudinal": accel, "throttle_percent": 0.0, "brake_active": False})
    result = estimate_drag(df, cfg)
    assert result.status == "accepted"
    assert result.parameters[0].value == pytest_approx(cda, 0.03)
    assert "drag_coefficient" in result.identifiability.non_identifiable_parameters


def test_downforce_insufficient_data_without_lateral_column() -> None:
    result = estimate_downforce(pd.DataFrame({"speed_ms": [50.0] * 30}), _config())
    assert result.status == "insufficient_data"


def test_longitudinal_force_and_power() -> None:
    rolling = rolling_resistance_force(rolling_resistance_coefficient=0.01, mass_kg=800.0, gravity=10.0)
    force = longitudinal_force_balance(np.array([2.0]), mass_kg=800.0, drag_force_n=np.array([400.0]), rolling_force_n=rolling)
    assert force[0] == 2080.0
    assert effective_wheel_power(force, np.array([50.0]))[0] == 104000.0


def test_lateral_acceleration_and_radius() -> None:
    accel = lateral_acceleration_from_radius(np.array([50.0]), np.array([100.0]))
    assert accel[0] == 25.0
    radius = infer_corner_radius(np.array([50.0]), np.array([25.0]))
    assert radius[0] == 100.0


def test_tyre_degradation_recovers_known_coefficient() -> None:
    cfg = _config()
    age = np.arange(1, 16)
    lap_time = 90.0 + 0.08 * age + 0.01 * np.arange(1, 16)
    laps = pd.DataFrame({"tyre_age": age, "lap_time_seconds": lap_time, "lap_number": np.arange(1, 16)})
    result = estimate_tyre_degradation(laps, cfg)
    assert result.status in {"accepted", "warning"}
    assert result.parameters[0].value == pytest_approx(0.08, 0.03)


def test_confidence_interval() -> None:
    low, high = confidence_interval(10.0, 1.0, 0.95)
    assert low < 10.0 < high


def test_residual_diagnostics() -> None:
    diagnostics = regression_diagnostics(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 2.0]), rows_input=3)
    assert diagnostics.rmse is not None
    assert diagnostics.sample_count == 3


def pytest_approx(value: float, tolerance: float):
    import pytest

    return pytest.approx(value, abs=tolerance)
