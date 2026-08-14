from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from f1_pipeline.core.paths import CONFIG_DIR, PROJECT_ROOT


CONFIG_FILES = ("base.yaml", "database.yaml", "ingestion.yaml", "normalization.yaml")


ConfigValue = dict[str, Any] | list[Any] | str | int | float | bool | None
ConfigDict = dict[str, ConfigValue]


@dataclass(frozen=True)
class RuntimeConfig:
    values: ConfigDict

    @property
    def log_level(self) -> str:
        app = self.section("app")
        return str(app.get("log_level", "INFO")).upper()

    @property
    def fastf1_cache_dir(self) -> Path:
        ingestion = self.section("ingestion")
        fastf1 = ingestion.get("fastf1", {})
        if not isinstance(fastf1, dict):
            raise TypeError("Config section 'ingestion.fastf1' is not a mapping.")
        return _project_path(str(fastf1.get("cache_dir", "data/cache/fastf1")))

    @property
    def raw_fastf1_root(self) -> Path:
        paths = self.section("paths")
        return _project_path(str(paths.get("fastf1_raw_dir", "data/raw/fastf1")))

    @property
    def supported_sessions(self) -> set[str]:
        ingestion = self.section("ingestion")
        fastf1 = ingestion.get("fastf1", {})
        if not isinstance(fastf1, dict):
            return {"FP1", "FP2", "FP3", "Q", "SQ", "S", "R"}
        values = fastf1.get("supported_sessions", ["FP1", "FP2", "FP3", "Q", "SQ", "S", "R"])
        if not isinstance(values, list):
            raise TypeError("Config value 'ingestion.fastf1.supported_sessions' must be a list.")
        return {str(value).upper() for value in values}

    def section(self, name: str) -> dict[str, Any]:
        value = self.values.get(name, {})
        if not isinstance(value, dict):
            raise TypeError(f"Config section '{name}' is not a mapping.")
        return value

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)


def load_config(
    config_dir: Path = CONFIG_DIR,
    env_file: Path | None = PROJECT_ROOT / ".env",
) -> RuntimeConfig:
    if env_file is not None:
        load_dotenv(env_file)
    else:
        load_dotenv()

    merged: ConfigDict = {}
    for file_name in CONFIG_FILES:
        merged = _deep_merge(merged, _load_yaml(config_dir / file_name))

    return RuntimeConfig(values=merged)


def _load_yaml(path: Path) -> ConfigDict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}

    if not isinstance(loaded, dict):
        raise TypeError(f"Config file must contain a mapping: {path}")

    return loaded


def _deep_merge(base: ConfigDict, override: Mapping[str, Any]) -> ConfigDict:
    merged: ConfigDict = dict(base)

    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, Mapping):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value

    return merged


def _project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path
