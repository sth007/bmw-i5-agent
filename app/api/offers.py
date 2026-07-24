from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.offer import OfferImport, OfferImportResult
from app.schemas.offer_requests import ExtractOfferRequest
from app.services.import_coordinator import ImportCoordinator
from app.services.offer_service import OfferService


router = APIRouter(
    prefix="/offers",
    tags=["offers"],
)

extract_service = OfferService()

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("/extract")
def extract_offer(request: ExtractOfferRequest):
    offer = extract_service.extract_offer(
        text=request.text,
        campaign_id=request.campaign_id,
        configuration_id=request.configuration_id,
        dealer_id=request.dealer_id,
        email_subject=request.email_subject,
        email_text=request.email_text,
        pdf_filename=request.pdf_filename,
    )

    return offer.model_dump(mode="json")


@router.post(
    "/import",
    response_model=OfferImportResult,
)
def import_offers(
    offers: list[OfferImport],
    db: DatabaseSession,
) -> OfferImportResult:
    coordinator = ImportCoordinator(db)

    return coordinator.import_offers(offers)