from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.entities.campaign import Campaign
from app.entities.campaign_configuration import CampaignConfiguration
from app.entities.dealer_offer import DealerOffer
from app.entities.vehicle_configuration import VehicleConfiguration


class CampaignRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, campaign: Campaign) -> Campaign:
        self.db.add(campaign)
        self.db.flush()
        return campaign

    def get(self, campaign_id: UUID) -> Campaign | None:
        statement = (
            select(Campaign)
            .options(
                joinedload(Campaign.configuration).joinedload(CampaignConfiguration.requirements),
                joinedload(Campaign.configuration)
                .joinedload(CampaignConfiguration.vehicle_configuration)
                .joinedload(VehicleConfiguration.features),
                joinedload(Campaign.offers).joinedload(DealerOffer.features),
            )
            .where(Campaign.id == campaign_id)
        )
        return self.db.execute(statement).unique().scalar_one_or_none()

    def list_all(self) -> list[Campaign]:
        statement = (
            select(Campaign)
            .options(joinedload(Campaign.configuration))
            .order_by(Campaign.created_at.desc())
        )
        return list(self.db.execute(statement).unique().scalars())

    def count(self) -> int:
        return int(self.db.execute(select(func.count()).select_from(Campaign)).scalar_one())

    def get_latest_relevant(self) -> Campaign | None:
        statement = (
            select(Campaign)
            .where(Campaign.status.in_(["STARTED", "COMPLETED"]))
            .order_by(desc(Campaign.started_at), desc(Campaign.created_at))
            .limit(1)
        )
        return self.db.execute(statement).scalar_one_or_none()

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()
