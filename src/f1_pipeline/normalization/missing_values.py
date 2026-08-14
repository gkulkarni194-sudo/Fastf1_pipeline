"""Missing-value normalization.

Rules (Layer 1 policy)
---------------------
* Replace empty strings with ``None`` / ``NaN``.
* Convert sentinel-like values to ``NaN`` where appropriate.
* Preserve ``NaT`` for time-like columns.
* Do **NOT** forward-fill, interpolate, or impute.
* Do **NOT** replace missing physical measurements with zero.
* Behaviour must be fully deterministic.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def normalize_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize missing-value representations.

    Transformations applied:
    1. Empty strings ``""`` → ``NaN``
    2. Whitespace-only strings → ``NaN``
    3. String ``"None"`` / ``"null"`` / ``"NaN"`` → ``NaN``

    No interpolation, forward-fill, or zero-replacement is performed.
    """
    out = df.copy()

    for col in out.columns:
        if out[col].dtype == object:
            # Replace empty / whitespace-only strings
            mask_empty = out[col].apply(
                lambda v: isinstance(v, str) and v.strip() == ""
            )
            out.loc[mask_empty, col] = None

            # Replace string sentinels
            mask_sentinel = out[col].apply(
                lambda v: isinstance(v, str) and v.strip().lower() in {"none", "null", "nan"}
            )
            out.loc[mask_sentinel, col] = None

    return out


def report_missing_values(df: pd.DataFrame) -> dict[str, int]:
    """Return ``{column_name: count_of_missing}`` for non-zero counts."""
    counts: dict[str, int] = {}
    for col in df.columns:
        n = int(df[col].isna().sum())
        if n > 0:
            counts[col] = n
    return counts
