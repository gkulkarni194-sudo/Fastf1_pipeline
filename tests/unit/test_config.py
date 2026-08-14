from __future__ import annotations

from f1_pipeline.core.config import load_config


def test_load_config_exposes_layer0_paths() -> None:
    config = load_config(env_file=None)

    assert config.raw_fastf1_root.as_posix().endswith("data/raw/fastf1")
    assert config.fastf1_cache_dir.as_posix().endswith("data/cache/fastf1")
    assert {"FP1", "Q", "R"}.issubset(config.supported_sessions)
