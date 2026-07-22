import re
from decimal import Decimal
from app.domain.dealer_offer import DealerOffer


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

    def extract_contact_person(self) -> str | None:
        match = re.search(
            r"Verkäufer\s+([^\n]+)",
            self.text,
        )

        if not match:
            return None

        return match.group(1).strip()

    def extract_leasing_available(self) -> bool:
        return bool(
            re.search(
                r"\bLeasing(?:beispiel|angebot|rate|raten)?\b",
                self.text,
                re.IGNORECASE,
            )
        )

    def extract_financing_available(self) -> bool:
        return bool(
            re.search(
                r"\bFinanzierung(?:sbeispiel|sangebot|srate)?\b",
                self.text,
                re.IGNORECASE,
            )
        )

    def extract(
        self,
        *,
        campaign_id: str,
        configuration_id: str,
        dealer_id: str,
        email_subject: str | None = None,
        email_text: str | None = None,
        pdf_filename: str | None = None,
    ) -> DealerOffer:
        list_price = self.extract_list_price()
        offer_price = self.extract_total_price()

        if list_price is None:
            raise ValueError(
                "Der Bruttolistenpreis konnte nicht aus dem Angebot extrahiert werden."
            )

        if offer_price is None:
            raise ValueError(
                "Der Gesamtpreis konnte nicht aus dem Angebot extrahiert werden."
            )

        offer_number = self.extract_offer_number()
        dealer_services = self.extract_dealer_services()
        stated_discount = self.extract_discount_percent()

        notes_parts: list[str] = []

        if offer_number:
            notes_parts.append(f"BMW-Angebotsnummer: {offer_number}")

        if dealer_services is not None:
            notes_parts.append(
                f"Händlerleistungen: {dealer_services:.2f} EUR"
            )

        if stated_discount is not None:
            notes_parts.append(
                f"Im Dokument ausgewiesener Nachlass: {stated_discount} %"
            )

        return DealerOffer(
            campaign_id=campaign_id,
            configuration_id=configuration_id,
            dealer_id=dealer_id,
            list_price=list_price,
            offer_price=offer_price,
            financing_available=self.extract_financing_available(),
            leasing_available=self.extract_leasing_available(),
            contact_person=self.extract_contact_person(),
            email_subject=email_subject,
            email_text=email_text,
            pdf_filename=pdf_filename,
            notes="\n".join(notes_parts) or None,
        )
