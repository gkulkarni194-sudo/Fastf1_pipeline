"""CLI entry-point for Layer 3 physics inference."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _bootstrap import bootstrap_src_layout  # noqa: E402

bootstrap_src_layout()

from f1_pipeline.core.config import load_config  # noqa: E402
from f1_pipeline.physics.estimation_pipeline import physics_config_hash, run_layer3_physics  # noqa: E402
from f1_pipeline.physics.model_registry import MODEL_REGISTRY  # noqa: E402
from f1_pipeline.physics.schemas import Layer3PhysicsRequest  # noqa: E402


VALID_MODELS = set(MODEL_REGISTRY) | {"all"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Layer 3 physics inference on Layer 2 feature assets.")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--event", type=str, required=True)
    parser.add_argument("--session", type=str, required=True)
    parser.add_argument("--driver", type=str, default=None)
    parser.add_argument("--model", action="append", choices=sorted(VALID_MODELS), default=None)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    args = parse_args()
    config = load_config()
    physics_config = config.section("physics")
    models = args.model or ["all"]
    if "all" in models:
        models = ["all"]
    request = Layer3PhysicsRequest(
        season=args.season,
        event=args.event,
        session_type=args.session.upper(),
        driver_code=args.driver.upper() if args.driver else None,
        models=models,
        force=args.force,
        config_hash=physics_config_hash(physics_config),
    )
    result = run_layer3_physics(request, physics_config=physics_config)
    print("\n" + "=" * 60)
    print("LAYER 3 PHYSICS INFERENCE RESULT")
    print("=" * 60)
    print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True, default=str))
    if not result.success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
