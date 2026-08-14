from __future__ import annotations

import pandas as pd

from f1_pipeline.ingestion.quality import validate_laps, validate_telemetry, validate_weather


def test_laps_quality_requires_key_columns() -> None:
    report = validate_laps(pd.DataFrame({"Driver": ["VER"]}))

    assert not report.passed
    assert "LapTime" in report.errors[0]


def test_telemetry_quality_warns_for_optional_channels() -> None:
    report = validate_telemetry(pd.DataFrame({"Speed": [300], "Throttle": [100]}))

    assert report.passed
    assert report.warnings


def test_weather_empty_is_warning_not_failure() -> None:
    report = validate_weather(pd.DataFrame())

    assert report.passed
    assert report.warnings
