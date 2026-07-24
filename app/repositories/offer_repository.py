from sqlalchemy import select
from sqlalchemy.orm import Session

from app.entities.offer import Offer


class OfferRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, offer_id: int) -> Offer | None:
        return self.db.get(Offer, offer_id)

    def get_by_external_id(
        self,
        source: str,
        external_id: str,
    ) -> Offer | None:

        stmt = (
            select(Offer)
            .where(Offer.source == source)
            .where(Offer.external_id == external_id)
        )

        return self.db.execute(stmt).scalar_one_or_none()

    def get_all(self) -> list[Offer]:
        stmt = (
            select(Offer)
            .order_by(Offer.id)
        )

        return list(self.db.scalars(stmt))

    def add(self, offer: Offer) -> None:
        self.db.add(offer)

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, offer: Offer) -> None:
        self.db.refresh(offer)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()