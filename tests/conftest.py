"""Shared test fixtures and configuration."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure src/ is on the import path for tests
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: marks tests requiring external services")
