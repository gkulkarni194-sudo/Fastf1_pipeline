from __future__ import annotations

import json
import logging
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from f1_pipeline.core.hashing import file_sha256
from f1_pipeline.core.paths import PATHS, PROJECT_ROOT
from f1_pipeline.core.text import slug
from f1_pipeline.db.repositories.feature_assets import FeatureAssetsRepository
from f1_pipeline.db.repositories.physics_assets import PhysicsAssetsRepository
from f1_pipeline.db.repositories.physics_runs import PhysicsRunsRepository
from f1_pipeline.ingestion.storage import StorageManager
from f1_pipeline.physics.model_registry import selected_models
from f1_pipeline.physics.schemas import (
    PHYSICS_SCHEMA_VERSION,
    Layer3PhysicsRequest,
    Layer3PhysicsResult,
    PhysicsAssetResult,
    PhysicsModelResult,
)

logger = logging.getLogger(__name__)


class Layer3PhysicsPipeline:
    def __init__(
        self,
        *,
        feature_assets: FeatureAssetsRepository | None = None,
        physics_assets: PhysicsAssetsRepository | None = None,
        physics_runs: PhysicsRunsRepository | None = None,
        physics_config: dict[str, Any] | None = None,
        storage: StorageManager | None = None,
    ) -> None:
        self._feature_assets_repo = feature_assets
        self._physics_assets_repo = physics_assets
        self._physics_runs_repo = physics_runs
        self._physics_config = physics_config or {}
        self._storage = storage or StorageManager()

    def run(self, request: Layer3PhysicsRequest) -> Layer3PhysicsResult:
        try:
            feature_repo = self._feature_assets_repo or FeatureAssetsRepository()
            physics_assets_repo = self._physics_assets_repo or PhysicsAssetsRepository()
            runs_repo = self._physics_runs_repo or PhysicsRunsRepository()
        except Exception as exc:
            return Layer3PhysicsResult(success=False, message=f"Supabase connection failed: {exc}")

        try:
            feature_rows = _discover_feature_assets(
                feature_repo,
                season=request.season,
                event=request.event,
                session_type=request.session_type,
                driver_code=request.driver_code,
            )
        except Exception as exc:
            return Layer3PhysicsResult(success=False, message=f"Layer 2 feature asset discovery failed: {exc}")
        if not feature_rows:
            return Layer3PhysicsResult(success=False, message="No successful Layer 2 feature assets found.")

        source_feature_run_id = feature_rows[0].get("feature_run_id")
        try:
            run_record = runs_repo.create_started(
                source_feature_run_id=source_feature_run_id,
                config_hash=request.config_hash,
                code_version=request.code_version,
            )
            physics_run_id = str(run_record["id"])
        except Exception as exc:
            return Layer3PhysicsResult(success=False, message=f"Failed to create physics_run: {exc}")

        assets: list[PhysicsAssetResult] = []
        model_results: dict[str, PhysicsModelResult] = {}
        try:
            datasets = _load_feature_datasets(feature_rows)
            source_by_type = {str(row.get("asset_type")): str(row.get("id")) for row in feature_rows if row.get("id")}
            context: dict[str, Any] = {}
            for model in selected_models(request.models):
                if not self._physics_config.get("models", {}).get(model.key, {}).get("enabled", True):
                    continue
                if not request.force and physics_assets_repo.find_existing(
                    source_feature_asset_id=source_by_type.get(model.asset_type),
                    asset_type=f"{model.key}_parameters",
                    physics_schema_version=PHYSICS_SCHEMA_VERSION,
                ):
                    continue
                result = model.fit(datasets, self._physics_config, context)
                model_results[model.key] = result
                for parameter in result.parameters:
                    if parameter.parameter_name == "effective_drag_parameter" and parameter.value is not None:
                        context["effective_drag_parameter"] = parameter.value
                    physics_assets_repo.create_parameter(
                        physics_run_id=physics_run_id,
                        parameter_name=parameter.parameter_name,
                        value=parameter.value,
                        unit=parameter.unit,
                        standard_error=parameter.standard_error,
                        confidence_interval_low=parameter.confidence_interval_low,
                        confidence_interval_high=parameter.confidence_interval_high,
                        model_name=parameter.model_name,
                        model_version=parameter.model_version,
                        sample_count=parameter.sample_count,
                        status=parameter.status,
                    )

            output_dir = _physics_output_dir(request.season, request.event, request.session_type, request.driver_code)
            output_dir.mkdir(parents=True, exist_ok=True)
            assets.extend(_save_model_jsons(output_dir, model_results, request, source_by_type, physics_assets_repo))
            assets.extend(_save_prediction_tables(output_dir, model_results, request, source_by_type, physics_assets_repo, self._storage))
            session_summary = _session_summary(model_results, request)
            summary_asset = self._storage.save_json(session_summary, output_dir.parent / "session_physics_summary.json")
            physics_assets_repo.create_asset(
                source_feature_asset_id=None,
                season=request.season,
                event_name=request.event,
                session_type=request.session_type,
                driver_code=None,
                asset_type="session_physics_summary",
                storage_path=summary_asset.path,
                file_format=summary_asset.file_format,
                checksum=summary_asset.checksum,
                row_count=summary_asset.row_count,
                physics_schema_version=PHYSICS_SCHEMA_VERSION,
            )
            assets.append(_asset_result(summary_asset, request, "session_physics_summary", None))
            runs_repo.mark_success(physics_run_id)
            return Layer3PhysicsResult(
                physics_run_id=physics_run_id,
                source_feature_run_id=source_feature_run_id,
                assets=assets,
                model_results=model_results,
                success=True,
                message="Layer 3 physics inference completed successfully.",
            )
        except Exception as exc:
            logger.exception("Layer 3 physics inference failed: %s", exc)
            try:
                runs_repo.mark_failed(physics_run_id, str(exc))
            except Exception:
                logger.error("Failed to mark physics_run as failed.")
            return Layer3PhysicsResult(
                physics_run_id=physics_run_id,
                source_feature_run_id=source_feature_run_id,
                assets=assets,
                model_results=model_results,
                success=False,
                message=f"Layer 3 physics inference failed: {exc}",
            )


