from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class InboundEmail(Base):
    __tablename__ = "inbound_email"
    __table_args__ = (
        UniqueConstraint("provider", "provider_message_id", name="uq_inbound_email_provider_message"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("campaign.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dealer_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("dealer.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_dealer_contact_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("campaign_dealer_contact.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mailbox_address: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    internet_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    references: Mapped[str | None] = mapped_column(Text, nullable=True)
    sender_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="RECEIVED", index=True)
    matching_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNMATCHED", index=True)
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    campaign: Mapped["Campaign | None"] = relationship(back_populates="inbound_emails")
    dealer: Mapped["Dealer | None"] = relationship(back_populates="inbound_emails")
    contact: Mapped["CampaignDealerContact | None"] = relationship(back_populates="inbound_emails")
    offers: Mapped[list["DealerOffer"]] = relationship(back_populates="inbound_email")


from app.entities.campaign import Campaign  # noqa: E402
from app.entities.campaign_dealer_contact import CampaignDealerContact  # noqa: E402
from app.entities.dealer import Dealer  # noqa: E402
from app.entities.dealer_offer import DealerOffer  # noqa: E402
