from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.entities.dealer_offer import DealerOffer


class DealerOfferRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, offer: DealerOffer) -> DealerOffer:
        self.db.add(offer)
        self.db.flush()
        return offer

    def get(self, offer_id: UUID) -> DealerOffer | None:
        statement = (
            select(DealerOffer)
            .options(joinedload(DealerOffer.features))
            .where(DealerOffer.id == offer_id)
        )
        return self.db.execute(statement).unique().scalar_one_or_none()

    def list_by_campaign(self, campaign_id: UUID) -> list[DealerOffer]:
        statement = (
            select(DealerOffer)
            .options(joinedload(DealerOffer.features))
            .where(DealerOffer.campaign_id == campaign_id)
            .order_by(DealerOffer.created_at.desc())
        )
        return list(self.db.execute(statement).unique().scalars())

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
