from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConfigurationRequirementCreate(BaseModel):
    feature_key: str = Field(min_length=1, max_length=120)
    feature_value: str | None = None
    display_label: str | None = Field(default=None, max_length=200)
    is_mandatory: bool = True


class CampaignConfigurationCreate(BaseModel):
    configuration_url: str | None = None
    model: str = Field(min_length=1, max_length=120)
    variant: str = Field(min_length=1, max_length=120)
    package: str | None = Field(default=None, max_length=120)
    list_price: Decimal | None = Field(default=None, ge=0)
    maximum_target_price: Decimal = Field(ge=0)
    payment_preference: Literal["cash", "financing", "either"] = "either"
    requirements: list[ConfigurationRequirementCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_prices(self) -> "CampaignConfigurationCreate":
        if self.list_price is not None and self.list_price < self.maximum_target_price:
            raise ValueError("list_price must be greater than or equal to maximum_target_price")
        return self


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    notes: str | None = None
    configuration: CampaignConfigurationCreate


class CampaignStatusPatch(BaseModel):
    status: Literal["draft", "active", "paused", "completed", "cancelled"]


class DealerOfferFeatureCreate(BaseModel):
    feature_key: str = Field(min_length=1, max_length=120)
    feature_value: str | None = None
    display_label: str | None = Field(default=None, max_length=200)
    is_available: bool = True


class DealerOfferCreate(BaseModel):
    dealer_name: str = Field(min_length=1, max_length=200)
    dealer_reference: str | None = Field(default=None, max_length=120)
    source_type: Literal["manual", "email", "pdf", "extracted"] = "manual"
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    vehicle_price: Decimal | None = Field(default=None, ge=0)
    transfer_cost: Decimal | None = Field(default=None, ge=0)
    registration_cost: Decimal | None = Field(default=None, ge=0)
    total_price: Decimal | None = Field(default=None, ge=0)
    cash_price: Decimal | None = Field(default=None, ge=0)
    financing_required: bool | None = None
    financing_total_cost: Decimal | None = Field(default=None, ge=0)
    delivery_date: date | None = None
    production_date: date | None = None
    model_year: int | None = Field(default=None, ge=1900, le=2100)
    holding_period_months: int | None = Field(default=None, ge=0)
    day_registration: bool | None = None
    trade_in_required: bool | None = None
    offer_valid_until: date | None = None
    raw_response: str = Field(min_length=1)
    features: list[DealerOfferFeatureCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_total_price(self) -> "DealerOfferCreate":
        if self.total_price is None:
            parts = [self.vehicle_price, self.transfer_cost, self.registration_cost]
            if any(part is not None for part in parts):
                self.total_price = sum((part or Decimal("0")) for part in parts)
        return self


class DealerOfferExtractRequest(BaseModel):
    dealer_name: str = Field(min_length=1, max_length=200)
    dealer_reference: str | None = Field(default=None, max_length=120)
    source_type: Literal["email", "pdf", "extracted"] = "extracted"
    text: str = Field(min_length=1)


class ConfigurationRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    feature_key: str
    feature_value: str | None
    normalized_key: str
    normalized_value: str | None
    display_label: str | None
    is_mandatory: bool


class CampaignConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    configuration_url: str | None
    model: str
    variant: str
    package: str | None
    list_price: Decimal | None
    maximum_target_price: Decimal
    payment_preference: str
    requirements: list[ConfigurationRequirementResponse]


class CampaignSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: str
    notes: str | None
    cheapest_exact_price: Decimal | None
    cheapest_alternative_price: Decimal | None
    cheapest_overall_price: Decimal | None
    created_at: datetime
    updated_at: datetime


class CampaignResponse(CampaignSummaryResponse):
    configuration: CampaignConfigurationResponse


class DealerOfferFeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    feature_key: str
    feature_value: str | None
    normalized_key: str
    normalized_value: str | None
    display_label: str | None
    is_available: bool


class DealerOfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    dealer_name: str
    dealer_reference: str | None
    source_type: str
    currency: str
    vehicle_price: Decimal | None
    transfer_cost: Decimal | None
    registration_cost: Decimal | None
    total_price: Decimal | None
    cash_price: Decimal | None
    financing_required: bool | None
    financing_total_cost: Decimal | None
    delivery_date: date | None
    production_date: date | None
    model_year: int | None
    holding_period_months: int | None
    day_registration: bool | None
    trade_in_required: bool | None
    offer_valid_until: date | None
    raw_response: str
    extracted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    features: list[DealerOfferFeatureResponse]


class RequirementMatchResponse(BaseModel):
    requirement_id: UUID
    feature_key: str
    expected_value: str | None
    actual_value: str | None
    status: Literal["exact", "alternative", "missing", "incompatible"]
    is_mandatory: bool


class OfferComparisonResponse(BaseModel):
    offer_id: UUID
    dealer_name: str
    category: Literal["exact", "alternative", "incompatible"]
    score: int
    total_price: Decimal | None
    price_delta_to_cheapest_overall: Decimal | None
    price_delta_to_cheapest_exact: Decimal | None
    price_delta_to_cheapest_alternative: Decimal | None
    is_cheapest_exact: bool = False
    is_cheapest_alternative: bool = False
    is_cheapest_overall: bool = False
    matches: list[RequirementMatchResponse]


class CampaignComparisonResponse(BaseModel):
    campaign: CampaignResponse
    ranked_offers: list[OfferComparisonResponse]
    cheapest_exact_offer_id: UUID | None
    cheapest_alternative_offer_id: UUID | None
    cheapest_overall_offer_id: UUID | None
