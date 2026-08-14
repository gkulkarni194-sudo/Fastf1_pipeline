from __future__ import annotations

import logging
from pathlib import Path

from f1_pipeline.core.paths import PATHS


SECRET_MARKERS = ("SUPABASE_SERVICE_ROLE_KEY",)


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for marker in SECRET_MARKERS:
            if marker in message:
                record.msg = message.replace(marker, "[redacted-secret-field]")
                record.args = ()
        return True


def configure_logging(level: str = "INFO", log_file: Path | None = None, console: bool = False) -> None:
    handlers: list[logging.Handler] = []
    if console:
        handlers.append(logging.StreamHandler())
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    if not handlers:
        handlers.append(logging.NullHandler())

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    logging.getLogger().addFilter(SecretRedactionFilter())
    PATHS.logs.mkdir(parents=True, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
