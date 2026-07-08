# src/config/settings.py
import os
from functools import lru_cache

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and security"""

    # === App Configuration ===
    app_name: str = Field(default="BomaQuant Backend")
    app_env: str = Field(default="development")
    api_prefix: str = Field(default="")

    # === NSE API Configuration ===
    nse_rapidapi_key: str = Field(default="", validate_default=True)
    nse_api_timeout: int = Field(default=10, ge=5, le=30)  # 5-30 seconds
    nse_max_retries: int = Field(default=3, ge=1, le=5)

    # === Caching ===
    cache_enabled: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=300, ge=60)  # 5 min default

    # === Security ===
    log_sensitive_data: bool = Field(default=False)  # NEVER log API keys
    auth_enabled: bool = Field(default=False)
    api_username: str = Field(default="admin")
    api_password: str = Field(default="change-me")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore unknown env vars (safer)
    )
    
    @field_validator('nse_rapidapi_key', mode='before')
    def validate_api_key(cls, v):
        """Ensure API key looks valid (basic check)"""
        if v is None:
            raise ValueError("NSE_RAPIDAPI_KEY appears invalid")
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("NSE_RAPIDAPI_KEY appears invalid")
            return v
        raise ValueError("NSE_RAPIDAPI_KEY appears invalid")

    @classmethod
    def _get_default_api_key(cls) -> str:
        return "test_key_12345678901234567890"

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings loader (efficient + singleton pattern)."""
    try:
        return Settings()
    except ValidationError:
        if os.getenv("APP_ENV", "development").lower() == "development":
            return Settings(nse_rapidapi_key=Settings._get_default_api_key())
        raise


def reset_settings_cache() -> None:
    """Clear the cached settings so tests can override values deterministically."""
    get_settings.cache_clear()