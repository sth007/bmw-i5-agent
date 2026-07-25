from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.campaign import (
    InboundEmailDebugMatchResponse,
    InboundEmailCreateRequest,
    InboundEmailResponse,
    InboundOfferExtractionRequest,
    InboundOfferExtractionResponse,
    ReviewQueueItemResponse,
)
from app.services.campaign_contact_service import CampaignContactService


router = APIRouter(prefix="/api/inbound-emails", tags=["inbound-emails"])
review_router = APIRouter(prefix="/api", tags=["inbound-emails"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=InboundEmailResponse, status_code=status.HTTP_201_CREATED)
def register_inbound_email(
    payload: InboundEmailCreateRequest,
    response: Response,
    db: DatabaseSession,
) -> InboundEmailResponse:
    service = CampaignContactService(db)
    existing = service.inbound_repository.get_by_provider_message(payload.provider, payload.provider_message_id)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return service._build_inbound_response(existing)
    try:
        return service.register_inbound_email(payload)
    except ValueError as exc:
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY if "campaign_id_hint" in str(exc) else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post(
    "/{inbound_email_id}/extract-offer",
    response_model=InboundOfferExtractionResponse,
    status_code=status.HTTP_200_OK,
)
def extract_offer(
    inbound_email_id: UUID,
    payload: InboundOfferExtractionRequest,
    db: DatabaseSession,
) -> InboundOfferExtractionResponse:
    service = CampaignContactService(db)
    try:
        return service.extract_offer(inbound_email_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{inbound_email_id}/debug-match", response_model=InboundEmailDebugMatchResponse)
def debug_match(
    inbound_email_id: UUID,
    db: DatabaseSession,
) -> InboundEmailDebugMatchResponse:
    service = CampaignContactService(db)
    try:
        return service.debug_match(inbound_email_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def _review_queue(
    db: DatabaseSession,
    campaign_id: UUID | None = Query(default=None),
) -> list[ReviewQueueItemResponse]:
    service = CampaignContactService(db)
    return service.review_queue(campaign_id)


@router.get("/review-queue", response_model=list[ReviewQueueItemResponse])
def review_queue(
    db: DatabaseSession,
    campaign_id: UUID | None = Query(default=None),
) -> list[ReviewQueueItemResponse]:
    return _review_queue(db, campaign_id)


@review_router.get("/review-queue", response_model=list[ReviewQueueItemResponse])
def review_queue_compat(
    db: DatabaseSession,
    campaign_id: UUID | None = Query(default=None),
) -> list[ReviewQueueItemResponse]:
    return _review_queue(db, campaign_id)
