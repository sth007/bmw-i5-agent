from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CampaignConfiguration(Base):
    __tablename__ = "campaign_configuration"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("campaign.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    configuration_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    variant: Mapped[str] = mapped_column(String(120), nullable=False)
    package: Mapped[str | None] = mapped_column(String(120), nullable=True)
    list_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    maximum_target_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_preference: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="either",
        server_default="either",
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

    campaign: Mapped["Campaign"] = relationship(back_populates="configuration")
    requirements: Mapped[list["ConfigurationRequirement"]] = relationship(
        back_populates="configuration",
        cascade="all, delete-orphan",
        order_by="ConfigurationRequirement.created_at.asc()",
    )


from app.entities.campaign import Campaign  # noqa: E402
from app.entities.configuration_requirement import ConfigurationRequirement  # noqa: E402
