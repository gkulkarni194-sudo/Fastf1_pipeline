from __future__ import annotations

from pathlib import Path
from typing import Any

import fastf1

from f1_pipeline.core.config import RuntimeConfig, load_config


class FastF1Client:
    def __init__(self, cache_dir: str | Path | None = None, config: RuntimeConfig | None = None) -> None:
        runtime_config = config or load_config()
        self.cache_dir = Path(cache_dir) if cache_dir is not None else runtime_config.fastf1_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(self.cache_dir))

    def load_session(self, season: int, event: str, session_type: str) -> Any:
        session = fastf1.get_session(season, event, session_type)
        session.load()
        return session
