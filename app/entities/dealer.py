from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship

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

    campaign_contacts: Mapped[list["CampaignDealerContact"]] = relationship(
        back_populates="dealer",
        cascade="all, delete-orphan",
    )
    inbound_emails: Mapped[list["InboundEmail"]] = relationship(back_populates="dealer")
    dealer_offers: Mapped[list["DealerOffer"]] = relationship(back_populates="dealer")


from app.entities.campaign_dealer_contact import CampaignDealerContact  # noqa: E402
from app.entities.dealer_offer import DealerOffer  # noqa: E402
from app.entities.inbound_email import InboundEmail  # noqa: E402
