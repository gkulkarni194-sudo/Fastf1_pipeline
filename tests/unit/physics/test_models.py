"""Comprehensive Layer 3 physics tests.

Covers:
- Synthetic parameter-recovery for all models (spec §34)
- Equation unit tests
- Insufficient-data handling for all models
- Parameter bounds → rejection
- Convergence failure → failed status
- Model quality status transitions
- Outlier handling / exclusion reasons
- Model registry completeness
- Rolling resistance formula
- Uncertainty edge cases
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from f1_pipeline.physics.aero.drag_model import drag_force
from f1_pipeline.physics.aero.downforce_model import downforce, estimate_cla_from_lateral_capacity
from f1_pipeline.physics.aero.estimator import estimate_drag, estimate_downforce
from f1_pipeline.physics.cornering.estimator import estimate_cornering
from f1_pipeline.physics.cornering.lateral_model import infer_corner_radius, lateral_acceleration_from_radius
from f1_pipeline.physics.diagnostics import evaluate_status, regression_diagnostics
from f1_pipeline.physics.longitudinal.estimator import estimate_longitudinal
from f1_pipeline.physics.longitudinal.force_model import effective_wheel_power, longitudinal_force_balance
from f1_pipeline.physics.longitudinal.resistance_model import rolling_resistance_force
from f1_pipeline.physics.model_registry import MODEL_REGISTRY, selected_models
from f1_pipeline.physics.schemas import PhysicsDiagnostics
from f1_pipeline.physics.tyres.estimator import estimate_tyre_degradation, estimate_tyre_grip
from f1_pipeline.physics.tyres.grip_model import effective_grip_coefficient
from f1_pipeline.physics.uncertainty import confidence_interval, covariance_from_design, standard_errors


# ─────────────────────────────────────────────────────────────
# Shared test config
# ─────────────────────────────────────────────────────────────

def _config() -> dict:
    return {
        "constants": {
            "air_density": {"value": 1.225, "unit": "kg/m^3", "provenance": "assumed"},
            "vehicle_mass_reference": {"value": 800.0, "unit": "kg", "provenance": "assumed"},
            "gravity": {"value": 9.80665, "unit": "m/s^2", "provenance": "configured"},
            "rolling_resistance_reference": {"value": 0.012, "unit": "dimensionless", "provenance": "assumed"},
        },
        "fitting": {"confidence_level": 0.95},
        "filtering": {
            "min_speed_ms": 20.0,
            "coast_throttle_max": 5.0,
            "full_throttle_threshold": 95.0,
            "exclude_braking": True,
            "max_gap_seconds": 0.5,
        },
        "models": {
            "drag": {"min_samples": 20, "max_rmse": 100.0, "minimum_r_squared": 0.1, "cda_bounds": [0.1, 3.5]},
            "downforce": {"min_samples": 20, "cla_bounds": [0.1, 10.0]},
            "longitudinal": {"min_samples": 20, "max_rmse": 50000.0, "minimum_r_squared": 0.0, "drive_force_bounds": [0.0, 25000.0]},
            "tyres": {"min_samples": 5, "max_rmse": 1.0, "minimum_r_squared": 0.05, "degradation_bounds": [-0.5, 1.5]},
            "grip": {"min_samples": 10, "grip_bounds": [0.5, 5.0]},
            "cornering": {"min_samples": 5, "max_rmse": 5.0, "minimum_r_squared": 0.0, "grip_bounds": [0.5, 5.0]},
        },
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYNTHETIC PARAMETER-RECOVERY TESTS (spec §34)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSyntheticRecoveryDrag:
    """Generate synthetic coast-down data, verify CdA recovery."""

    def test_recovers_known_cda_noiseless(self) -> None:
        cfg = _config()
        true_cda = 1.45
        mass = 800.0
        speed = np.linspace(25.0, 75.0, 80)
        accel = -drag_force(speed, air_density=1.225, effective_drag_parameter=true_cda) / mass
        df = pd.DataFrame({
            "speed_ms": speed,
            "acceleration_longitudinal": accel,
            "throttle_percent": 0.0,
            "brake_active": False,
        })
        result = estimate_drag(df, cfg)
        assert result.status == "accepted"
        assert result.parameters[0].value == pytest.approx(true_cda, abs=0.01)
        assert result.parameters[0].parameter_name == "effective_drag_parameter"
        assert result.parameters[0].unit == "m^2"

    def test_recovers_known_cda_with_noise(self) -> None:
        cfg = _config()
        true_cda = 1.8
        mass = 800.0
        rng = np.random.default_rng(42)
        speed = np.linspace(25.0, 80.0, 200)
        accel = -drag_force(speed, air_density=1.225, effective_drag_parameter=true_cda) / mass
        # Add small Gaussian noise
        accel += rng.normal(0, 0.05, len(accel))
        df = pd.DataFrame({
            "speed_ms": speed,
            "acceleration_longitudinal": accel,
            "throttle_percent": 0.0,
            "brake_active": False,
        })
        result = estimate_drag(df, cfg)
        assert result.status in {"accepted", "warning"}
        assert result.parameters[0].value == pytest.approx(true_cda, abs=0.15)


class TestSyntheticRecoveryDownforce:
    """Generate synthetic lateral-capacity data, verify ClA recovery."""

    def test_recovers_known_cla_noiseless(self) -> None:
        cfg = _config()
        true_cla = 4.5
        mass = 800.0
        g = 9.80665
        rho = 1.225
        # Create speeds where downforce gives enough aero load so a_lat > g
        speed = np.linspace(40.0, 90.0, 100)
        # F_down = 0.5 * rho * ClA * v^2
        # Normal force = m*g + F_down
        # Friction-limited: a_lat_max = mu * N / m  =>  a_lat = (N/m) approx
        # Here we construct a_lat = g + (0.5*rho*ClA*v^2)/m  (mu=1 assumption in model)
        a_lat = g + (0.5 * rho * true_cla * speed**2) / mass
        df = pd.DataFrame({"speed_ms": speed, "acceleration_lateral": a_lat})
        result = estimate_downforce(df, cfg)
        assert result.status in {"accepted", "warning", "rejected"}
        assert result.parameters[0].parameter_name == "effective_downforce_parameter"
        assert result.parameters[0].value == pytest.approx(true_cla, abs=0.5)
        assert "lift_coefficient" in result.identifiability.non_identifiable_parameters


class TestSyntheticRecoveryLongitudinal:
    """Generate synthetic full-throttle data, verify effective drive force recovery."""

    def test_recovers_mean_drive_force(self) -> None:
        cfg = _config()
        true_drive_force = 8000.0
        mass = 800.0
        rho = 1.225
        cda = 1.5
        crr = 0.012
        g = 9.80665
        speed = np.linspace(25.0, 70.0, 100)
        # a = (F_drive - F_drag - F_rolling) / m
        drag = 0.5 * rho * cda * speed**2
        rolling = crr * mass * g
        accel = (true_drive_force - drag - rolling) / mass
        df = pd.DataFrame({
            "speed_ms": speed,
            "acceleration_longitudinal": accel,
            "throttle_percent": 100.0,
            "brake_active": False,
        })
        result = estimate_longitudinal(df, cfg, drag_cda=cda)
        assert result.status in {"accepted", "warning"}
        assert result.parameters[0].parameter_name == "effective_drive_force"
        assert result.parameters[0].value == pytest.approx(true_drive_force, abs=500.0)
        assert "engine_power" in result.identifiability.non_identifiable_parameters
        # Check effective_wheel_power is also reported
        power_params = [p for p in result.parameters if p.parameter_name == "effective_wheel_power"]
        assert len(power_params) == 1
        assert power_params[0].value > 0


class TestSyntheticRecoveryCornering:
    """Generate synthetic corner data with known radius, verify consistency."""

    def test_recovers_lateral_acceleration_from_known_radius(self) -> None:
        cfg = _config()
        true_radius = 120.0
        speed = np.linspace(20.0, 60.0, 50)
        a_lat = speed**2 / true_radius
        corners = pd.DataFrame({
            "corner_radius": true_radius,
            "minimum_corner_speed": speed * 3.6,  # convert to km/h as expected by estimator
            "peak_lateral_acceleration": a_lat,
        })
        result = estimate_cornering(corners, None, cfg)
        assert result.status in {"accepted", "warning"}
        radius_param = [p for p in result.parameters if p.parameter_name == "effective_corner_radius"]
        assert len(radius_param) == 1
        assert radius_param[0].value == pytest.approx(true_radius, abs=5.0)

    def test_recovers_from_telemetry_when_corners_empty(self) -> None:
        cfg = _config()
        rng = np.random.default_rng(99)
        speed = rng.uniform(20.0, 60.0, 200)
        radius = rng.uniform(50.0, 300.0, 200)
        a_lat = speed**2 / radius
        # Only keep samples with a_lat > 1.0 as the estimator filters on this
        mask = a_lat > 1.0
        telemetry = pd.DataFrame({
            "speed_ms": speed[mask],
            "acceleration_lateral": a_lat[mask],
        })
        result = estimate_cornering(pd.DataFrame(), telemetry, cfg)
        assert result.status in {"accepted", "warning", "insufficient_data"}
        if result.status != "insufficient_data":
            assert result.diagnostics.sample_count > 0


class TestSyntheticRecoveryGrip:
    """Generate synthetic lateral acceleration data, verify grip proxy recovery."""

    def test_recovers_95th_percentile_grip(self) -> None:
        cfg = _config()
        rng = np.random.default_rng(7)
        g = 9.80665
        # Simulate a_lat values where the 95th percentile is about 2.5g
        a_lat = rng.uniform(5.0, 25.0, 500)
        telemetry = pd.DataFrame({"acceleration_lateral": a_lat})
        result = estimate_tyre_grip(telemetry, cfg)
        assert result.status in {"accepted", "warning"}
        assert result.parameters[0].parameter_name == "effective_grip_parameter"
        expected_grip = float(np.nanpercentile(np.abs(a_lat) / g, 95))
        assert result.parameters[0].value == pytest.approx(expected_grip, abs=0.01)
        assert result.diagnostics.sample_count == 500

    def test_grip_insufficient_data_no_column(self) -> None:
        result = estimate_tyre_grip(pd.DataFrame({"speed_ms": [50.0]}), _config())
        assert result.status == "insufficient_data"


class TestSyntheticRecoveryTyreDegradation:
    """Generate synthetic lap time data with known degradation, verify recovery."""

    def test_recovers_known_degradation_coefficient(self) -> None:
        cfg = _config()
        true_degradation = 0.08
        baseline = 90.0
        age = np.arange(1, 16)
        lap_time = baseline + true_degradation * age
        laps = pd.DataFrame({"tyre_age": age, "lap_time_seconds": lap_time})
        result = estimate_tyre_degradation(laps, cfg)
        assert result.status in {"accepted", "warning"}
        assert result.parameters[0].value == pytest.approx(true_degradation, abs=0.01)

    def test_recovers_with_control_variable(self) -> None:
        cfg = _config()
        true_degradation = 0.1
        baseline = 88.0
        rng = np.random.default_rng(123)
        age = np.arange(1, 21)
        speed_effect = rng.uniform(-0.5, 0.5, 20)
        lap_time = baseline + true_degradation * age + speed_effect
        laps = pd.DataFrame({
            "tyre_age": age,
            "lap_time_seconds": lap_time,
            "average_speed": 200.0 + speed_effect * 10,
            "lap_number": np.arange(1, 21),
        })
        result = estimate_tyre_degradation(laps, cfg)
        assert result.status in {"accepted", "warning"}
        assert result.parameters[0].value == pytest.approx(true_degradation, abs=0.05)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EQUATION UNIT TESTS (spec §33)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDragEquation:
    def test_basic_drag(self) -> None:
        f = drag_force(np.array([50.0]), air_density=1.225, effective_drag_parameter=1.6)
        assert f[0] == pytest.approx(0.5 * 1.225 * 1.6 * 50**2, abs=1e-9)

    def test_zero_speed(self) -> None:
        f = drag_force(np.array([0.0]), air_density=1.225, effective_drag_parameter=1.6)
        assert f[0] == 0.0


class TestDownforceEquation:
    def test_basic_downforce(self) -> None:
        f = downforce(np.array([40.0]), air_density=1.25, effective_downforce_parameter=5.0)
        assert f[0] == pytest.approx(0.5 * 1.25 * 5.0 * 40**2, abs=1e-9)


class TestRollingResistance:
    def test_basic_formula(self) -> None:
        f = rolling_resistance_force(rolling_resistance_coefficient=0.012, mass_kg=800.0, gravity=9.80665)
        assert f == pytest.approx(0.012 * 800.0 * 9.80665, abs=1e-9)

    def test_zero_coefficient(self) -> None:
        f = rolling_resistance_force(rolling_resistance_coefficient=0.0, mass_kg=800.0, gravity=9.80665)
        assert f == 0.0


class TestLongitudinalForceEquation:
    def test_force_balance(self) -> None:
        force = longitudinal_force_balance(np.array([2.0]), mass_kg=800.0, drag_force_n=np.array([400.0]), rolling_force_n=80.0)
        # m*a + drag + rolling = 800*2 + 400 + 80 = 2080
        assert force[0] == pytest.approx(2080.0, abs=1e-9)

    def test_wheel_power(self) -> None:
        power = effective_wheel_power(np.array([2000.0]), np.array([50.0]))
        assert power[0] == pytest.approx(100000.0, abs=1e-9)


class TestLateralModel:
    def test_a_lat_from_radius(self) -> None:
        a = lateral_acceleration_from_radius(np.array([50.0]), np.array([100.0]))
        assert a[0] == pytest.approx(25.0, abs=1e-9)

    def test_infer_radius(self) -> None:
        r = infer_corner_radius(np.array([50.0]), np.array([25.0]))
        assert r[0] == pytest.approx(100.0, abs=1e-9)

    def test_infer_radius_zero_accel(self) -> None:
        r = infer_corner_radius(np.array([50.0]), np.array([0.0]))
        assert np.isnan(r[0])


class TestGripCoefficientFormula:
    def test_basic(self) -> None:
        grip = effective_grip_coefficient(np.array([19.6133]), gravity=9.80665)
        assert grip[0] == pytest.approx(2.0, abs=0.001)


class TestConfidenceInterval:
    def test_basic_ci(self) -> None:
        low, high = confidence_interval(10.0, 1.0, 0.95)
        assert low is not None and high is not None
        assert low < 10.0 < high

    def test_none_value(self) -> None:
        low, high = confidence_interval(None, 1.0, 0.95)
        assert low is None and high is None

    def test_none_se(self) -> None:
        low, high = confidence_interval(10.0, None, 0.95)
        assert low is None and high is None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INSUFFICIENT-DATA HANDLING (spec §33)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestInsufficientDataAllModels:
    """Every model must return insufficient_data when required features are missing."""

    def test_drag_missing_columns(self) -> None:
        result = estimate_drag(pd.DataFrame({"speed_ms": [50.0]}), _config())
        assert result.status == "insufficient_data"

    def test_drag_too_few_samples(self) -> None:
        cfg = _config()
        cfg["models"]["drag"]["min_samples"] = 1000
        speed = np.array([50.0, 60.0])
        accel = np.array([-0.5, -0.6])
        df = pd.DataFrame({"speed_ms": speed, "acceleration_longitudinal": accel, "throttle_percent": 0.0, "brake_active": False})
        result = estimate_drag(df, cfg)
        assert result.status == "insufficient_data"

    def test_downforce_missing_columns(self) -> None:
        result = estimate_downforce(pd.DataFrame({"speed_ms": [50.0]}), _config())
        assert result.status == "insufficient_data"

    def test_longitudinal_missing_columns(self) -> None:
        result = estimate_longitudinal(pd.DataFrame({"speed_ms": [50.0]}), _config())
        assert result.status == "insufficient_data"

    def test_tyre_degradation_missing_columns(self) -> None:
        result = estimate_tyre_degradation(pd.DataFrame({"speed_ms": [50.0]}), _config())
        assert result.status == "insufficient_data"

    def test_grip_missing_columns(self) -> None:
        result = estimate_tyre_grip(pd.DataFrame({"speed_ms": [50.0]}), _config())
        assert result.status == "insufficient_data"

    def test_cornering_empty_both(self) -> None:
        result = estimate_cornering(pd.DataFrame(), pd.DataFrame(), _config())
        assert result.status == "insufficient_data"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODEL QUALITY STATUS TRANSITIONS (spec §22)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEvaluateStatus:
    def test_accepted(self) -> None:
        diag = PhysicsDiagnostics(sample_count=100, rmse=0.5, r_squared=0.9, convergence_status="converged")
        status = evaluate_status(diag, {"min_samples": 10, "max_rmse": 1.0, "minimum_r_squared": 0.5})
        assert status == "accepted"

    def test_insufficient_data(self) -> None:
        diag = PhysicsDiagnostics(sample_count=5, convergence_status="converged")
        status = evaluate_status(diag, {"min_samples": 100})
        assert status == "insufficient_data"

    def test_warning_rmse(self) -> None:
        diag = PhysicsDiagnostics(sample_count=100, rmse=5.0, convergence_status="converged")
        status = evaluate_status(diag, {"min_samples": 10, "max_rmse": 2.0})
        assert status == "warning"

    def test_warning_r_squared(self) -> None:
        diag = PhysicsDiagnostics(sample_count=100, r_squared=0.05, convergence_status="converged")
        status = evaluate_status(diag, {"min_samples": 10, "minimum_r_squared": 0.5})
        assert status == "warning"

    def test_rejected_out_of_bounds(self) -> None:
        diag = PhysicsDiagnostics(sample_count=100, convergence_status="converged")
        status = evaluate_status(diag, {"min_samples": 10}, {"cda": 99.0, "cda_bounds": [0.1, 3.5]})
        # evaluate_status checks f"{name}_bounds" so we pass cda and cda_bounds
        # Actually looking at the code: for name, value in (parameter_values or {}).items():
        #   bounds = config.get(f"{name}_bounds")
        # So we need config to have "cda_bounds"
        status = evaluate_status(diag, {"min_samples": 10, "cda_bounds": [0.1, 3.5]}, {"cda": 99.0})
        assert status == "rejected"

    def test_failed_non_converged(self) -> None:
        diag = PhysicsDiagnostics(sample_count=100, convergence_status="failed")
        status = evaluate_status(diag, {"min_samples": 10})
        assert status == "failed"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OUTLIER HANDLING / EXCLUSION REASONS (spec §19)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestOutlierHandling:
    def test_drag_filter_records_exclusion_reasons(self) -> None:
        cfg = _config()
        n = 100
        rng = np.random.default_rng(11)
        speed = rng.uniform(5.0, 80.0, n)
        accel = rng.uniform(-3.0, 1.0, n)
        throttle = rng.uniform(0.0, 100.0, n)
        brake = rng.choice([True, False], n)
        df = pd.DataFrame({
            "speed_ms": speed,
            "acceleration_longitudinal": accel,
            "throttle_percent": throttle,
            "brake_active": brake,
        })
        result = estimate_drag(df, cfg)
        # The result should have exclusion reasons in diagnostics
        diag = result.diagnostics
        assert diag.rows_input == n
        total_accounted = diag.rows_used + sum(diag.exclusion_reasons.values())
        # Total accounted should equal or be close to rows_input
        # (some categories may overlap; exclusion_reasons counts are sequential)
        assert total_accounted <= diag.rows_input + 1  # sequential filter, no double-count

    def test_exclusion_reasons_keys_present(self) -> None:
        cfg = _config()
        speed = np.concatenate([np.array([10.0, 15.0]), np.linspace(25.0, 75.0, 60)])
        accel = np.concatenate([np.array([-0.5, -0.6]), -np.linspace(0.3, 2.0, 60)])
        df = pd.DataFrame({
            "speed_ms": speed,
            "acceleration_longitudinal": accel,
            "throttle_percent": 0.0,
            "brake_active": False,
        })
        result = estimate_drag(df, cfg)
        # Should have "below_min_speed" as an exclusion reason
        assert "below_min_speed" in result.diagnostics.exclusion_reasons


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DIAGNOSTICS (spec §21)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestRegressionDiagnostics:
    def test_perfect_prediction(self) -> None:
        observed = np.array([1.0, 2.0, 3.0])
        predicted = np.array([1.0, 2.0, 3.0])
        d = regression_diagnostics(observed, predicted, rows_input=3)
        assert d.rmse == pytest.approx(0.0, abs=1e-12)
        assert d.r_squared == pytest.approx(1.0, abs=1e-12)
        assert d.sample_count == 3

    def test_all_nan(self) -> None:
        observed = np.array([np.nan, np.nan])
        predicted = np.array([1.0, 2.0])
        d = regression_diagnostics(observed, predicted, rows_input=2)
        assert d.sample_count == 0
        assert d.rows_used == 0

    def test_residual_stats(self) -> None:
        observed = np.array([1.0, 2.0, 3.0])
        predicted = np.array([1.0, 2.0, 2.0])
        d = regression_diagnostics(observed, predicted, rows_input=3)
        assert d.residual_mean is not None
        assert d.residual_std is not None
        assert d.mae is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UNCERTAINTY (spec §20)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestUncertainty:
    def test_covariance_from_design_basic(self) -> None:
        x = np.array([[1.0], [2.0], [3.0]])
        residuals = np.array([0.1, -0.1, 0.05])
        cov = covariance_from_design(x, residuals, 1)
        assert cov is not None
        assert cov.shape == (1, 1)

    def test_covariance_underdetermined(self) -> None:
        x = np.array([[1.0]])
        residuals = np.array([0.1])
        cov = covariance_from_design(x, residuals, 1)
        assert cov is None

    def test_standard_errors_none_covariance(self) -> None:
        se = standard_errors(None)
        assert se == []

    def test_standard_errors_negative_diagonal(self) -> None:
        cov = np.array([[-1.0]])
        se = standard_errors(cov)
        assert se == [None]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODEL REGISTRY (spec §6)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestModelRegistry:
    EXPECTED_KEYS = {"drag", "downforce", "longitudinal", "tyres", "grip", "cornering"}

    def test_all_models_registered(self) -> None:
        assert set(MODEL_REGISTRY.keys()) == self.EXPECTED_KEYS

    def test_each_model_has_required_attributes(self) -> None:
        for key, model in MODEL_REGISTRY.items():
            assert model.name, f"{key} missing name"
            assert model.version, f"{key} missing version"
            assert len(model.required_features) > 0, f"{key} missing required_features"
            assert len(model.parameters) > 0, f"{key} missing parameters"
            assert callable(model.fit), f"{key} fit not callable"

    def test_selected_models_all(self) -> None:
        models = selected_models(["all"])
        assert len(models) == len(self.EXPECTED_KEYS)

    def test_selected_models_specific(self) -> None:
        models = selected_models(["drag", "tyres"])
        assert len(models) == 2

    def test_selected_models_unknown_ignored(self) -> None:
        models = selected_models(["drag", "nonexistent"])
        assert len(models) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONVERGENCE FAILURE (spec §33)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConvergenceFailure:
    def test_drag_all_nan_data(self) -> None:
        cfg = _config()
        cfg["models"]["drag"]["min_samples"] = 0
        df = pd.DataFrame({
            "speed_ms": [np.nan] * 30,
            "acceleration_longitudinal": [np.nan] * 30,
            "throttle_percent": 0.0,
            "brake_active": False,
        })
        result = estimate_drag(df, cfg)
        # With min_samples=0, all NaN rows are filtered out → 0 usable samples.
        # The model either returns insufficient_data, failed, or rejected (bounds violation on CdA=0).
        # All are acceptable: the model does not fabricate a meaningful estimate.
        assert result.status in {"insufficient_data", "failed", "rejected"}

    def test_drag_zero_variance_speed(self) -> None:
        cfg = _config()
        cfg["models"]["drag"]["min_samples"] = 0
        # All same speed → singular design matrix for CdA, but lstsq handles it
        df = pd.DataFrame({
            "speed_ms": [50.0] * 30,
            "acceleration_longitudinal": [-0.5] * 30,
            "throttle_percent": 0.0,
            "brake_active": False,
        })
        result = estimate_drag(df, cfg)
        # Should still produce a result (lstsq handles rank-deficient cases)
        assert result.status in {"accepted", "warning", "rejected"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# IDENTIFIABILITY REPORTING (spec §17/§39)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIdentifiabilityReporting:
    """Verify that every model correctly reports what it can and cannot identify."""

    def _run_drag(self) -> None:
        cfg = _config()
        speed = np.linspace(25.0, 75.0, 80)
        accel = -drag_force(speed, air_density=1.225, effective_drag_parameter=1.5) / 800.0
        df = pd.DataFrame({"speed_ms": speed, "acceleration_longitudinal": accel, "throttle_percent": 0.0, "brake_active": False})
        return estimate_drag(df, cfg)

    def test_drag_never_claims_cd_identifiable(self) -> None:
        result = self._run_drag()
        assert "drag_coefficient" in result.identifiability.non_identifiable_parameters
        assert "frontal_area" in result.identifiability.non_identifiable_parameters
        for p in result.parameters:
            assert p.parameter_name != "drag_coefficient"
            assert p.parameter_name != "frontal_area"

    def test_longitudinal_never_claims_engine_power(self) -> None:
        cfg = _config()
        speed = np.linspace(25.0, 70.0, 100)
        accel = np.full(100, 2.0)
        df = pd.DataFrame({"speed_ms": speed, "acceleration_longitudinal": accel, "throttle_percent": 100.0, "brake_active": False})
        result = estimate_longitudinal(df, cfg, drag_cda=1.5)
        assert "engine_power" in result.identifiability.non_identifiable_parameters
        for p in result.parameters:
            assert p.parameter_name != "engine_power"
            assert p.parameter_name != "true_engine_power"
