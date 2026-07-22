from decimal import Decimal

from app.services.offer_extractor import OfferExtractor

from pathlib import Path


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