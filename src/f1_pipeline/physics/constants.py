from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PhysicalConstant:
    name: str
    value: float
    unit: str
    provenance: str


DEFAULT_CONSTANTS = {
    "air_density": PhysicalConstant("air_density", 1.225, "kg/m^3", "assumed"),
    "gravity": PhysicalConstant("gravity", 9.80665, "m/s^2", "configured"),
    "vehicle_mass_reference": PhysicalConstant("vehicle_mass_reference", 798.0, "kg", "assumed"),
    "rolling_resistance_reference": PhysicalConstant(
        "rolling_resistance_reference", 0.012, "dimensionless", "assumed"
    ),
}


def constant_from_config(config: dict[str, Any], name: str) -> PhysicalConstant:
    raw = config.get("constants", {}).get(name, {})
    default = DEFAULT_CONSTANTS[name]
    if not isinstance(raw, dict):
        return default
    return PhysicalConstant(
        name=name,
        value=float(raw.get("value", default.value)),
        unit=str(raw.get("unit", default.unit)),
        provenance=str(raw.get("provenance", default.provenance)),
    )
