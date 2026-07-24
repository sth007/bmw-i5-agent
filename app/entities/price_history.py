from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    offer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "offer.id",
            name="fk_price_history_offer_id_offer",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="EUR",
        server_default="EUR",
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=sa.func.now(),
        index=True,
    )