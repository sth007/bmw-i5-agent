from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preferences:
    budget_eur: int = 70000
    preferred_color: str = "black"
    minimum_range_km: int = 500


@dataclass(frozen=True)
class Offer:
    model: str
    price_eur: int
    color: str
    range_km: int
