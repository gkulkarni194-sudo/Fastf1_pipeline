from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PROJECT_ROOT / "configs"
DATA_DIR = PROJECT_ROOT / "data"


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    configs: Path
    data: Path
    raw: Path
    interim: Path
    processed: Path
    curated: Path
    cache: Path
    logs: Path
    fastf1_raw: Path

    @classmethod
    def from_root(cls, root: Path = PROJECT_ROOT) -> ProjectPaths:
        data_dir = root / "data"
        return cls(
            root=root,
            configs=root / "configs",
            data=data_dir,
            raw=data_dir / "raw",
            interim=data_dir / "interim",
            processed=data_dir / "processed",
            curated=data_dir / "curated",
            cache=data_dir / "cache",
            logs=data_dir / "logs",
            fastf1_raw=data_dir / "raw" / "fastf1",
        )

    def ensure_directories(self) -> None:
        for directory in self.data_directories:
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def data_directories(self) -> tuple[Path, ...]:
        return (
            self.data,
            self.raw,
            self.interim,
            self.processed,
            self.curated,
            self.cache,
            self.logs,
            self.fastf1_raw,
        )


def slugify_path_component(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    if not slug:
        raise ValueError("Path component cannot be empty.")
    return slug


def fastf1_raw_session_dir(
    *,
    season: int,
    event: str,
    session_type: str,
    driver_code: str | None = None,
    raw_root: Path | None = None,
) -> Path:
    root = raw_root or PATHS.fastf1_raw
    driver = driver_code.upper() if driver_code else "all"
    return (
        root
        / str(season)
        / slugify_path_component(event)
        / session_type.upper()
        / driver
    )


PATHS = ProjectPaths.from_root()
PATHS.ensure_directories()
