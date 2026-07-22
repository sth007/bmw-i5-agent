from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    preferences_path: Path = DATA_DIR / "preferences.json"
    offers_path: Path = DATA_DIR / "offers.json"


settings = Settings()
