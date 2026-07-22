from decimal import Decimal

from app.services.offer_extractor import OfferExtractor

from pathlib import Path

import pytest


def test_extract_real_bmw_offer():
    file_path = Path("tests/data/bmw_offer_20216449.txt")
    text = file_path.read_text(encoding="utf-8")

    extractor = OfferExtractor(text)

    assert extractor.extract_offer_number() == "20216449"
    assert extractor.extract_discount_percent() == Decimal("25.7")
    assert extractor.extract_total_price() == Decimal("56881.26")
    assert extractor.extract_list_price() == Decimal("74820.00")
    assert extractor.extract_dealer_services() == Decimal("1290.00")

def test_extract_offer_number():
    text = """
    BMW Niederlassung Stuttgart

    Angebot Nr. 20216449

    Vielen Dank...
    """

    extractor = OfferExtractor(text)

    assert extractor.extract_offer_number() == "20216449"


def test_extract_discount():
    text = """
    Nachlass Modell und Ausstattung (25,7%)
    """

    extractor = OfferExtractor(text)

    assert extractor.extract_discount_percent() == Decimal("25.7")

def test_extract_total_price():
    text = """
    Händlerleistungen 1.290,00
    Gesamtpreis 56.881,26
    """

    extractor = OfferExtractor(text)

    assert extractor.extract_total_price() == Decimal("56881.26")


def test_extract_list_price():
    text = """
    Der Bruttolistenpreis (Summe Modell und zugehöriger Ausstattung)
    für dieses Fahrzeug beträgt 74.820,00 EUR.
    """

    extractor = OfferExtractor(text)

    assert extractor.extract_list_price() == Decimal("74820.00")


def test_extract_dealer_services():
    text = """
    Zubehör 0,00
    Händlerleistungen 1.290,00
    Gesamtpreis 56.881,26
    """

    extractor = OfferExtractor(text)

    assert extractor.extract_dealer_services() == Decimal("1290.00")


def test_extract_contact_person():
    text = """
    Verkäufer
    Linus Hermann
    Telefon
    +49-711-1318-5312
    """

    extractor = OfferExtractor(text)

    assert extractor.extract_contact_person() == "Linus Hermann"


def test_extract_complete_dealer_offer():
    text = """
    Angebot Nr. 20216449 vom 13.07.2026

    Nachlass Modell und Ausstattung (25,7%) - 19.228,74
    Händlerleistungen 1.290,00
    Gesamtpreis 56.881,26

    Der Bruttolistenpreis für dieses Fahrzeug beträgt
    74.820,00 EUR.

    Verkäufer
    Linus Hermann
    Telefon
    +49-711-1318-5312

    Leasingbeispiel der BMW Bank GmbH
    """

    extractor = OfferExtractor(text)

    offer = extractor.extract(
        campaign_id="campaign-001",
        configuration_id="configuration-001",
        dealer_id="dealer-001",
        email_subject="Ihr BMW-Angebot",
        pdf_filename="angebot-20216449.pdf",
    )

    assert offer.campaign_id == "campaign-001"
    assert offer.configuration_id == "configuration-001"
    assert offer.dealer_id == "dealer-001"

    assert offer.list_price == Decimal("74820.00")
    assert offer.offer_price == Decimal("56881.26")
    assert offer.contact_person == "Linus Hermann"

    assert offer.leasing_available is True
    assert offer.financing_available is False

    assert offer.pdf_filename == "angebot-20216449.pdf"
    assert "20216449" in offer.notes
    assert "1290.00 EUR" in offer.notes
    assert "25.7 %" in offer.notes


def test_extract_fails_when_list_price_is_missing():
    extractor = OfferExtractor(
        "Gesamtpreis 56.881,26"
    )

    with pytest.raises(
        ValueError,
        match="Bruttolistenpreis",
    ):
        extractor.extract(
            campaign_id="campaign-001",
            configuration_id="configuration-001",
            dealer_id="dealer-001",
        )


def test_extract_fails_when_total_price_is_missing():
    extractor = OfferExtractor(
        "Der Bruttolistenpreis für dieses Fahrzeug "
        "beträgt 74.820,00 EUR."
    )

    with pytest.raises(
        ValueError,
        match="Gesamtpreis",
    ):
        extractor.extract(
            campaign_id="campaign-001",
            configuration_id="configuration-001",
            dealer_id="dealer-001",
        )
