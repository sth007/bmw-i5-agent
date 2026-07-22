from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


NonNegativeDecimal = Annotated[Decimal, Field(ge=Decimal("0"))]
PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeInt = Annotated[int, Field(ge=0)]


class DomainModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class BMWConfiguration(DomainModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    configuration_url: HttpUrl
    model: str = Field(min_length=1)
    variant: str = Field(min_length=1)
    package: str | None = Field(default=None, min_length=1)
    list_price: NonNegativeDecimal | None = None
    maximum_target_price: NonNegativeDecimal
    payment_preference: Literal["cash", "financing", "either"]
    equipment: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pricing(self) -> BMWConfiguration:
        if self.list_price is not None and self.list_price < self.maximum_target_price:
            raise ValueError("list_price must be greater than or equal to maximum_target_price")
        return self

    @model_validator(mode="after")
    def validate_equipment(self) -> BMWConfiguration:
        if any(not item for item in self.equipment):
            raise ValueError("equipment entries must not be empty")
        return self


class Dealer(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    company_name: str = Field(min_length=1)
    dealer_group: str | None = Field(default=None, min_length=1)
    location_name: str | None = Field(default=None, min_length=1)
    postal_code: str = Field(min_length=3, max_length=12)
    city: str = Field(min_length=1)
    website: HttpUrl | None = None
    sales_email: EmailStr | None = None
    contact_form_url: HttpUrl | None = None
    authorized_bmw_partner: bool
    status: Literal[
        "new",
        "drafted",
        "approved",
        "sent",
        "responded",
        "offer_received",
        "rejected",
    ] = "new"
    last_contacted_at: datetime | None = None


class DealerInquiry(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    dealer_id: UUID
    configuration_id: str = Field(min_length=1)
    campaign_number: PositiveInt
    subject: str = Field(min_length=1)
    message: str = Field(min_length=1)
    status: Literal["drafted", "approved", "sent", "failed"] = "drafted"
    created_at: datetime = Field(default_factory=utc_now)
    approved_at: datetime | None = None
    sent_at: datetime | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> DealerInquiry:
        if self.approved_at is not None and self.approved_at < self.created_at:
            raise ValueError("approved_at must not be earlier than created_at")
        if self.sent_at is not None and self.sent_at < self.created_at:
            raise ValueError("sent_at must not be earlier than created_at")
        if self.approved_at is not None and self.sent_at is not None and self.sent_at < self.approved_at:
            raise ValueError("sent_at must not be earlier than approved_at")
        return self


class DealerOffer(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    dealer_id: UUID
    inquiry_id: UUID
    vehicle_price: NonNegativeDecimal | None = None
    transfer_cost: NonNegativeDecimal | None = None
    registration_cost: NonNegativeDecimal | None = None
    cash_price: NonNegativeDecimal | None = None
    financing_required: bool | None = None
    financing_total_cost: NonNegativeDecimal | None = None
    delivery_date: date | None = None
    production_date: date | None = None
    model_year: int | None = Field(default=None, ge=1900, le=date.today().year + 2)
    holding_period_months: NonNegativeInt | None = None
    day_registration: bool | None = None
    trade_in_required: bool | None = None
    offer_valid_until: date | None = None
    raw_response: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_offer_dates(self) -> DealerOffer:
        if (
            self.production_date is not None
            and self.delivery_date is not None
            and self.production_date > self.delivery_date
        ):
            raise ValueError("production_date must not be later than delivery_date")
        return self


@dataclass(frozen=True)
class Preferences:
    budget_eur: int = 70000
    preferred_color: str = "black"
    minimum_range_km: int = 500


@dataclass(frozen=True)
class Offer:
    model: str
    price_eur: int
    color: str
    range_km: int
