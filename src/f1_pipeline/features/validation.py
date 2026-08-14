"""Layer 2 feature validation and data-quality reporting.

Every Layer 2 execution must produce a ``QualityReport`` documenting
input/output row counts, features created, missing/invalid values,
and any warnings or errors.

Infinite values (±inf) are replaced with NaN.  This module does NOT
drop rows — it cleans in-place and reports statistics.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from f1_pipeline.features.schemas import QualityReport

logger = logging.getLogger(__name__)


def validate_features(
    df: pd.DataFrame,
    asset_type: str,
) -> tuple[pd.DataFrame, QualityReport]:
    """Validate a derived-feature DataFrame.

    Parameters
    ----------
    df:
        The feature DataFrame to validate.
    asset_type:
        Label for the report (e.g. ``"telemetry"``, ``"laps"``).

    Returns
    -------
    tuple[pd.DataFrame, QualityReport]
        A cleaned copy of *df* and the associated quality report.
    """
    out = df.copy()
    rows_input = len(out)
    features_created = list(out.columns)

    # ------------------------------------------------------------------
    # Replace ±inf with NaN in numeric columns
    # ------------------------------------------------------------------
    numeric_cols = out.select_dtypes(include=[np.number]).columns
    inf_counts: dict[str, int] = {}
    for col in numeric_cols:
        mask = np.isinf(out[col])
        count = int(mask.sum())
        if count > 0:
            inf_counts[col] = count
            out.loc[mask, col] = np.nan

    # ------------------------------------------------------------------
    # Count NaN per column
    # ------------------------------------------------------------------
    missing_counts: dict[str, int] = {}
    for col in out.columns:
        nan_count = int(out[col].isna().sum())
        if nan_count > 0:
            missing_counts[col] = nan_count

    # ------------------------------------------------------------------
    # Duplicate detection (row-level)
    # ------------------------------------------------------------------
    dup_count = int(out.duplicated().sum())

    # ------------------------------------------------------------------
    # Warnings
    # ------------------------------------------------------------------
    warnings: list[str] = []
    if inf_counts:
        warnings.append(
            f"Replaced infinite values with NaN in columns: {sorted(inf_counts.keys())}"
        )
    if dup_count > 0:
        warnings.append(f"Found {dup_count} duplicate rows.")

    # ------------------------------------------------------------------
    # Build report
    # ------------------------------------------------------------------
    report = QualityReport(
        asset_type=asset_type,
        valid=True,
        rows_input=rows_input,
        rows_output=len(out),
        features_created=features_created,
        missing_feature_counts=missing_counts,
        invalid_values_count=inf_counts,
        duplicate_count=dup_count,
        warnings=warnings,
    )

    logger.info(
        "Validation [%s]: %d→%d rows, %d features, %d inf replaced, %d warnings",
        asset_type, rows_input, len(out), len(features_created),
        sum(inf_counts.values()), len(warnings),
    )

    return out, report
