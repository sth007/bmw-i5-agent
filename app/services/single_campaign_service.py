from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.entities.campaign import Campaign
from app.entities.inbound_email import InboundEmail


class MultipleCampaignsError(Exception):
    pass


class SingleCampaignService:
    def __init__(self, db: Session):
        self.db = db

    def get_single_campaign(self) -> Campaign | None:
        campaigns = list(self.db.execute(select(Campaign).order_by(Campaign.created_at.desc())).scalars())
        if not campaigns:
            return None
        if len(campaigns) > 1:
            raise MultipleCampaignsError("Multiple campaigns exist in single-campaign mode.")
        return campaigns[0]

    def assert_at_most_one_campaign(self) -> None:
        if self.db.execute(select(Campaign.id).limit(2)).fetchall().__len__() > 1:
            raise MultipleCampaignsError("Multiple campaigns exist in single-campaign mode.")

    def delete_all_campaigns_except(self, campaign_id: UUID | None) -> None:
        if not settings.single_campaign_mode:
            return

        statement = select(Campaign.id)
        if campaign_id is not None:
            statement = statement.where(Campaign.id != campaign_id)
        campaign_ids = list(self.db.execute(statement).scalars())
        if not campaign_ids:
            return

        self.db.execute(delete(InboundEmail).where(InboundEmail.campaign_id.in_(campaign_ids)))
        self.db.execute(delete(Campaign).where(Campaign.id.in_(campaign_ids)))
        self.db.flush()
