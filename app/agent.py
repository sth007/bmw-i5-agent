from __future__ import annotations

from app.config import settings
from app.evaluator import score_offer
from app.models import Offer, Preferences
from app.utils import load_json


class BmwI5Agent:
    def load_preferences(self) -> Preferences:
        return Preferences(**load_json(settings.preferences_path))

    def load_offers(self) -> list[Offer]:
        raw_offers = load_json(settings.offers_path)
        return [Offer(**item) for item in raw_offers]

    def pick_best_offer(self) -> tuple[Offer, int]:
        preferences = self.load_preferences()
        offers = self.load_offers()
        ranked = sorted(
            ((offer, score_offer(offer, preferences)) for offer in offers),
            key=lambda item: item[1],
            reverse=True,
        )
        return ranked[0]
