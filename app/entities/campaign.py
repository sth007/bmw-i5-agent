from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Campaign(Base):
    __tablename__ = "campaign"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    config_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
        server_default="draft",
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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


from app.entities.campaign_configuration import CampaignConfiguration  # noqa: E402
from app.entities.dealer_offer import DealerOffer  # noqa: E402