def run_layer3_physics(request: Layer3PhysicsRequest, physics_config: dict[str, Any] | None = None) -> Layer3PhysicsResult:
    return Layer3PhysicsPipeline(physics_config=physics_config).run(request)


def _discover_feature_assets(repo: FeatureAssetsRepository, *, season: int, event: str, session_type: str, driver_code: str | None) -> list[dict[str, Any]]:
    query = (
        repo.client.table(repo.table_name)
        .select("*")
        .eq("season", season)
        .eq("event_name", event)
        .eq("session_type", session_type)
    )
    if driver_code:
        query = query.eq("driver_code", driver_code)
    rows = query.order("created_at", desc=True).execute().data
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        asset_type = str(row.get("asset_type"))
        if asset_type not in latest:
            latest[asset_type] = row
    return list(latest.values())


def _load_feature_datasets(feature_rows: list[dict[str, Any]]) -> dict[str, pd.DataFrame]:
    datasets: dict[str, pd.DataFrame] = {}
    for row in feature_rows:
        path = _resolve_storage_path(str(row["storage_path"]))
        if path.exists() and str(row.get("file_format", "parquet")).lower() == "parquet":
            datasets[str(row["asset_type"])] = pd.read_parquet(path)
    return datasets


def _save_model_jsons(
    output_dir: Path,
    model_results: dict[str, PhysicsModelResult],
    request: Layer3PhysicsRequest,
    source_by_type: dict[str, str],
    repo: PhysicsAssetsRepository,
) -> list[PhysicsAssetResult]:
    assets: list[PhysicsAssetResult] = []
    storage = StorageManager()
    diagnostics_payload = {key: result.diagnostics.model_dump(mode="json") for key, result in model_results.items()}
    metadata_payload = {
        "physics_schema_version": PHYSICS_SCHEMA_VERSION,
        "request": request.model_dump(mode="json"),
        "model_status": {key: result.status for key, result in model_results.items()},
        "identifiability": {key: result.identifiability.model_dump(mode="json") for key, result in model_results.items()},
    }
    json_assets = {"model_diagnostics.json": diagnostics_payload, "metadata.json": metadata_payload}
    grouped = {
        "aero_parameters.json": {key: model_results[key].model_dump(mode="json", exclude={"predictions", "residuals"}) for key in ("drag", "downforce") if key in model_results},
        "longitudinal_parameters.json": {key: model_results[key].model_dump(mode="json", exclude={"predictions", "residuals"}) for key in ("longitudinal",) if key in model_results},
        "tyre_parameters.json": {key: model_results[key].model_dump(mode="json", exclude={"predictions", "residuals"}) for key in ("tyres", "grip") if key in model_results},
        "cornering_parameters.json": {key: model_results[key].model_dump(mode="json", exclude={"predictions", "residuals"}) for key in ("cornering",) if key in model_results},
    }
    json_assets.update({file_name: payload for file_name, payload in grouped.items() if payload})
    for file_name, payload in json_assets.items():
        stored = storage.save_json(payload, output_dir / file_name)
        asset_type = Path(file_name).stem
        source_id = _source_for_asset(asset_type, source_by_type)
        repo.create_asset(
            source_feature_asset_id=source_id,
            season=request.season,
            event_name=request.event,
            session_type=request.session_type,
            driver_code=request.driver_code,
            asset_type=asset_type,
            storage_path=stored.path,
            file_format=stored.file_format,
            checksum=stored.checksum,
            row_count=stored.row_count,
            physics_schema_version=PHYSICS_SCHEMA_VERSION,
        )
        assets.append(_asset_result(stored, request, asset_type, source_id))
    return assets


