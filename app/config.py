from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "BMW Agent"
    app_version: str = "1.0.0"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://bmw_agent:bmw_agent@localhost:5432/bmw_agent_app",
    )


settings = Settings()
