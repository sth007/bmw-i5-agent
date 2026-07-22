from decimal import Decimal

from app.domain.dealer_offer import DealerOffer


def create_offer() -> DealerOffer:
    return DealerOffer(
        campaign_id="campaign-001",
        configuration_id="chtwyiio",
        dealer_id="dealer-001",
        list_price=Decimal("84900"),
        offer_price=Decimal("71900"),
    )


def test_discount_amount():
    offer = create_offer()

    assert offer.discount_amount == Decimal("13000")


def test_discount_percent():
    offer = create_offer()

    assert offer.discount_percent == Decimal("15.31")


def test_is_discounted():
    offer = create_offer()

    assert offer.is_discounted is True


def test_offer_id_is_generated():
    offer = create_offer()

    assert len(offer.offer_id) > 20