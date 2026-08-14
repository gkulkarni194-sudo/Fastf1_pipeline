"""CLI entry-point for Layer 2 feature extraction.

Usage::

    python scripts/run_layer2_features.py \\
        --season 2024 --event Bahrain --session Q --driver VER \\
        --feature-set all

    python scripts/run_layer2_features.py \\
        --season 2024 --event Bahrain --session Q \\
        --feature-set telemetry --feature-set laps

    python scripts/run_layer2_features.py \\
        --season 2024 --event Bahrain --session Q --driver VER \\
        --feature-set all --force
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap src-layout imports
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _bootstrap import bootstrap_src_layout  # noqa: E402

bootstrap_src_layout()

from f1_pipeline.core.config import load_config  # noqa: E402
from f1_pipeline.features.feature_pipeline import run_layer2_features  # noqa: E402
from f1_pipeline.features.schemas import Layer2FeatureRequest  # noqa: E402

VALID_FEATURE_SETS = {"telemetry", "laps", "corners", "stints", "all"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Layer 2 derived-feature extraction on Layer 1 canonical assets.",
    )
    parser.add_argument("--season", type=int, required=True, help="Season year (e.g. 2024)")
    parser.add_argument("--event", type=str, required=True, help="Event name (e.g. Bahrain)")
    parser.add_argument("--session", type=str, required=True, help="Session type (e.g. Q, R, FP1)")
    parser.add_argument("--driver", type=str, default=None, help="Driver code (e.g. VER)")
    parser.add_argument(
        "--feature-set",
        type=str,
        action="append",
        dest="feature_sets",
        choices=sorted(VALID_FEATURE_SETS),
        help="Feature sets to compute. Repeatable. Default: all.",
    )
    parser.add_argument("--force", action="store_true", help="Force re-computation even if already done.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    args = parse_args()

    # Determine feature sets
    feature_sets = args.feature_sets or ["all"]
    if "all" in feature_sets:
        feature_sets = ["all"]

    # Load config for thresholds
    try:
        config = load_config()
        features_config = config.section("features")
    except Exception:
        features_config = {}

    # Build config hash for reproducibility
    import hashlib
    config_hash_input = json.dumps(features_config, sort_keys=True, default=str)
    config_hash = hashlib.sha256(config_hash_input.encode()).hexdigest()

    request = Layer2FeatureRequest(
        season=args.season,
        event=args.event,
        session_type=args.session.upper(),
        driver_code=args.driver.upper() if args.driver else None,
        feature_sets=feature_sets,
        force=args.force,
        config_hash=config_hash,
    )

    result = run_layer2_features(request, features_config=features_config)

    # Pretty-print result
    print("\n" + "=" * 60)
    print("LAYER 2 FEATURE EXTRACTION RESULT")
    print("=" * 60)
    print(json.dumps(_model_to_dict(result), indent=2, sort_keys=True, default=str))

    if not result.success:
        raise SystemExit(1)


def _model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return json.loads(model.json())


if __name__ == "__main__":
    main()
