from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.domain.dealer_offer import DealerOffer
from app.repositories.dealer_offer_repository import DealerOfferRepository


def create_offer(
    offer_id: str = "offer-001",
) -> DealerOffer:
    return DealerOffer(
        offer_id=offer_id,
        campaign_id="campaign-001",
        configuration_id="config-001",
        dealer_id="dealer-001",
        list_price=Decimal("74820.00"),
        offer_price=Decimal("56881.26"),
        delivery_date=date(2026, 12, 15),
        financing_available=True,
        leasing_available=True,
        contact_person="Linus Hermann",
        pdf_filename="Angebot-20216449.pdf",
        received_at=datetime(
            2026,
            7,
            23,
            13,
            18,
            tzinfo=timezone.utc,
        ),
        notes="BMW-Angebotsnummer: 20216449",
    )


def test_offer_can_be_saved_and_loaded(tmp_path):
    repository = DealerOfferRepository(
        tmp_path / "offers.db"
    )

    original = create_offer()

    repository.save(original)

    loaded = repository.get_by_id(original.offer_id)

    assert loaded is not None
    assert loaded == original
    assert loaded.list_price == Decimal("74820.00")
    assert loaded.offer_price == Decimal("56881.26")
    assert loaded.contact_person == "Linus Hermann"


def test_unknown_offer_returns_none(tmp_path):
    repository = DealerOfferRepository(
        tmp_path / "offers.db"
    )

    assert repository.get_by_id("unknown") is None


def test_all_offers_can_be_listed(tmp_path):
    repository = DealerOfferRepository(
        tmp_path / "offers.db"
    )

    repository.save(create_offer("offer-001"))
    repository.save(create_offer("offer-002"))

    offers = repository.list_all()

    assert len(offers) == 2
    assert {
        offer.offer_id
        for offer in offers
    } == {
        "offer-001",
        "offer-002",
    }


def test_offer_count(tmp_path):
    repository = DealerOfferRepository(
        tmp_path / "offers.db"
    )

    assert repository.count() == 0

    repository.save(create_offer("offer-001"))
    repository.save(create_offer("offer-002"))

    assert repository.count() == 2


def test_duplicate_offer_id_is_rejected(tmp_path):
    repository = DealerOfferRepository(
        tmp_path / "offers.db"
    )

    offer = create_offer()

    repository.save(offer)

    with pytest.raises(
        ValueError,
        match="bereits gespeichert",
    ):
        repository.save(offer)