from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Date, DateTime, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class VehicleConfiguration(Base):
    __tablename__ = "vehicle_configuration"
    __table_args__ = (
        UniqueConstraint("provider", "configuration_id", "effect_date", name="uq_vehicle_configuration_provider_id_date"),
        UniqueConstraint("provider", "resolved_url_hash", name="uq_vehicle_configuration_provider_hash"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_url_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(32), nullable=False)
    series_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    model_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    variant: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body: Mapped[str | None] = mapped_column(String(120), nullable=True)
    paint_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    paint_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    upholstery_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    upholstery_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    list_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR", server_default="EUR")
    effect_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    normalized_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
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

    features: Mapped[list["VehicleConfigurationFeature"]] = relationship(
        back_populates="configuration",
        cascade="all, delete-orphan",
        order_by="VehicleConfigurationFeature.sort_order.asc()",
    )
    campaign_configurations: Mapped[list["CampaignConfiguration"]] = relationship(back_populates="vehicle_configuration")


from app.entities.campaign_configuration import CampaignConfiguration  # noqa: E402
from app.entities.vehicle_configuration_feature import VehicleConfigurationFeature  # noqa: E402
