from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, DateTime, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Campaign(Base):
    __tablename__ = "campaign"
    __table_args__ = (
        UniqueConstraint("singleton_key", name="uq_campaign_singleton"),
        CheckConstraint("singleton_key = 1", name="ck_campaign_singleton_key"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    singleton_key: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    config_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="DRAFT",
        server_default="DRAFT",
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    completion_execution_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cheapest_exact_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    cheapest_alternative_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    cheapest_overall_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
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

    configuration: Mapped["CampaignConfiguration | None"] = relationship(
        back_populates="campaign",
        uselist=False,
        cascade="all, delete-orphan",
    )
    offers: Mapped[list["DealerOffer"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="DealerOffer.created_at.desc()",
    )
    contacts: Mapped[list["CampaignDealerContact"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="CampaignDealerContact.created_at.asc()",
    )
    inbound_emails: Mapped[list["InboundEmail"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="InboundEmail.created_at.desc()",
    )


from app.entities.campaign_configuration import CampaignConfiguration  # noqa: E402
from app.entities.campaign_dealer_contact import CampaignDealerContact  # noqa: E402
from app.entities.dealer_offer import DealerOffer  # noqa: E402
from app.entities.inbound_email import InboundEmail  # noqa: E402
