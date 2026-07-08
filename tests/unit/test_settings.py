# tests/unit/test_settings.py
import pytest
from pydantic import ValidationError

from src.config.settings import Settings, get_settings


def test_settings_require_api_key(monkeypatch):
    """Test that missing API key raises error"""
    monkeypatch.delenv("NSE_RAPIDAPI_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings()

def test_settings_valid_key(monkeypatch):
    """Test that valid key is accepted"""
    monkeypatch.setenv("NSE_RAPIDAPI_KEY", "a" * 32)
    settings = Settings()
    assert settings.nse_rapidapi_key == "a" * 32
    assert settings.nse_api_timeout == 10  # default

def test_settings_cached():
    """Test that get_settings() uses cache"""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2  # Same object (cached)