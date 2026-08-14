from __future__ import annotations

import pandas as pd

from f1_pipeline.ingestion.schemas import QualityReport


def validate_laps(dataframe: pd.DataFrame) -> QualityReport:
    errors: list[str] = []
    warnings: list[str] = []
    if dataframe is None:
        errors.append("Laps dataframe is missing.")
    elif dataframe.empty:
        errors.append("Laps dataframe is empty.")
    else:
        for column in ("Driver", "LapTime"):
            if column not in dataframe.columns:
                errors.append(f"Laps dataframe is missing required column '{column}'.")
    return QualityReport(asset_type="fastf1_session_laps", passed=not errors, errors=errors, warnings=warnings)


def validate_weather(dataframe: pd.DataFrame) -> QualityReport:
    errors: list[str] = []
    warnings: list[str] = []
    if dataframe is None:
        warnings.append("Weather dataframe is missing.")
    elif dataframe.empty:
        warnings.append("Weather dataframe is empty.")
    return QualityReport(asset_type="fastf1_weather", passed=not errors, errors=errors, warnings=warnings)


def validate_telemetry(dataframe: pd.DataFrame) -> QualityReport:
    errors: list[str] = []
    warnings: list[str] = []
    if dataframe is None or dataframe.empty:
        errors.append("Telemetry dataframe is missing or empty.")
    else:
        expected = ("Speed", "Throttle", "Brake", "RPM", "nGear", "DRS")
        missing = [column for column in expected if column not in dataframe.columns]
        if missing:
            warnings.append(f"Telemetry missing optional raw channel(s): {', '.join(missing)}")
    return QualityReport(asset_type="fastf1_driver_telemetry", passed=not errors, errors=errors, warnings=warnings)


def raise_if_failed(report: QualityReport) -> None:
    if not report.passed:
        raise ValueError("; ".join(report.errors))
