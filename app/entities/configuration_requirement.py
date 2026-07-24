from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ConfigurationRequirement(Base):
    __tablename__ = "configuration_requirement"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    configuration_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("campaign_configuration.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_key: Mapped[str] = mapped_column(String(120), nullable=False)
    feature_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    normalized_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    display_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=sa.true(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    configuration: Mapped["CampaignConfiguration"] = relationship(back_populates="requirements")


from app.entities.campaign_configuration import CampaignConfiguration  # noqa: E402
