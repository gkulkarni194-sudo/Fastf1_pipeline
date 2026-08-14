"""CLI entry-point for Layer 1 normalization.

Usage::

    python scripts/run_layer1_normalization.py \\
        --season 2024 --event Bahrain --session Q --driver VER --all

    python scripts/run_layer1_normalization.py \\
        --season 2024 --event Bahrain --session Q \\
        --asset-type laps --asset-type weather

    python scripts/run_layer1_normalization.py \\
        --season 2024 --event Bahrain --session Q --driver VER --all --force
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

from f1_pipeline.normalization.layer1_pipeline import run_layer1_normalization  # noqa: E402
from f1_pipeline.normalization.schemas import Layer1NormalizationRequest  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Layer 1 canonical normalization on Layer 0 raw assets.",
    )
    parser.add_argument("--season", type=int, required=True, help="Season year (e.g. 2024)")
    parser.add_argument("--event", type=str, required=True, help="Event name (e.g. Bahrain)")
    parser.add_argument("--session", type=str, required=True, help="Session type (e.g. Q, R, FP1)")
    parser.add_argument("--driver", type=str, default=None, help="Driver code (e.g. VER)")
    parser.add_argument(
        "--asset-type",
        type=str,
        action="append",
        dest="asset_types",
        help="Asset types to normalize (laps, weather, telemetry). Repeatable.",
    )
    parser.add_argument("--all", action="store_true", dest="all_assets", help="Normalize all asset types.")
    parser.add_argument("--force", action="store_true", help="Force re-normalization even if already done.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    args = parse_args()

    # Determine asset types
    if args.all_assets:
        asset_types = ["laps", "weather", "telemetry"]
    elif args.asset_types:
        asset_types = args.asset_types
    else:
        asset_types = ["laps", "weather", "telemetry"]  # default to all

    request = Layer1NormalizationRequest(
        season=args.season,
        event=args.event,
        session_type=args.session,
        driver_code=args.driver,
        asset_types=asset_types,
        force=args.force,
    )

    result = run_layer1_normalization(request)

    # Pretty-print result
    print("\n" + "=" * 60)
    print("LAYER 1 NORMALIZATION RESULT")
    print("=" * 60)
    print(json.dumps(_model_to_dict(result), indent=2, sort_keys=True))

    if not result.success:
        raise SystemExit(1)


def _model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return json.loads(model.json())


if __name__ == "__main__":
    main()
