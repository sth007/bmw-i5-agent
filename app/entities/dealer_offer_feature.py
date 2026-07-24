from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class DealerOfferFeature(Base):
    __tablename__ = "dealer_offer_feature"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    offer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("dealer_offer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_key: Mapped[str] = mapped_column(String(120), nullable=False)
    feature_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    normalized_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    display_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_available: Mapped[bool] = mapped_column(
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

    offer: Mapped["DealerOffer"] = relationship(back_populates="features")


from app.entities.dealer_offer import DealerOffer  # noqa: E402
