from __future__ import annotations

from pathlib import Path

from f1_pipeline.core.paths import fastf1_raw_session_dir, slugify_path_component


def test_event_slug_generation() -> None:
    assert slugify_path_component("Saudi Arabian Grand Prix") == "saudi_arabian_grand_prix"


def test_fastf1_raw_session_dir_with_driver() -> None:
    path = fastf1_raw_session_dir(
        season=2024,
        event="Bahrain",
        session_type="q",
        driver_code="VER",
        raw_root=Path("data/raw/fastf1"),
    )

    assert path == Path("data/raw/fastf1/2024/bahrain/Q/VER")


def test_fastf1_raw_session_dir_without_driver() -> None:
    path = fastf1_raw_session_dir(
        season=2024,
        event="Bahrain",
        session_type="Q",
        raw_root=Path("data/raw/fastf1"),
    )

    assert path == Path("data/raw/fastf1/2024/bahrain/Q/all")
