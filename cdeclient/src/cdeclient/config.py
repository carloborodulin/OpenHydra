"""Configuration, loaded from the environment and an optional local .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BASE_URL = "https://api.usa.gov/crime/fbi/cde"


class Settings(BaseSettings):
    """Reads ``FBI_CDE_API_KEY`` and ``FBI_CDE_BASE_URL`` from env / .env."""

    model_config = SettingsConfigDict(
        env_prefix="FBI_CDE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
