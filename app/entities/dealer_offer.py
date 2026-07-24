from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class DealerOffer(Base):
    __tablename__ = "dealer_offer"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("campaign.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dealer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dealer_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="manual",
        server_default="manual",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="EUR",
        server_default="EUR",
    )
    vehicle_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    transfer_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    registration_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, index=True)
    cash_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    financing_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    financing_total_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    production_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    model_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    holding_period_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_registration: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    trade_in_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    offer_valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    campaign: Mapped["Campaign"] = relationship(back_populates="offers")
    features: Mapped[list["DealerOfferFeature"]] = relationship(
        back_populates="offer",
        cascade="all, delete-orphan",
        order_by="DealerOfferFeature.created_at.asc()",
    )


from app.entities.campaign import Campaign  # noqa: E402
from app.entities.dealer_offer_feature import DealerOfferFeature  # noqa: E402
