from sqlalchemy.orm import Session

from app.schemas.offer import OfferImport, OfferImportResult
from app.services.offer_import_service import OfferImportService


class ImportCoordinator:

    def __init__(self, db: Session):
        self.offer_service = OfferImportService(db)

    def import_offers(
        self,
        offers: list[OfferImport],
    ) -> OfferImportResult:
        return self.offer_service.import_offers(offers)