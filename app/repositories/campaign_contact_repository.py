from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.entities.campaign_dealer_contact import CampaignDealerContact


class CampaignContactRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, contact: CampaignDealerContact) -> CampaignDealerContact:
        self.db.add(contact)
        self.db.flush()
        return contact

    def add_all(self, contacts: list[CampaignDealerContact]) -> None:
        self.db.add_all(contacts)
        self.db.flush()

    def get(self, contact_id: UUID) -> CampaignDealerContact | None:
        statement = (
            select(CampaignDealerContact)
            .options(joinedload(CampaignDealerContact.dealer))
            .where(CampaignDealerContact.id == contact_id)
        )
        return self.db.execute(statement).unique().scalar_one_or_none()

    def get_by_outbound_key(self, outbound_message_key: str) -> CampaignDealerContact | None:
        statement = (
            select(CampaignDealerContact)
            .options(joinedload(CampaignDealerContact.dealer))
            .where(CampaignDealerContact.outbound_message_key == outbound_message_key)
        )
        return self.db.execute(statement).unique().scalar_one_or_none()

    def get_by_campaign_and_dealer(
        self,
        campaign_id: UUID,
        dealer_id: int,
    ) -> CampaignDealerContact | None:
        statement = (
            select(CampaignDealerContact)
            .options(joinedload(CampaignDealerContact.dealer))
            .where(
                CampaignDealerContact.campaign_id == campaign_id,
                CampaignDealerContact.dealer_id == dealer_id,
            )
            .order_by(CampaignDealerContact.created_at.desc())
        )
        return self.db.execute(statement).unique().scalar_one_or_none()

    def list_by_campaign_dealer_ids(
        self,
        campaign_id: UUID,
        dealer_ids: list[int],
    ) -> list[CampaignDealerContact]:
        if not dealer_ids:
            return []
        statement = select(CampaignDealerContact).where(
            CampaignDealerContact.campaign_id == campaign_id,
            CampaignDealerContact.dealer_id.in_(dealer_ids),
        )
        return list(self.db.execute(statement).scalars())

    def list_open_for_campaign(self, campaign_id: UUID) -> list[CampaignDealerContact]:
        statement = (
            select(CampaignDealerContact)
            .options(joinedload(CampaignDealerContact.dealer))
            .where(
                CampaignDealerContact.campaign_id == campaign_id,
                CampaignDealerContact.recipient_email.is_not(None),
                CampaignDealerContact.status.in_(
                    [
                        "SENT",
                        "REPLIED",
                        "OFFER_EXTRACTED",
                        "NEEDS_REVIEW",
                        "SEND_STATE_UNKNOWN",
                    ]
                ),
            )
            .order_by(CampaignDealerContact.created_at.desc())
        )
        return list(self.db.execute(statement).unique().scalars())

    def list_pending_for_update(self, campaign_id: UUID, limit: int) -> list[CampaignDealerContact]:
        statement = (
            select(CampaignDealerContact.id)
            .where(
                CampaignDealerContact.campaign_id == campaign_id,
                CampaignDealerContact.status == "PENDING",
            )
            .order_by(CampaignDealerContact.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
        ids = list(self.db.execute(statement).scalars())
        if not ids:
            return []
        load_statement = (
            select(CampaignDealerContact)
            .options(joinedload(CampaignDealerContact.dealer))
            .where(CampaignDealerContact.id.in_(ids))
            .order_by(CampaignDealerContact.created_at.asc())
        )
        return list(self.db.execute(load_statement).unique().scalars())

    def list_by_provider_thread(
        self,
        provider: str,
        provider_thread_id: str,
        campaign_id: UUID | None = None,
    ) -> list[CampaignDealerContact]:
        statement = (
            select(CampaignDealerContact)
            .options(joinedload(CampaignDealerContact.dealer))
            .where(
                CampaignDealerContact.provider == provider,
                CampaignDealerContact.provider_thread_id == provider_thread_id,
            )
        )
        if campaign_id is not None:
            statement = statement.where(CampaignDealerContact.campaign_id == campaign_id)
        statement = statement.order_by(CampaignDealerContact.created_at.desc())
        return list(self.db.execute(statement).unique().scalars())

    def list_by_message_identifiers(
        self,
        identifiers: list[str],
        campaign_id: UUID | None = None,
    ) -> list[CampaignDealerContact]:
        identifiers = [value for value in identifiers if value]
        if not identifiers:
            return []
        statement = (
            select(CampaignDealerContact)
            .options(joinedload(CampaignDealerContact.dealer))
            .where(
                or_(
                    CampaignDealerContact.internet_message_id.in_(identifiers),
                    CampaignDealerContact.provider_message_id.in_(identifiers),
                )
            )
            .order_by(CampaignDealerContact.created_at.desc())
        )
        if campaign_id is not None:
            statement = statement.where(CampaignDealerContact.campaign_id == campaign_id)
        return list(self.db.execute(statement).unique().scalars())

    def list_open_by_sender_email(
        self,
        sender_email: str,
        campaign_id: UUID | None = None,
    ) -> list[CampaignDealerContact]:
        contacts = self.list_open_for_campaign(campaign_id) if campaign_id is not None else list(
            self.db.execute(
                select(CampaignDealerContact)
                .options(joinedload(CampaignDealerContact.dealer))
                .where(
                    CampaignDealerContact.recipient_email.is_not(None),
                    CampaignDealerContact.status.in_(
                        [
                            "SENT",
                            "REPLIED",
                            "OFFER_EXTRACTED",
                            "NEEDS_REVIEW",
                            "SEND_STATE_UNKNOWN",
                        ]
                    ),
                )
                .order_by(CampaignDealerContact.created_at.desc())
            ).unique().scalars()
        )
        target = sender_email.strip().lower()
        return [
            contact
            for contact in contacts
            if contact.dealer
            and any(
                email and email.strip().lower() == target
                for email in [
                    contact.dealer.email,
                    contact.dealer.new_car_email,
                    contact.dealer.used_car_email,
                ]
            )
        ]

    def list_review_queue(self, campaign_id: UUID | None) -> list[CampaignDealerContact]:
        statement = select(CampaignDealerContact).options(joinedload(CampaignDealerContact.dealer)).where(
            CampaignDealerContact.status.in_(["NEEDS_REVIEW", "SEND_STATE_UNKNOWN", "SEND_FAILED"])
        )
        if campaign_id is not None:
            statement = statement.where(CampaignDealerContact.campaign_id == campaign_id)
        statement = statement.order_by(CampaignDealerContact.updated_at.desc())
        return list(self.db.execute(statement).unique().scalars())

    def status_counts(self, campaign_id: UUID) -> dict[str, int]:
        statement = (
            select(CampaignDealerContact.status, func.count(CampaignDealerContact.id))
            .where(CampaignDealerContact.campaign_id == campaign_id)
            .group_by(CampaignDealerContact.status)
        )
        return {status: count for status, count in self.db.execute(statement).all()}

    def total_count(self, campaign_id: UUID) -> int:
        statement = select(func.count(CampaignDealerContact.id)).where(CampaignDealerContact.campaign_id == campaign_id)
        return int(self.db.execute(statement).scalar_one())

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
