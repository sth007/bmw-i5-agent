from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OfferImport(BaseModel):
    source: str = Field(min_length=1, max_length=50)
    external_id: str = Field(min_length=1, max_length=150)

    dealer_id: int | None = None

    title: str = Field(min_length=1, max_length=300)
    model: str | None = Field(default=None, max_length=100)
    variant: str | None = Field(default=None, max_length=150)

    price: Decimal = Field(gt=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)

    mileage_km: int | None = Field(default=None, ge=0)
    first_registration: str | None = Field(default=None, max_length=10)
    power_kw: int | None = Field(default=None, ge=0)

    fuel_type: str | None = Field(default=None, max_length=50)
    transmission: str | None = Field(default=None, max_length=50)
    drivetrain: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=100)

    vin: str | None = Field(default=None, max_length=50)

    url: str
    image_url: str | None = None


class OfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    external_id: str
    dealer_id: int | None

    title: str
    model: str | None
    variant: str | None

    price: Decimal
    currency: str

    mileage_km: int | None
    first_registration: str | None
    power_kw: int | None

    fuel_type: str | None
    transmission: str | None
    drivetrain: str | None
    color: str | None

    vin: str | None
    url: str
    image_url: str | None

    is_active: bool
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class OfferImportResult(BaseModel):
    received: int
    created: int
    updated: int
    unchanged: int