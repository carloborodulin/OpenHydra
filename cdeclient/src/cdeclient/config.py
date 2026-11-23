"""Configuration, loaded from the environment and an optional local .env."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BASE_URL = "https://api.usa.gov/crime/fbi/cde"


def find_env_file(start: Path | None = None) -> Path | None:
    """Find the .env file to read.

    1. ``OPENHYDRA_ENV_FILE``, when it is set.
    2. Else the first ``.env`` in the working directory or a parent directory.
       The search stops at the repository root (the directory with ``.git``),
       so a command in ``api/`` or ``warehouse/`` reads the root ``.env``.
    """
    explicit = os.environ.get("OPENHYDRA_ENV_FILE")
    if explicit:
        return Path(explicit)
    here = (start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            break
    return None


class Settings(BaseSettings):
    """Reads ``FBI_CDE_API_KEY`` and ``FBI_CDE_BASE_URL``.

    A process environment variable wins over the .env file (see
    :func:`find_env_file` for the file location).
    """

    model_config = SettingsConfigDict(
        env_prefix="FBI_CDE_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SecretStr keeps the key out of repr(), str() and validation errors.
    api_key: SecretStr | None = None
    base_url: str = DEFAULT_BASE_URL

    def __init__(self, **values: Any) -> None:
        values.setdefault("_env_file", find_env_file())
        super().__init__(**values)
