from __future__ import annotations

from pathlib import Path

from f1_pipeline.core.paths import PROJECT_ROOT


MIGRATION_PATH = PROJECT_ROOT / "docs" / "sql" / "layer0_schema.sql"


def init_db() -> None:
    print("Layer 0 schema initialization uses a Supabase SQL migration.")
    print("Open the Supabase SQL Editor for your project and execute:")
    print(str(MIGRATION_PATH))
    print("")
    print("The migration is idempotent and can be run multiple times.")


__all__ = ["MIGRATION_PATH", "init_db"]
