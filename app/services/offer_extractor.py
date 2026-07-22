import re
from decimal import Decimal


class OfferExtractor:
    """
    Extrahiert strukturierte Informationen aus einem BMW-Angebot.
    """

    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def _parse_german_decimal(value: str) -> Decimal:
        normalized = value.replace(".", "").replace(",", ".")
        return Decimal(normalized)

    def extract_offer_number(self) -> str | None:
        match = re.search(
            r"Angebot Nr\.\s+(\d+)",
            self.text,
        )

        if not match:
            return None

        return match.group(1)

    def extract_discount_percent(self) -> Decimal | None:
        match = re.search(
            r"Nachlass.*?\(([\d,]+)%\)",
            self.text,
            re.DOTALL,
        )

        if not match:
            return None

        value = match.group(1).replace(",", ".")
        return Decimal(value)

    def extract_total_price(self) -> Decimal | None:
        match = re.search(
            r"Gesamtpreis\s+([\d.]+,\d{2})",
            self.text,
        )

        if not match:
            return None

        return self._parse_german_decimal(match.group(1))

    def extract_list_price(self) -> Decimal | None:
        match = re.search(
            r"Bruttolistenpreis.*?beträgt\s+([\d.]+,\d{2})\s+EUR",
            self.text,
            re.DOTALL,
        )

        if not match:
            return None

        return self._parse_german_decimal(match.group(1))

    def extract_dealer_services(self) -> Decimal | None:
        match = re.search(
            r"Händlerleistungen\s+([\d.]+,\d{2})",
            self.text,
        )

        if not match:
            return None

        return self._parse_german_decimal(match.group(1))