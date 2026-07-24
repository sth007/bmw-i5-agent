from sqlalchemy import select
from sqlalchemy.orm import Session

from app.entities.offer import Offer


class OfferRepository:
    """Repository für öffentlich gefundene Fahrzeugangebote."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, offer_id: int) -> Offer | None:
        return self.db.get(Offer, offer_id)

    def get_by_external_id(
        self,
        source: str,
        external_id: str,
    ) -> Offer | None:
        statement = select(Offer).where(
            Offer.source == source,
            Offer.external_id == external_id,
        )

        return self.db.execute(
            statement
        ).scalar_one_or_none()

    def list_all(self) -> list[Offer]:
        statement = select(Offer).order_by(
            Offer.id,
        )

        return list(
            self.db.scalars(statement)
        )

    def add(self, offer: Offer) -> Offer:
        self.db.add(offer)
        return offer

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, offer: Offer) -> None:
        self.db.refresh(offer)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()