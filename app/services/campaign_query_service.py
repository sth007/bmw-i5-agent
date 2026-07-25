from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.campaign_repository import CampaignRepository
from app.schemas.campaign import LatestRelevantCampaignResponse


class CampaignQueryService:
    def __init__(self, db: Session):
        self.repository = CampaignRepository(db)

    def get_latest_relevant_campaign(self) -> LatestRelevantCampaignResponse:
        campaign = self.repository.get_latest_relevant()
        if campaign is None:
            raise LookupError("No relevant campaign found")
        return LatestRelevantCampaignResponse(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            status=campaign.status,
            started_at=campaign.started_at,
            completed_at=campaign.completed_at,
        )
