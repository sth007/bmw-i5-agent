from app.services.offer_extractor import OfferExtractor
from app.domain.dealer_offer import DealerOffer
from app.repositories.offer_repository import OfferRepository


class OfferService:

    def __init__(self):
        self.repository = OfferRepository()

    def extract_offer(
        self,
        *,
        text: str,
        campaign_id: str,
        configuration_id: str,
        dealer_id: str,
        email_subject: str | None = None,
        email_text: str | None = None,
        pdf_filename: str | None = None,
    ) -> DealerOffer:

        extractor = OfferExtractor(text)

        offer = extractor.extract(
            campaign_id=campaign_id,
            configuration_id=configuration_id,
            dealer_id=dealer_id,
            email_subject=email_subject,
            email_text=email_text,
            pdf_filename=pdf_filename,
        )

        self.repository.save(offer)

        return offer