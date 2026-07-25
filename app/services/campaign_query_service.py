from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.campaign import LatestRelevantCampaignResponse
from app.services.single_campaign_service import MultipleCampaignsError, SingleCampaignService


class CampaignQueryService:
    def __init__(self, db: Session):
        self.single_campaign_service = SingleCampaignService(db)

    def get_latest_relevant_campaign(self) -> LatestRelevantCampaignResponse:
        try:
            campaign = self.single_campaign_service.get_single_campaign()
        except MultipleCampaignsError as exc:
            raise LookupError("Multiple campaigns exist in single-campaign mode.") from exc
        if campaign is None:
            raise LookupError("No relevant campaign found")
        if campaign.status not in {"STARTED", "COMPLETED"}:
            raise LookupError("No relevant campaign found")
        return LatestRelevantCampaignResponse(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            status=campaign.status,
            started_at=campaign.started_at,
            completed_at=campaign.completed_at,
        )
