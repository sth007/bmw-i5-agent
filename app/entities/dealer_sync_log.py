from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DealerSyncLog(Base):
    __tablename__ = "dealer_sync_log"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    dealers_received: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    dealers_created: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    dealers_updated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    dealers_failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )