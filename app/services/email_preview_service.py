from __future__ import annotations

from dataclasses import dataclass

from app.entities.dealer import Dealer


EMAIL_SUBJECT = "Anfrage zu meiner BMW Wunschkonfiguration"
EMAIL_BODY_TEMPLATE = """Sehr geehrte Damen und Herren,

ich interessiere mich für einen neuen BMW.

Meine Wunschkonfiguration:

{config_url}

Ich freue mich über Ihr Angebot.

Bitte teilen Sie mir mit:

- Endpreis
- Lieferzeit
- Gültigkeit
- Überführungskosten

Vielen Dank.

Mit freundlichen Grüßen"""


@dataclass(frozen=True)
class EmailPreview:
    dealer_id: int
    to: str
    subject: str
    body: str


class EmailPreviewService:
    def build_preview(self, dealer: Dealer, config_url: str) -> EmailPreview:
        return EmailPreview(
            dealer_id=dealer.id,
            to=dealer.email or "",
            subject=EMAIL_SUBJECT,
            body=EMAIL_BODY_TEMPLATE.format(config_url=config_url),
        )

    def build_previews(self, dealers: list[Dealer], config_url: str) -> list[EmailPreview]:
        return [self.build_preview(dealer, config_url) for dealer in dealers]
