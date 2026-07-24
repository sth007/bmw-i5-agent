from datetime import datetime
from decimal import Decimal
import sqlalchemy as sa

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Offer(Base):
    __tablename__ = "offer"

    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_offer_source_external_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    external_id: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    dealer_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "dealer.id",
            name="fk_offer_dealer_id_dealer",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    variant: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="EUR",
        server_default="EUR",
        nullable=False,
    )

    mileage_km: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    first_registration: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    power_kw: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    fuel_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    transmission: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    drivetrain: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    color: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    vin: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        index=True,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=sa.func.now(),
        nullable=False,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=sa.func.now(),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=sa.func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=sa.func.now(),
        nullable=False,
    )