from decimal import Decimal
from uuid import uuid4

from app.entities.dealer_offer import DealerOffer
from app.services.campaign_offer_ranking_service import CampaignOfferRankingService
from app.services.offer_comparison_service import OfferComparison


def comparison(category: str, score: int, price: str, dealer_name: str) -> OfferComparison:
    offer = DealerOffer(
        id=uuid4(),
        campaign_id=uuid4(),
        dealer_name=dealer_name,
        total_price=Decimal(price),
        raw_response="Antwort",
    )
    return OfferComparison(offer=offer, category=category, score=score, matches=[])


def test_ranking_prioritizes_exact_then_price_then_alternative() -> None:
    service = CampaignOfferRankingService()
    ranked = service.rank(
        [
            comparison("alternative", 92, "63000.00", "Alternative A"),
            comparison("exact", 100, "65000.00", "Exact B"),
            comparison("exact", 100, "62000.00", "Exact A"),
            comparison("incompatible", 30, "61000.00", "Bad Fit"),
        ]
    )

    assert [item.comparison.offer.dealer_name for item in ranked.ranked_offers] == [
        "Exact A",
        "Exact B",
        "Alternative A",
        "Bad Fit",
    ]
    assert ranked.cheapest_exact_offer_id == ranked.ranked_offers[0].comparison.offer.id
    assert ranked.cheapest_overall_offer_id == ranked.ranked_offers[3].comparison.offer.id
