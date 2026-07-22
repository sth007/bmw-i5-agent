from __future__ import annotations

from app.models import Offer, Preferences


def score_offer(offer: Offer, preferences: Preferences) -> int:
    score = 0

    if offer.price_eur <= preferences.budget_eur:
        score += 50

    if offer.color.lower() == preferences.preferred_color.lower():
        score += 25

    if offer.range_km >= preferences.minimum_range_km:
        score += 25

    return score
