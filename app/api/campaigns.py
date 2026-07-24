from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.campaign import (
    CampaignComparisonResponse,
    CampaignCreate,
    CampaignResponse,
    CampaignStatusPatch,
    CampaignSummaryResponse,
    DealerOfferCreate,
    DealerOfferExtractRequest,
    DealerOfferResponse,
)
from app.services.campaign_comparison_service import CampaignComparisonService
from app.services.campaign_service import CampaignService
from app.services.dealer_offer_service import DealerOfferService, OfferExtractionService


router = APIRouter(prefix="/campaigns", tags=["campaigns"])
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
