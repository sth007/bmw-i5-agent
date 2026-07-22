from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Campaign(BaseModel):
    campaign_id: str = Field(min_length=1)
    name: str = Field(min_length=1)

    configuration_id: str = Field(min_length=1)
    dealer_ids: list[str] = Field(default_factory=list)

    batch_size: int = Field(default=30, ge=1, le=100)
    status: CampaignStatus = CampaignStatus.DRAFT

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: datetime | None = None
    completed_at: datetime | None = None

    contacted_dealer_ids: list[str] = Field(default_factory=list)
    replied_dealer_ids: list[str] = Field(default_factory=list)

    notes: str | None = None

    @field_validator(
        "campaign_id",
        "name",
        "configuration_id",
        "notes",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()
        return cleaned or None

    @field_validator(
        "dealer_ids",
        "contacted_dealer_ids",
        "replied_dealer_ids",
    )
    @classmethod
    def normalize_ids(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned = value.strip()

            if not cleaned:
                continue

            if cleaned not in seen:
                normalized.append(cleaned)
                seen.add(cleaned)

        return normalized

    def can_start(self) -> bool:
        return (
            self.status in {
                CampaignStatus.DRAFT,
                CampaignStatus.READY,
                CampaignStatus.PAUSED,
            }
            and bool(self.dealer_ids)
            and bool(self.configuration_id)
        )

    def start(self) -> None:
        if not self.can_start():
            raise ValueError("Kampagne kann nicht gestartet werden")

        if self.started_at is None:
            self.started_at = datetime.now(timezone.utc)

        self.status = CampaignStatus.RUNNING

    def pause(self) -> None:
        if self.status != CampaignStatus.RUNNING:
            raise ValueError(
                "Nur eine laufende Kampagne kann pausiert werden"
            )

        self.status = CampaignStatus.PAUSED

    def complete(self) -> None:
        if self.status not in {
            CampaignStatus.RUNNING,
            CampaignStatus.PAUSED,
        }:
            raise ValueError(
                "Nur eine laufende oder pausierte Kampagne "
                "kann abgeschlossen werden"
            )

        self.status = CampaignStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def mark_contacted(self, dealer_id: str) -> None:
        cleaned = dealer_id.strip()

        if not cleaned:
            raise ValueError("Händler-ID darf nicht leer sein")

        if cleaned not in self.dealer_ids:
            raise ValueError(
                "Händler gehört nicht zu dieser Kampagne"
            )

        if cleaned not in self.contacted_dealer_ids:
            self.contacted_dealer_ids.append(cleaned)

    def mark_replied(self, dealer_id: str) -> None:
        cleaned = dealer_id.strip()

        if cleaned not in self.contacted_dealer_ids:
            raise ValueError(
                "Händler muss zuerst als kontaktiert markiert werden"
            )

        if cleaned not in self.replied_dealer_ids:
            self.replied_dealer_ids.append(cleaned)

    def next_dealer_batch(self) -> list[str]:
        remaining_dealers = [
            dealer_id
            for dealer_id in self.dealer_ids
            if dealer_id not in self.contacted_dealer_ids
        ]

        return remaining_dealers[: self.batch_size]

    @property
    def contacted_count(self) -> int:
        return len(self.contacted_dealer_ids)

    @property
    def replied_count(self) -> int:
        return len(self.replied_dealer_ids)

    @property
    def remaining_count(self) -> int:
        return len(
            [
                dealer_id
                for dealer_id in self.dealer_ids
                if dealer_id not in self.contacted_dealer_ids
            ]
        )