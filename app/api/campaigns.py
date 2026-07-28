from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.campaign import (
    CampaignComparisonResponse,
    CampaignCompletionRequest,
    CampaignCompletionResponse,
    CampaignContactClaimRequest,
    CampaignContactClaimResponse,
    CampaignContactFailedRequest,
    CampaignContactSentRequest,
    CampaignContactStateResponse,
    CampaignCreate,
    CampaignCreateAndStartRequest,
    CampaignFromConfigRequest,
    CampaignFromPublicConfigRequest,
    CampaignStartRequest,
    CampaignStartResponse,
    CampaignResponse,
    CampaignStatusPatch,
    CampaignSummaryResponse,
    CampaignDispatchStatusResponse,
    DealerOfferCreate,
    DealerOfferExtractRequest,
    DealerOfferResponse,
    LatestRelevantCampaignResponse,
)
from app.services.campaign_comparison_service import CampaignComparisonService
from app.services.campaign_contact_service import CampaignContactService
from app.services.campaign_dispatch_service import CampaignCompletionBlockedError, CampaignDispatchService
from app.services.campaign_query_service import CampaignQueryService
from app.services.campaign_service import CampaignService
from app.services.dealer_offer_service import DealerOfferService, OfferExtractionService


router = APIRouter(prefix="/campaigns", tags=["campaigns"])
start_router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CampaignCreate, db: DatabaseSession) -> CampaignResponse:
    service = CampaignService(db)
    campaign = service.create_campaign(payload)
    return CampaignResponse.model_validate(campaign)


@router.get("", response_model=list[CampaignSummaryResponse])
def list_campaigns(db: DatabaseSession) -> list[CampaignSummaryResponse]:
    service = CampaignService(db)
    return [CampaignSummaryResponse.model_validate(item) for item in service.list_campaigns()]


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: UUID, db: DatabaseSession) -> CampaignResponse:
    service = CampaignService(db)
    campaign = service.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return CampaignResponse.model_validate(campaign)


@router.patch("/{campaign_id}/status", response_model=CampaignResponse)
def patch_campaign_status(
    campaign_id: UUID,
    payload: CampaignStatusPatch,
    db: DatabaseSession,
) -> CampaignResponse:
    service = CampaignService(db)
    campaign = service.update_status(campaign_id, payload)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return CampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/offers", response_model=DealerOfferResponse, status_code=status.HTTP_201_CREATED)
