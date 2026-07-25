from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CampaignDealerContact(Base):
    __tablename__ = "campaign_dealer_contact"
    __table_args__ = (
        UniqueConstraint("campaign_id", "dealer_id", name="uq_campaign_dealer_contact_campaign_dealer"),
        UniqueConstraint("outbound_message_key", name="uq_campaign_dealer_contact_outbound_message_key"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("campaign.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dealer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dealer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="PENDING")
    reservation_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    recipient_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    rendered_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    outbound_message_key: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    internet_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
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

    campaign: Mapped["Campaign"] = relationship(back_populates="contacts")
    dealer: Mapped["Dealer"] = relationship(back_populates="campaign_contacts")
    inbound_emails: Mapped[list["InboundEmail"]] = relationship(back_populates="contact")


from app.entities.campaign import Campaign  # noqa: E402
from app.entities.dealer import Dealer  # noqa: E402
from app.entities.inbound_email import InboundEmail  # noqa: E402
