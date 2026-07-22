from decimal import Decimal

import pytest

from app.domain.dealer_offer import DealerOffer
from app.services.offer_evaluator import OfferEvaluator


def offer(price: str) -> DealerOffer:
    return DealerOffer(
        campaign_id="c1",
        configuration_id="cfg1",
        dealer_id=price,
        list_price=Decimal("85000"),
        offer_price=Decimal(price),
    )


def test_best_offer():
    evaluator = OfferEvaluator()

    best = evaluator.best_offer([
        offer("73000"),
        offer("70500"),
        offer("71900"),
    ])

    assert best.offer_price == Decimal("70500")


def test_empty_list():
    evaluator = OfferEvaluator()

    with pytest.raises(ValueError):
        evaluator.best_offer([])