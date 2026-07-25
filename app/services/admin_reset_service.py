from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.entities.campaign import Campaign
from app.entities.campaign_configuration import CampaignConfiguration
from app.entities.campaign_dealer_contact import CampaignDealerContact
from app.entities.configuration_requirement import ConfigurationRequirement
from app.entities.dealer import Dealer
from app.entities.dealer_offer import DealerOffer
from app.entities.dealer_offer_feature import DealerOfferFeature
from app.entities.inbound_email import InboundEmail
from app.schemas.campaign import AdminResetResponse, AdminResetStatusResponse


class AdminResetService:
    def __init__(self, db: Session):
        self.db = db

    def reset_campaign_data(self) -> AdminResetResponse:
        deleted = self._delete_campaign_scoped(include_dealers=False)
        return AdminResetResponse(
            status="RESET_COMPLETED",
            scope="campaign_data",
            deleted=deleted,
            completed_at=datetime.now(UTC),
        )

    def reset_all_application_data(self) -> AdminResetResponse:
        deleted = self._delete_campaign_scoped(include_dealers=True)
        return AdminResetResponse(
            status="RESET_COMPLETED",
            scope="all_application_data",
            deleted=deleted,
            completed_at=datetime.now(UTC),
        )

    def get_status(self, environment: str, reset_enabled: bool) -> AdminResetStatusResponse:
        return AdminResetStatusResponse(
            environment=environment,
            reset_enabled=reset_enabled,
            campaign_count=self._count(Campaign),
            dealer_count=self._count(Dealer),
            inbound_email_count=self._count(InboundEmail),
            dealer_offer_count=self._count(DealerOffer),
        )

    def _delete_campaign_scoped(self, include_dealers: bool) -> dict[str, int]:
        deleted = {
            "campaigns": self._count(Campaign),
            "campaign_contacts": self._count(CampaignDealerContact),
            "inbound_emails": self._count(InboundEmail),
            "dealer_offers": self._count(DealerOffer),
            "review_items": self._count(InboundEmail, InboundEmail.processing_status == "NEEDS_REVIEW"),
        }
        if include_dealers:
            deleted["dealers"] = self._count(Dealer)

        self.db.execute(delete(DealerOfferFeature))
        self.db.execute(delete(DealerOffer))
        self.db.execute(delete(InboundEmail))
        self.db.execute(delete(ConfigurationRequirement))
        self.db.execute(delete(CampaignConfiguration))
        self.db.execute(delete(CampaignDealerContact))
        self.db.execute(delete(Campaign))
        if include_dealers:
            self.db.execute(delete(Dealer))
        self.db.commit()
        return deleted

    def _count(self, model, *conditions) -> int:
        statement = select(func.count()).select_from(model)
        for condition in conditions:
            statement = statement.where(condition)
        return int(self.db.execute(statement).scalar_one())
