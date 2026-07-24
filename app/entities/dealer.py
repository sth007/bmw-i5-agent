from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Dealer(Base):
    __tablename__ = "dealer"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    bmw_dealer_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    distribution_partner_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    outlet_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    street: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    homepage: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    new_car_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    new_car_phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    used_car_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    used_car_phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    new_car_sales: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    used_car_sales: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    last_sync: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )