"""Pytest configuration and shared fixtures."""

import pytest
from app.core.config import settings


@pytest.fixture(autouse=True)
def _override_settings(monkeypatch):
    """Use safe defaults for tests (no real API keys needed)."""
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret-key-do-not-use-in-prod")
