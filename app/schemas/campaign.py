from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


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


class CampaignStartRequest(BaseModel):
    campaign_name: str = Field(min_length=1, max_length=200)
    config_url: str = Field(min_length=1)
    dealer_limit: int = Field(default=3, ge=1, le=100)


class CampaignCustomerInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = None


class CampaignFromConfigRequest(BaseModel):
    campaign_name: str = Field(min_length=1, max_length=200)
    config_url: str = Field(min_length=1)
    dealer_limit: int = Field(default=3, ge=1, le=100)
    customer: CampaignCustomerInput


class CampaignCreateAndStartRequest(BaseModel):
    campaign_name: str = Field(min_length=1, max_length=200)
    dealer_limit: int = Field(default=3, ge=1, le=100)
    customer: CampaignCustomerInput
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
    config_url: str | None
    config_id: str | None
    status: str
    notes: str | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    cheapest_exact_price: Decimal | None
    cheapest_alternative_price: Decimal | None
    cheapest_overall_price: Decimal | None
    created_at: datetime
    updated_at: datetime


class CampaignResponse(CampaignSummaryResponse):
    configuration: CampaignConfigurationResponse | None


class CampaignStartDealerResponse(BaseModel):
    dealer_id: int
    name: str
    city: str | None
    email: str


class CampaignEmailPreviewResponse(BaseModel):
    dealer_id: int
    dealer_name: str | None
    to: EmailStr
    subject: str
    body: str


class CampaignStartResponse(BaseModel):
    campaign_id: UUID
    campaign_name: str
    config_url: str
    config_id: str
    status: str
    dealers: list[CampaignStartDealerResponse]
    email_previews: list[CampaignEmailPreviewResponse]
    warnings: list[str] = Field(default_factory=list)


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


class CampaignContactClaimRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)
    reservation_owner: str = Field(min_length=1, max_length=120)
    test_mode: bool = False
    test_recipient: EmailStr | None = None


class CampaignContactClaimItemResponse(BaseModel):
    contact_id: UUID
    campaign_id: UUID
    dealer_id: int
    dealer_name: str
    outbound_message_key: str
    subject: str
    body: str
    effective_to: EmailStr
    recipient_email: EmailStr | None
    test_mode: bool
    test_email: EmailStr | None = None


class CampaignContactClaimResponse(BaseModel):
    campaign_id: UUID
    contacts: list[CampaignContactClaimItemResponse]


class CampaignContactSentRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=32)
    provider_message_id: str = Field(min_length=1, max_length=255)
    provider_thread_id: str | None = Field(default=None, max_length=255)
    internet_message_id: str | None = Field(default=None, max_length=255)
    sent_to: EmailStr
    test_mode: bool = False
    n8n_execution_id: str | None = Field(default=None, max_length=120)


class CampaignContactFailedRequest(BaseModel):
    error_message: str = Field(min_length=1)
    unknown_state: bool = False


class CampaignContactStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    dealer_id: int
    status: str
    reservation_owner: str | None
    reserved_at: datetime | None
    sent_at: datetime | None
    replied_at: datetime | None
    last_error: str | None
    recipient_email: str | None
    original_subject: str | None
    outbound_message_key: str
    provider: str | None
    provider_message_id: str | None
    provider_thread_id: str | None
    internet_message_id: str | None
    created_at: datetime
    updated_at: datetime


class InboundEmailCreateRequest(BaseModel):
    campaign_id_hint: UUID | None = None
    mailbox_address: EmailStr
    provider: str = Field(min_length=1, max_length=32)
    provider_message_id: str = Field(min_length=1, max_length=255)
    provider_thread_id: str | None = Field(default=None, max_length=255)
    internet_message_id: str | None = Field(default=None, max_length=255)
    in_reply_to: str | None = None
    references: str | None = None
    sender_raw: str | None = Field(default=None, max_length=1000)
    sender_email: str | None = Field(default=None, max_length=255)
    sender_name: str | None = Field(default=None, max_length=255)
    subject: str | None = None
    text_body: str | None = None
    html_body: str | None = None
    received_at: datetime
    raw_metadata: dict | None = None


class InboundEmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID | None
    dealer_id: int | None
    campaign_dealer_contact_id: UUID | None
    mailbox_address: str
    provider: str
    provider_message_id: str
    provider_thread_id: str | None
    internet_message_id: str | None
    sender_email: str | None
    subject: str | None
    received_at: datetime
    processing_status: str
    matching_status: str
    message_type: str | None = None
    extraction_confidence: Decimal | None = None
    extraction_reason: str | None = None
    processed_at: datetime | None = None
    can_extract: bool = False
    created_at: datetime
    updated_at: datetime


class InboundOfferExtractionRequest(BaseModel):
    attachment_text: list[str] = Field(default_factory=list)
    force_reextract: bool = False


class InboundOfferExtractionResponse(BaseModel):
    inbound_email_id: UUID
    processing_result: str
    message_type: str
    confidence: Decimal
    offer: dict | None
    reason: str | None
    status: str
    gross_final_price: Decimal | None
    currency: str | None
    price_confidence: Decimal | None
    needs_review: bool
    review_reason: str | None
    dealer_offer_id: UUID | None


class ReviewQueueItemResponse(BaseModel):
    item_type: Literal["contact", "inbound_email"]
    campaign_id: UUID | None
    dealer_id: int | None
    contact_id: UUID | None
    inbound_email_id: UUID | None
    dealer_offer_id: UUID | None
    status: str
    reason: str
    subject: str | None
    sender_email: str | None
    created_at: datetime


class DebugMatchCandidateResponse(BaseModel):
    contact_id: UUID | None = None
    dealer_id: int | None = None
    dealer: str
    status: str
    score: int | None = None
    reasons: list[str] = Field(default_factory=list)


class InboundEmailDebugMatchResponse(BaseModel):
    inbound_email_id: UUID
    matching_status: str
    campaign_id: UUID | None
    dealer_id: int | None
    campaign_dealer_contact_id: UUID | None
    provider_thread_id: str | None
    in_reply_to: str | None
    references: str | None
    subject: str | None
    sender_email: str | None
    matching_method: str | None = None
    matching_score: int | None = None
    matching_candidate_count: int = 0
    matching_reasons: list[str] = Field(default_factory=list)
    checked: dict[str, bool]
    candidate_contacts: list[DebugMatchCandidateResponse]


class CampaignCompletionRequest(BaseModel):
    completed_by: str | None = Field(default=None, max_length=120)
    n8n_execution_id: str | None = Field(default=None, max_length=120)


class CampaignCompletionResponse(BaseModel):
    campaign_id: UUID
    status: str
    completed_at: datetime
    remaining_sendable_contacts: int


class CampaignDispatchStatusResponse(BaseModel):
    campaign_id: UUID
    campaign_status: str
    total_contacts: int
    pending: int
    reserved: int
    sent: int
    replied: int
    offer_extracted: int
    needs_review: int
    skipped: int
    send_failed: int
    send_state_unknown: int
    has_more_sendable_contacts: bool
    can_complete: bool


class LatestRelevantCampaignResponse(BaseModel):
    campaign_id: UUID
    campaign_name: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None


class AdminResetRequest(BaseModel):
    scope: Literal["campaign_data", "all_application_data"] = "campaign_data"
    confirm: str | None = None


class AdminResetResponse(BaseModel):
    status: Literal["RESET_COMPLETED"]
    scope: Literal["campaign_data", "all_application_data"]
    deleted: dict[str, int]
    completed_at: datetime


class AdminResetStatusResponse(BaseModel):
    environment: str
    reset_enabled: bool
    campaign_count: int
    dealer_count: int
    inbound_email_count: int
    dealer_offer_count: int