def _save_prediction_tables(
    output_dir: Path,
    model_results: dict[str, PhysicsModelResult],
    request: Layer3PhysicsRequest,
    source_by_type: dict[str, str],
    repo: PhysicsAssetsRepository,
    storage: StorageManager,
) -> list[PhysicsAssetResult]:
    assets: list[PhysicsAssetResult] = []
    for attr, asset_type, file_name in (("predictions", "predictions", "predictions.parquet"), ("residuals", "residuals", "residuals.parquet")):
        rows = []
        for key, result in model_results.items():
            for record in getattr(result, attr):
                rec = dict(record)
                rec["model_key"] = key
                rec["model_name"] = result.model_name
                rec["model_version"] = result.model_version
                rows.append(rec)
        if not rows:
            rows = [{"model_key": None, "model_name": None, "model_version": None, "model": None, "value": np.nan}]
        stored = storage.save_dataframe(pd.DataFrame(rows), output_dir / file_name)
        repo.create_asset(
            source_feature_asset_id=source_by_type.get("derived_telemetry"),
            season=request.season,
            event_name=request.event,
            session_type=request.session_type,
            driver_code=request.driver_code,
            asset_type=asset_type,
            storage_path=stored.path,
            file_format=stored.file_format,
            checksum=stored.checksum,
            row_count=stored.row_count,
            physics_schema_version=PHYSICS_SCHEMA_VERSION,
        )
        assets.append(_asset_result(stored, request, asset_type, source_by_type.get("derived_telemetry")))
    return assets


def _session_summary(model_results: dict[str, PhysicsModelResult], request: Layer3PhysicsRequest) -> dict[str, Any]:
    return {
        "physics_schema_version": PHYSICS_SCHEMA_VERSION,
        "season": request.season,
        "event": request.event,
        "session_type": request.session_type,
        "drivers": [request.driver_code] if request.driver_code else [],
        "model_status": {key: result.status for key, result in model_results.items()},
        "parameters": [
            parameter.model_dump(mode="json")
            for result in model_results.values()
            for parameter in result.parameters
        ],
    }


def _source_for_asset(asset_type: str, source_by_type: dict[str, str]) -> str | None:
    if asset_type.startswith("tyre") and "derived_laps" in source_by_type:
        return source_by_type["derived_laps"]
    if asset_type.startswith("corner") and "corners" in source_by_type:
        return source_by_type["corners"]
    return source_by_type.get("derived_telemetry")


def _physics_output_dir(season: int, event: str, session_type: str, driver_code: str | None) -> Path:
    return PATHS.processed / "physics" / str(season) / slug(event) / slug(session_type) / slug(driver_code or "all")


def _resolve_storage_path(storage_path: str) -> Path:
    path = Path(storage_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _asset_result(stored: Any, request: Layer3PhysicsRequest, asset_type: str, source_feature_asset_id: str | None) -> PhysicsAssetResult:
    return PhysicsAssetResult(
        source_feature_asset_id=source_feature_asset_id,
        asset_type=asset_type,
        season=request.season,
        event=request.event,
        session_type=request.session_type,
        driver_code=request.driver_code,
        storage_path=stored.path,
        file_format=stored.file_format,
        checksum=stored.checksum,
        row_count=stored.row_count,
    )


def physics_config_hash(physics_config: dict[str, Any]) -> str:
    payload = json.dumps(physics_config, sort_keys=True, default=str)
    return sha256(payload.encode("utf-8")).hexdigest()
