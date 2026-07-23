from fastapi import APIRouter

from app.services.offer_service import OfferService
from app.schemas.offer_requests import ExtractOfferRequest

router = APIRouter(prefix="/offers", tags=["offers"])

service = OfferService()


@router.post("/extract")
def extract_offer(request: ExtractOfferRequest):
    offer = service.extract_offer(
        text=request.text,
        campaign_id=request.campaign_id,
        configuration_id=request.configuration_id,
        dealer_id=request.dealer_id,
        email_subject=request.email_subject,
        email_text=request.email_text,
        pdf_filename=request.pdf_filename,
    )

    return offer.model_dump(mode="json")