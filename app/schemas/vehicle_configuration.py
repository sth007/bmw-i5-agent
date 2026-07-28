from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.bmw_configuration import ResolvedBMWConfiguration


class BMWConfigurationParseRequest(BaseModel):
    configuration_url: str = Field(min_length=1)


class ParsedFeatureRequirement(BaseModel):
    feature_key: str
    feature_value: str
    feature_code: str | None = None
    display_label: str | None = None
    is_mandatory: bool = False


class ParsedConfigurationSelection(BaseModel):
    code: str
    name: str | None = None
    category: str
    is_standard: bool = False
    is_resolved: bool = True


class ParsedChoice(BaseModel):
    code: str
    name: str | None = None


class ParsedConfigurationSection(BaseModel):
    paint: ParsedChoice | None = None
    upholstery: ParsedChoice | None = None
    options: list[ParsedConfigurationSelection] = Field(default_factory=list)


class ParserMetadata(BaseModel):
    provider: str
    version: str
    status: str
    warnings: list[str] = Field(default_factory=list)


class ParsedSource(BaseModel):
    original_url: str
    resolved_url: str
    configuration_id: str | None = None
    effect_date: date | None = None


class ParsedVehicle(BaseModel):
    brand: str
    series_code: str | None = None
    model_code: str | None = None
    model_name: str | None = None
    variant: str | None = None
    body: str | None = None


class ParsedPricing(BaseModel):
    list_price: Decimal | None = None
    currency: str = "EUR"


class DealerRequestPayload(BaseModel):
    subject: str
    configuration_text: str


class BMWConfigurationParseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parser: ParserMetadata
    source: ParsedSource
    vehicle: ParsedVehicle
    pricing: ParsedPricing
    configuration: ParsedConfigurationSection
    resolved_configuration: ResolvedBMWConfiguration
    requirements: list[ParsedFeatureRequirement]
    dealer_request: DealerRequestPayload


class VehicleConfigurationFeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    feature_code: str | None
    feature_key: str
    feature_value: str
    display_label: str | None
    category: str | None
    is_standard: bool
    is_mandatory: bool
    sort_order: int
    raw_data: dict | None


class VehicleConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    configuration_id: str | None
    original_url: str
    resolved_url: str | None
    brand: str
    series_code: str | None
    model_code: str | None
    model_name: str | None
    variant: str | None
    body: str | None
    paint_code: str | None
    paint_name: str | None
    upholstery_code: str | None
    upholstery_name: str | None
    list_price: Decimal | None
    currency: str
    effect_date: date | None
    parse_status: str
    parser_version: str
    normalized_data: dict
    created_at: datetime
    updated_at: datetime
    features: list[VehicleConfigurationFeatureResponse]
