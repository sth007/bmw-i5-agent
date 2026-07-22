import pytest
from pydantic import ValidationError

from app.domain.dealer import ContactStatus, Dealer


def test_valid_dealer_can_be_contacted_by_email() -> None:
    dealer = Dealer(
        dealer_id="dealer-001",
        name="BMW Autohaus Beispiel",
        dealer_group="Beispiel Gruppe",
        branch_name="Filiale Stuttgart",
        street="Musterstraße 1",
        postal_code="70173",
        city="Stuttgart",
        sales_email="verkauf@example.de",
        website_url="https://example.de",
    )

    assert dealer.name == "BMW Autohaus Beispiel"
    assert dealer.contact_status == ContactStatus.NOT_CONTACTED
    assert dealer.can_be_contacted() is True


def test_dealer_without_contact_path_cannot_be_contacted() -> None:
    dealer = Dealer(
        dealer_id="dealer-002",
        name="BMW Autohaus Ohne Kontakt",
        city="München",
    )

    assert dealer.can_be_contacted() is False


def test_blocked_dealer_cannot_be_contacted() -> None:
    dealer = Dealer(
        dealer_id="dealer-003",
        name="BMW Autohaus Gesperrt",
        city="Berlin",
        sales_email="verkauf@example.de",
        contact_status=ContactStatus.BLOCKED,
    )

    assert dealer.can_be_contacted() is False


def test_do_not_contact_prevents_contact() -> None:
    dealer = Dealer(
        dealer_id="dealer-004",
        name="BMW Autohaus Abgemeldet",
        city="Hamburg",
        sales_email="verkauf@example.de",
        do_not_contact=True,
    )

    assert dealer.can_be_contacted() is False


def test_invalid_email_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Dealer(
            dealer_id="dealer-005",
            name="BMW Autohaus Fehler",
            city="Köln",
            sales_email="keine-gueltige-email",
        )


def test_empty_city_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Dealer(
            dealer_id="dealer-006",
            name="BMW Autohaus Fehler",
            city="   ",
            sales_email="verkauf@example.de",
        )