def create_offer(
    campaign_id: UUID,
    payload: DealerOfferCreate,
    db: DatabaseSession,
) -> DealerOfferResponse:
    service = DealerOfferService(db)
    try:
        offer = service.create_offer(campaign_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DealerOfferResponse.model_validate(offer)


@router.post(
    "/{campaign_id}/offers/extract",
    response_model=DealerOfferResponse,
    status_code=status.HTTP_201_CREATED,
)
def extract_offer(
    campaign_id: UUID,
    payload: DealerOfferExtractRequest,
    db: DatabaseSession,
) -> DealerOfferResponse:
    service = OfferExtractionService(db)
    try:
        offer = service.extract_and_create_offer(
            campaign_id=campaign_id,
            dealer_name=payload.dealer_name,
            dealer_reference=payload.dealer_reference,
            source_type=payload.source_type,
            text=payload.text,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DealerOfferResponse.model_validate(offer)


@router.get("/{campaign_id}/offers", response_model=list[DealerOfferResponse])
def list_offers(campaign_id: UUID, db: DatabaseSession) -> list[DealerOfferResponse]:
    service = DealerOfferService(db)
    return [DealerOfferResponse.model_validate(item) for item in service.list_offers(campaign_id)]


@router.get("/{campaign_id}/comparison", response_model=CampaignComparisonResponse)
def get_comparison(campaign_id: UUID, db: DatabaseSession) -> CampaignComparisonResponse:
    service = CampaignComparisonService(db)
    comparison = service.compare(campaign_id)
    if comparison is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return comparison


@start_router.post("/start", response_model=CampaignStartResponse, status_code=status.HTTP_201_CREATED)
def start_campaign(payload: CampaignStartRequest, db: DatabaseSession) -> CampaignStartResponse:
    service = CampaignService(db)
    try:
        return service.start_campaign(
            campaign_name=payload.campaign_name,
            config_url=payload.config_url,
            dealer_limit=payload.dealer_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email template rendering failed.",
        )


@start_router.post("/from-config", response_model=CampaignStartResponse, status_code=status.HTTP_201_CREATED)
def create_campaign_from_config(
    payload: CampaignFromConfigRequest,
    db: DatabaseSession,
) -> CampaignStartResponse:
    service = CampaignService(db)
    try:
        return service.create_from_config(
            campaign_name=payload.campaign_name,
            config_url=payload.effective_configuration_url,
            dealer_limit=payload.dealer_limit,
            customer=payload.customer,
            maximum_target_price=payload.maximum_target_price,
            payment_preference=payload.payment_preference,
            notes=payload.notes,
            email_body_template=payload.email_body_template,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email template rendering failed.",
        )


@start_router.post("/from-public-config", response_model=CampaignStartResponse, status_code=status.HTTP_201_CREATED)
def create_campaign_from_public_config(
    payload: CampaignFromPublicConfigRequest,
    db: DatabaseSession,
) -> CampaignStartResponse:
    service = CampaignService(db)
    try:
        return service.create_from_public_config(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email template rendering failed.",
        )


@start_router.post("/create-and-start", response_model=CampaignStartResponse, status_code=status.HTTP_201_CREATED)
def create_and_start_campaign(
    payload: CampaignCreateAndStartRequest,
    db: DatabaseSession,
) -> CampaignStartResponse:
    service = CampaignService(db)
    try:
        return service.create_and_start_campaign(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email template rendering failed.",
        )


@start_router.get("/latest-relevant", response_model=LatestRelevantCampaignResponse)
def latest_relevant_campaign(db: DatabaseSession) -> LatestRelevantCampaignResponse:
    service = CampaignQueryService(db)
    try:
        return service.get_latest_relevant_campaign()
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@start_router.post(
    "/{campaign_id}/contacts/claim",
    response_model=CampaignContactClaimResponse,
    status_code=status.HTTP_200_OK,
)
def claim_campaign_contacts(
    campaign_id: UUID,
    payload: CampaignContactClaimRequest,
    db: DatabaseSession,
) -> CampaignContactClaimResponse:
    service = CampaignContactService(db)
    try:
        return service.claim_contacts(campaign_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@start_router.get(
    "/{campaign_id}/dispatch-status",
    response_model=CampaignDispatchStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_campaign_dispatch_status(
    campaign_id: UUID,
    db: DatabaseSession,
) -> CampaignDispatchStatusResponse:
    service = CampaignDispatchService(db)
    try:
        return service.get_dispatch_status(campaign_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@start_router.post(
    "/{campaign_id}/complete",
    response_model=CampaignCompletionResponse,
    status_code=status.HTTP_200_OK,
)
def complete_campaign(
    campaign_id: UUID,
    db: DatabaseSession,
    payload: CampaignCompletionRequest | None = None,
):
    service = CampaignDispatchService(db)
    payload = payload or CampaignCompletionRequest()
    try:
        return service.complete_campaign(
            campaign_id,
            completed_by=payload.completed_by,
            execution_id=payload.n8n_execution_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CampaignCompletionBlockedError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": str(exc),
                "remaining_sendable_contacts": exc.pending,
                "remaining_reserved_contacts": exc.reserved,
                "remaining_failed_contacts": exc.failed,
            },
        )


contact_router = APIRouter(prefix="/api/campaign-contacts", tags=["campaigns"])


@contact_router.post("/{contact_id}/sent", response_model=CampaignContactStateResponse)
def mark_contact_sent(
    contact_id: UUID,
    payload: CampaignContactSentRequest,
    db: DatabaseSession,
) -> CampaignContactStateResponse:
    service = CampaignContactService(db)
    try:
        return service.mark_sent(contact_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@contact_router.post("/{contact_id}/send-failed", response_model=CampaignContactStateResponse)
def mark_contact_send_failed(
    contact_id: UUID,
    payload: CampaignContactFailedRequest,
    db: DatabaseSession,
) -> CampaignContactStateResponse:
    service = CampaignContactService(db)
    try:
        return service.mark_send_failed(contact_id, payload.error_message, payload.unknown_state)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
