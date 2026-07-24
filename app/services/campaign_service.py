from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.campaign import Campaign
from app.entities.campaign_configuration import CampaignConfiguration
from app.entities.configuration_requirement import ConfigurationRequirement
from app.repositories.campaign_repository import CampaignRepository
from app.schemas.campaign import CampaignCreate, CampaignStatusPatch
from app.services.feature_normalization_service import FeatureNormalizationService


class CampaignService:
    def __init__(self, db: Session):
        self.repository = CampaignRepository(db)
        self.normalizer = FeatureNormalizationService()

    def create_campaign(self, payload: CampaignCreate) -> Campaign:
        campaign = Campaign(
            name=payload.name.strip(),
            notes=payload.notes.strip() if payload.notes else None,
        )
        configuration = CampaignConfiguration(
            configuration_url=payload.configuration.configuration_url,
            model=payload.configuration.model.strip(),
            variant=payload.configuration.variant.strip(),
            package=payload.configuration.package.strip() if payload.configuration.package else None,
            list_price=payload.configuration.list_price,
            maximum_target_price=payload.configuration.maximum_target_price,
            payment_preference=payload.configuration.payment_preference,
        )
        configuration.requirements = [
            self._build_requirement(item)
            for item in payload.configuration.requirements
        ]
        campaign.configuration = configuration

        try:
            self.repository.add(campaign)
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

        return self.repository.get(campaign.id) or campaign

    def list_campaigns(self) -> list[Campaign]:
        return self.repository.list_all()

    def get_campaign(self, campaign_id: UUID) -> Campaign | None:
        return self.repository.get(campaign_id)

    def update_status(self, campaign_id: UUID, payload: CampaignStatusPatch) -> Campaign | None:
        campaign = self.repository.get(campaign_id)
        if campaign is None:
            return None

        campaign.status = payload.status
        try:
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise
        return self.repository.get(campaign_id)

    def update_pricing_summary(
        self,
        campaign: Campaign,
        cheapest_exact_price: Decimal | None,
        cheapest_alternative_price: Decimal | None,
        cheapest_overall_price: Decimal | None,
    ) -> Campaign:
        campaign.cheapest_exact_price = cheapest_exact_price
        campaign.cheapest_alternative_price = cheapest_alternative_price
        campaign.cheapest_overall_price = cheapest_overall_price
        self.repository.commit()
        return campaign

    def _build_requirement(self, item) -> ConfigurationRequirement:
        normalized_key, normalized_value = self.normalizer.normalize_feature(
            item.feature_key,
            item.feature_value,
        )
        return ConfigurationRequirement(
            feature_key=item.feature_key.strip(),
            feature_value=item.feature_value.strip() if item.feature_value else None,
            normalized_key=normalized_key,
            normalized_value=normalized_value,
            display_label=item.display_label.strip() if item.display_label else None,
            is_mandatory=item.is_mandatory,
        )
