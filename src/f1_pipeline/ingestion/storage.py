from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from f1_pipeline.core.hashing import file_sha256
from f1_pipeline.core.paths import PROJECT_ROOT


@dataclass(frozen=True)
class StoredAsset:
    path: str
    checksum: str
    row_count: int | None
    file_format: str


class StorageManager:
    def save_dataframe(self, dataframe: pd.DataFrame, path: str | Path) -> StoredAsset:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        safe = _safe_dataframe_for_parquet(dataframe)
        safe.to_parquet(output_path, index=False)
        return StoredAsset(
            path=_clean_path(output_path),
            checksum=file_sha256(output_path),
            row_count=int(len(safe.index)),
            file_format="parquet",
        )

    def save_json(self, payload: dict[str, Any], path: str | Path) -> StoredAsset:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=True, allow_nan=False, indent=2, sort_keys=True)
            file.write("\n")
        return StoredAsset(
            path=_clean_path(output_path),
            checksum=file_sha256(output_path),
            row_count=1,
            file_format="json",
        )


def _clean_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _safe_dataframe_for_parquet(dataframe: pd.DataFrame) -> pd.DataFrame:
    safe = pd.DataFrame(dataframe).copy()
    for column in safe.columns:
        if safe[column].dtype == "object":
            safe[column] = safe[column].map(_safe_value)
    return safe


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
