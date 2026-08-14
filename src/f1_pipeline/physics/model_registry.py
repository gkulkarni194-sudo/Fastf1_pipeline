from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from f1_pipeline.physics.aero.estimator import (
    DOWNFORCE_MODEL_NAME,
    DOWNFORCE_MODEL_VERSION,
    DRAG_MODEL_NAME,
    DRAG_MODEL_VERSION,
    estimate_downforce,
    estimate_drag,
)
from f1_pipeline.physics.cornering.estimator import CORNERING_MODEL_NAME, CORNERING_MODEL_VERSION, estimate_cornering
from f1_pipeline.physics.longitudinal.estimator import LONGITUDINAL_MODEL_NAME, LONGITUDINAL_MODEL_VERSION, estimate_longitudinal
from f1_pipeline.physics.schemas import PhysicsModelResult
from f1_pipeline.physics.tyres.estimator import GRIP_MODEL_NAME, GRIP_MODEL_VERSION, TYRE_MODEL_NAME, TYRE_MODEL_VERSION, estimate_tyre_degradation, estimate_tyre_grip


@dataclass(frozen=True)
class RegisteredPhysicsModel:
    key: str
    name: str
    version: str
    required_features: tuple[str, ...]
    parameters: tuple[str, ...]
    fit: Callable[..., PhysicsModelResult]
    asset_type: str

    def predict(self, *_args: Any, **_kwargs: Any) -> None:
        raise NotImplementedError("Predictions are produced during fit for registered Layer 3 models.")

    def diagnostics(self, result: PhysicsModelResult) -> dict[str, Any]:
        return result.diagnostics.model_dump(mode="json")


def _fit_drag(datasets: dict[str, pd.DataFrame], config: dict[str, Any], _context: dict[str, Any]) -> PhysicsModelResult:
    return estimate_drag(datasets.get("derived_telemetry", pd.DataFrame()), config)


def _fit_downforce(datasets: dict[str, pd.DataFrame], config: dict[str, Any], _context: dict[str, Any]) -> PhysicsModelResult:
    return estimate_downforce(datasets.get("derived_telemetry", pd.DataFrame()), config)


def _fit_longitudinal(datasets: dict[str, pd.DataFrame], config: dict[str, Any], context: dict[str, Any]) -> PhysicsModelResult:
    return estimate_longitudinal(datasets.get("derived_telemetry", pd.DataFrame()), config, drag_cda=context.get("effective_drag_parameter"))


def _fit_tyres(datasets: dict[str, pd.DataFrame], config: dict[str, Any], _context: dict[str, Any]) -> PhysicsModelResult:
    return estimate_tyre_degradation(datasets.get("derived_laps", pd.DataFrame()), config)


def _fit_grip(datasets: dict[str, pd.DataFrame], config: dict[str, Any], _context: dict[str, Any]) -> PhysicsModelResult:
    return estimate_tyre_grip(datasets.get("derived_telemetry", pd.DataFrame()), config)


def _fit_cornering(datasets: dict[str, pd.DataFrame], config: dict[str, Any], _context: dict[str, Any]) -> PhysicsModelResult:
    return estimate_cornering(datasets.get("corners", pd.DataFrame()), datasets.get("derived_telemetry"), config)


MODEL_REGISTRY: dict[str, RegisteredPhysicsModel] = {
    "drag": RegisteredPhysicsModel("drag", DRAG_MODEL_NAME, DRAG_MODEL_VERSION, ("speed_ms", "acceleration_longitudinal"), ("effective_drag_parameter",), _fit_drag, "derived_telemetry"),
    "downforce": RegisteredPhysicsModel("downforce", DOWNFORCE_MODEL_NAME, DOWNFORCE_MODEL_VERSION, ("speed_ms", "acceleration_lateral"), ("effective_downforce_parameter",), _fit_downforce, "derived_telemetry"),
    "longitudinal": RegisteredPhysicsModel("longitudinal", LONGITUDINAL_MODEL_NAME, LONGITUDINAL_MODEL_VERSION, ("speed_ms", "acceleration_longitudinal"), ("effective_drive_force", "effective_wheel_power"), _fit_longitudinal, "derived_telemetry"),
    "tyres": RegisteredPhysicsModel("tyres", TYRE_MODEL_NAME, TYRE_MODEL_VERSION, ("lap_time_seconds",), ("estimated_degradation_coefficient",), _fit_tyres, "derived_laps"),
    "grip": RegisteredPhysicsModel("grip", GRIP_MODEL_NAME, GRIP_MODEL_VERSION, ("acceleration_lateral",), ("effective_grip_parameter",), _fit_grip, "derived_telemetry"),
    "cornering": RegisteredPhysicsModel("cornering", CORNERING_MODEL_NAME, CORNERING_MODEL_VERSION, ("speed_ms", "acceleration_lateral"), ("effective_corner_radius",), _fit_cornering, "corners"),
}


def selected_models(model_keys: list[str]) -> list[RegisteredPhysicsModel]:
    keys = list(MODEL_REGISTRY) if "all" in model_keys else model_keys
    return [MODEL_REGISTRY[key] for key in keys if key in MODEL_REGISTRY]
