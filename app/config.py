from __future__ import annotations

import os
from dataclasses import dataclass


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "BMW Agent"
    app_version: str = "1.0.0"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://bmw_agent:bmw_agent@localhost:5432/bmw_agent_app",
    )

    @property
    def app_env(self) -> str:
        return os.getenv("APP_ENV", "development").strip().lower()

    @property
    def single_campaign_mode(self) -> bool:
        return _env_flag("SINGLE_CAMPAIGN_MODE", True)

    @property
    def allow_test_reset(self) -> bool:
        return _env_flag("ALLOW_TEST_RESET", True)

    @property
    def test_reset_token(self) -> str:
        return os.getenv("TEST_RESET_TOKEN", "change-me")


settings = Settings()
