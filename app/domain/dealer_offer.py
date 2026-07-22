from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class DealerOffer(BaseModel):
    offer_id: str = Field(default_factory=lambda: str(uuid4()))

    campaign_id: str = Field(min_length=1)
    configuration_id: str = Field(min_length=1)
    dealer_id: str = Field(min_length=1)

    list_price: Decimal = Field(gt=0)
    offer_price: Decimal = Field(gt=0)

    delivery_date: date | None = None
    production_date: date | None = None

    financing_available: bool = False
    leasing_available: bool = False
    trade_in_possible: bool = False

    contact_person: str | None = None

    email_subject: str | None = None
    email_text: str | None = None

    pdf_filename: str | None = None

    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    notes: str | None = None

    @field_validator(
        "campaign_id",
        "configuration_id",
        "dealer_id",
        "contact_person",
        "email_subject",
        "email_text",
        "pdf_filename",
        "notes",
    )
    @classmethod
    def strip_text(cls, value: str | None):
        if value is None:
            return None

        value = value.strip()
        return value or None

    @property
    def discount_amount(self) -> Decimal:
        return self.list_price - self.offer_price

    @property
    def discount_percent(self) -> Decimal:
        return (
            self.discount_amount
            / self.list_price
            * Decimal("100")
        ).quantize(Decimal("0.01"))

    @property
    def is_discounted(self) -> bool:
        return self.offer_price < self.list_price