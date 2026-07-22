from app.evaluator import score_offer
from app.models import Offer, Preferences


def test_score_offer_rewards_matching_preferences() -> None:
    preferences = Preferences(
        budget_eur=70000,
        preferred_color="black",
        minimum_range_km=500,
    )
    offer = Offer(
        model="BMW i5 eDrive40",
        price_eur=68000,
        color="black",
        range_km=580,
    )

    assert score_offer(offer, preferences) == 100
