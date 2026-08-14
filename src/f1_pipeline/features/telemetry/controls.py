"""Driver control-state normalisation.

Derives consistently-named boolean and percentage control features:

* ``throttle_percent`` — 0–100 clamped
* ``brake_active``     — bool (True when brake > 0)
* ``brake_intensity``  — raw brake value passed-through (if source is
  a pressure/percentage), otherwise same as brake_active cast to float
* ``gear``             — integer gear number (pass-through)
* ``drs_active``       — bool (DRS open when value >= 10 per F1 convention)

Missing source channels produce NaN-filled columns rather than errors.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_controls(df: pd.DataFrame) -> pd.DataFrame:
    """Derive and normalise driver control states.

    Parameters
    ----------
    df:
        Canonical telemetry DataFrame.

    Returns
    -------
    pd.DataFrame
        Copy of *df* with normalised control columns added.
    """
    out = df.copy()

    # ------------------------------------------------------------------
    # Throttle
    # ------------------------------------------------------------------
    if "throttle" in out.columns:
        out["throttle_percent"] = pd.to_numeric(
            out["throttle"], errors="coerce"
        ).clip(0, 100)
    else:
        logger.warning("Missing 'throttle' channel — throttle_percent filled with NaN.")
        out["throttle_percent"] = np.nan

    # ------------------------------------------------------------------
    # Brake
    # ------------------------------------------------------------------
    if "brake" in out.columns:
        brake_numeric = pd.to_numeric(out["brake"], errors="coerce").fillna(0)
        out["brake_active"] = brake_numeric > 0

        # Brake intensity: if the source already encodes a pressure or
        # percentage (values between 0-100), pass it through.  Otherwise
        # treat it as the boolean flag cast to float (0.0 / 1.0).
        if brake_numeric.max() > 1:
            out["brake_intensity"] = brake_numeric
        else:
            out["brake_intensity"] = brake_numeric.astype(float)
    else:
        logger.warning("Missing 'brake' channel — brake_active filled with False.")
        out["brake_active"] = False
        out["brake_intensity"] = 0.0

    # ------------------------------------------------------------------
    # Gear (pass-through, ensure integer-like)
    # ------------------------------------------------------------------
    if "gear" in out.columns:
        out["gear"] = pd.to_numeric(out["gear"], errors="coerce")
    # else: leave absent — not all sources provide gear

    # ------------------------------------------------------------------
    # DRS
    # ------------------------------------------------------------------
    if "drs" in out.columns:
        drs_numeric = pd.to_numeric(out["drs"], errors="coerce").fillna(0)
        # In F1 telemetry, DRS values 10, 12, 14 indicate open DRS.
        out["drs_active"] = drs_numeric >= 10
    else:
        logger.warning("Missing 'drs' channel — drs_active filled with False.")
        out["drs_active"] = False

    return out
