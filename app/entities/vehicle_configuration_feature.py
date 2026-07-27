from __future__ import annotations

from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class VehicleConfigurationFeature(Base):
    __tablename__ = "vehicle_configuration_feature"
    __table_args__ = (
        UniqueConstraint("configuration_id", "feature_key", "feature_code", "sort_order", name="uq_vehicle_configuration_feature"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    configuration_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vehicle_configuration.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    feature_key: Mapped[str] = mapped_column(String(120), nullable=False)
    feature_value: Mapped[str] = mapped_column(Text, nullable=False)
    display_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_standard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa.false())
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa.false())
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    configuration: Mapped["VehicleConfiguration"] = relationship(back_populates="features")


from app.entities.vehicle_configuration import VehicleConfiguration  # noqa: E402
