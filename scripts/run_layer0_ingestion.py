from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _bootstrap import bootstrap_src_layout


bootstrap_src_layout()

from f1_pipeline.ingestion.layer0_pipeline import run_layer0_ingestion
from f1_pipeline.ingestion.schemas import Layer0IngestionRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Layer 0 FastF1 ingestion.")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--event", type=str, required=True)
    parser.add_argument("--session", type=str, required=True)
    parser.add_argument("--driver", type=str, required=False, default=None)
    parser.add_argument("--force", action="store_true", help="Re-fetch and overwrite existing local raw assets.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    request = Layer0IngestionRequest(
        season=args.season,
        event=args.event,
        session_type=args.session,
        driver_code=args.driver,
        force=args.force,
    )
    result = run_layer0_ingestion(request)
    _print_result(result)
    if not result.success:
        raise SystemExit(1)


def _model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return json.loads(model.json())


def _print_result(result: Any) -> None:
    print(f"status: {'success' if result.success else 'failed'}")
    print(f"message: {result.message}")
    print(f"ingestion_run_id: {result.ingestion_run_id or '<not created>'}")
    for asset in result.assets:
        print("")
        print(f"source: {asset.source}")
        print(f"asset_type: {asset.asset_type}")
        print(f"path: {asset.storage_path}")
        print(f"rows: {asset.row_count}")
        print(f"checksum: {asset.checksum}")


if __name__ == "__main__":
    main()
