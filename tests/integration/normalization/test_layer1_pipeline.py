"""Integration tests for Layer 1 pipeline.

These tests require:
- Supabase connection (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)
- Layer 0 raw assets to exist in Supabase + locally

Run with: pytest tests/integration/normalization/ -v -m integration
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.integration
class TestLayer1PipelineIntegration:
    """Placeholder for integration tests — require live Supabase."""

    def test_supabase_normalization_run_lifecycle(self):
        """Test creating/marking a normalization run in Supabase."""
        pytest.skip("Requires live Supabase connection")

    def test_canonical_asset_registration(self):
        """Test registering a canonical asset in Supabase."""
        pytest.skip("Requires live Supabase connection")

    def test_idempotency(self):
        """Test that re-running normalization skips existing assets."""
        pytest.skip("Requires live Supabase connection and Layer 0 data")

    def test_force_regeneration(self):
        """Test that --force causes re-normalization."""
        pytest.skip("Requires live Supabase connection and Layer 0 data")
