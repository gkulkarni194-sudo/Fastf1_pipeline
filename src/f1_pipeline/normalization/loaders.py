from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from f1_pipeline.core.paths import PROJECT_ROOT


def load_raw_parquet(storage_path: str) -> pd.DataFrame:
    """Load a raw Parquet file produced by Layer 0.

    ``storage_path`` is stored relative to ``PROJECT_ROOT`` in the
    ``raw_data_assets`` table, e.g.
    ``data/raw/fastf1/2024/bahrain/q/ver/laps.parquet``.
    """
    path = _resolve(storage_path)
    if not path.exists():
        raise FileNotFoundError(f"Raw asset not found: {path}")
    return pd.read_parquet(path)


def load_raw_json(storage_path: str) -> dict[str, Any]:
    """Load a raw JSON metadata file produced by Layer 0."""
    path = _resolve(storage_path)
    if not path.exists():
        raise FileNotFoundError(f"Raw metadata not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _resolve(storage_path: str) -> Path:
    p = Path(storage_path)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p
