from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.models import BMWConfiguration, Dealer, DealerInquiry, DealerOffer


def test_bmw_configuration_defaults_and_decimal_fields() -> None:
    configuration = BMWConfiguration(
        configuration_url="https://www.bmw.de/de-de/sl/stocklocator#/detail/123",
        model="BMW i5",
        variant="eDrive40",
        list_price=Decimal("75990.00"),
        maximum_target_price=Decimal("70000.00"),
        payment_preference="either",
        equipment=["M Sportpaket", "Panoramadach"],
    )

    assert configuration.id
    assert isinstance(configuration.id, str)
    assert configuration.list_price == Decimal("75990.00")
    assert configuration.maximum_target_price == Decimal("70000.00")


def test_bmw_configuration_rejects_blank_equipment_entries() -> None:
    with pytest.raises(ValidationError, match="equipment entries must not be empty"):
        BMWConfiguration(
            configuration_url="https://www.bmw.de/de-de/sl/stocklocator#/detail/123",
            model="BMW i5",
            variant="eDrive40",
            maximum_target_price=Decimal("70000.00"),
            payment_preference="cash",
            equipment=["M Sportpaket", "  "],
        )


def test_bmw_configuration_rejects_target_price_above_list_price() -> None:
    with pytest.raises(
        ValidationError,
        match="list_price must be greater than or equal to maximum_target_price",
    ):
        BMWConfiguration(
            configuration_url="https://www.bmw.de/de-de/sl/stocklocator#/detail/123",
            model="BMW i5",
            variant="eDrive40",
            list_price=Decimal("65000.00"),
            maximum_target_price=Decimal("70000.00"),
            payment_preference="financing",
            equipment=[],
        )


def test_dealer_defaults_and_email_validation() -> None:
    dealer = Dealer(
        company_name="Autohaus Beispiel GmbH",
        postal_code="80331",
        city="Muenchen",
        website="https://www.example-bmw.de",
        sales_email="verkauf@example-bmw.de",
        authorized_bmw_partner=True,
    )

    assert isinstance(dealer.id, UUID)
    assert dealer.status == "new"
    assert dealer.sales_email == "verkauf@example-bmw.de"


def test_dealer_inquiry_uses_utc_timestamp_and_uuid_defaults() -> None:
    dealer_id = UUID("11111111-1111-1111-1111-111111111111")
    inquiry = DealerInquiry(
        dealer_id=dealer_id,
        configuration_id="config-123",
        campaign_number=1,
        subject="Anfrage BMW i5",
        message="Bitte senden Sie ein Angebot.",
    )

    assert isinstance(inquiry.id, UUID)
    assert inquiry.created_at.tzinfo == timezone.utc
    assert inquiry.status == "drafted"


def test_dealer_inquiry_rejects_inconsistent_timestamps() -> None:
    created_at = datetime(2026, 7, 22, 10, 0, tzinfo=timezone.utc)
    approved_at = datetime(2026, 7, 22, 9, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="approved_at must not be earlier than created_at"):
        DealerInquiry(
            dealer_id=UUID("11111111-1111-1111-1111-111111111111"),
            configuration_id="config-123",
            campaign_number=2,
            subject="Anfrage BMW i5",
            message="Bitte senden Sie ein Angebot.",
            created_at=created_at,
            approved_at=approved_at,
        )


def test_dealer_offer_defaults_and_optional_fields() -> None:
    offer = DealerOffer(
        dealer_id=UUID("11111111-1111-1111-1111-111111111111"),
        inquiry_id=UUID("22222222-2222-2222-2222-222222222222"),
        vehicle_price=Decimal("68990.00"),
        transfer_cost=Decimal("990.00"),
        cash_price=Decimal("69980.00"),
        raw_response="Wir koennen Ihnen das Fahrzeug kurzfristig anbieten.",
    )

    assert isinstance(offer.id, UUID)
    assert offer.created_at.tzinfo == timezone.utc
    assert offer.vehicle_price == Decimal("68990.00")


def test_dealer_offer_rejects_negative_amounts() -> None:
    with pytest.raises(ValidationError):
        DealerOffer(
            dealer_id=UUID("11111111-1111-1111-1111-111111111111"),
            inquiry_id=UUID("22222222-2222-2222-2222-222222222222"),
            vehicle_price=Decimal("-1.00"),
            raw_response="Antwort",
        )


def test_dealer_offer_rejects_production_date_after_delivery_date() -> None:
    with pytest.raises(ValidationError, match="production_date must not be later than delivery_date"):
        DealerOffer(
            dealer_id=UUID("11111111-1111-1111-1111-111111111111"),
            inquiry_id=UUID("22222222-2222-2222-2222-222222222222"),
            production_date=date(2026, 9, 1),
            delivery_date=date(2026, 8, 15),
            raw_response="Antwort",
        )
