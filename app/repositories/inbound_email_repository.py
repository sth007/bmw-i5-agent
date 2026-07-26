from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.entities.inbound_email import InboundEmail


class InboundEmailRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, inbound_email: InboundEmail) -> InboundEmail:
        self.db.add(inbound_email)
        self.db.flush()
        return inbound_email

    def get(self, inbound_email_id: UUID) -> InboundEmail | None:
        statement = (
            select(InboundEmail)
            .options(
                joinedload(InboundEmail.contact).joinedload(CampaignDealerContact.dealer),
                joinedload(InboundEmail.dealer),
                joinedload(InboundEmail.offers),
            )
            .where(InboundEmail.id == inbound_email_id)
        )
        return self.db.execute(statement).unique().scalar_one_or_none()

    def get_by_provider_message(self, provider: str, provider_message_id: str) -> InboundEmail | None:
        statement = select(InboundEmail).where(
            InboundEmail.provider == provider,
            InboundEmail.provider_message_id == provider_message_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def list_review_queue(self, campaign_id: UUID | None) -> list[InboundEmail]:
        statement = select(InboundEmail).where(
            InboundEmail.processing_status.in_(["NEEDS_REVIEW", "EXTRACTION_FAILED"]),
        )
        if campaign_id is not None:
            statement = statement.where(InboundEmail.campaign_id == campaign_id)
        statement = statement.order_by(InboundEmail.received_at.desc())
        return list(self.db.execute(statement).scalars())

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()


from app.entities.campaign_dealer_contact import CampaignDealerContact  # noqa: E402
