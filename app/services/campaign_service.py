from __future__ import annotations

from decimal import Decimal
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.campaign import Campaign
from app.entities.campaign_configuration import CampaignConfiguration
from app.entities.configuration_requirement import ConfigurationRequirement
from app.repositories.campaign_repository import CampaignRepository
from app.schemas.campaign import (
    CampaignCreate,
    CampaignCustomerInput,
    CampaignStartResponse,
    CampaignStatusPatch,
)
from app.services.dealer_selection_service import DealerSelectionService
from app.services.email_template_service import DEFAULT_CUSTOMER_NAME, EmailTemplateService
from app.services.feature_normalization_service import FeatureNormalizationService


class CampaignService:
    def __init__(self, db: Session):
        self.repository = CampaignRepository(db)
        self.normalizer = FeatureNormalizationService()

    def create_campaign(self, payload: CampaignCreate) -> Campaign:
        campaign = Campaign(
            name=payload.name.strip(),
            config_url=payload.configuration.configuration_url,
            config_id=self.extract_config_id(payload.configuration.configuration_url),
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

    def start_campaign(
        self,
        *,
        campaign_name: str,
        config_url: str,
        dealer_limit: int,
    ) -> CampaignStartResponse:
        return self.create_from_config(
            campaign_name=campaign_name,
            config_url=config_url,
            dealer_limit=dealer_limit,
            customer=None,
        )

    def create_from_config(
        self,
        *,
        campaign_name: str,
        config_url: str,
        dealer_limit: int,
        customer: CampaignCustomerInput | None,
    ) -> CampaignStartResponse:
        cleaned_name = campaign_name.strip()
        cleaned_config_url = config_url.strip()
        if not cleaned_name:
            raise ValueError("campaign_name must not be blank")
        if not cleaned_config_url:
            raise ValueError("config_url must not be blank")

        config_id = self.extract_config_id(cleaned_config_url)
        if not config_id:
            raise ValueError("Invalid BMW configuration URL.")
        campaign = Campaign(
            name=cleaned_name,
            config_url=cleaned_config_url,
            config_id=config_id,
            status="DRAFT",
        )

        try:
            self.repository.add(campaign)
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

        dealer_selection_service = DealerSelectionService(self.repository.db)
        dealers = dealer_selection_service.select_for_campaign(dealer_limit)

        customer_name = DEFAULT_CUSTOMER_NAME
        customer_email = None
        customer_phone = None
        if customer is not None:
            customer_name = customer.name.strip()
            customer_email = customer.email
            customer_phone = customer.phone

        email_template_service = EmailTemplateService()
        email_previews = [
            email_template_service.render_campaign_request(
                dealer_id=dealer.id,
                campaign_name=campaign.name,
                config_url=cleaned_config_url,
                dealer_name=dealer.name,
                dealer_email=dealer.email or "",
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
            )
            for dealer in dealers
            if dealer.email and dealer.email.strip()
        ]
        warnings: list[str] = []
        if not dealers:
            warnings.append("No eligible dealers with a valid email address were found.")

        return CampaignStartResponse(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            config_url=cleaned_config_url,
            config_id=config_id,
            status=campaign.status,
            dealers=[
                {
                    "dealer_id": dealer.id,
                    "name": dealer.name,
                    "city": dealer.city,
                    "email": dealer.email or "",
                }
                for dealer in dealers
            ],
            email_previews=[
                {
                    "dealer_id": preview.dealer_id,
                    "dealer_name": preview.dealer_name,
                    "to": preview.to,
                    "subject": preview.subject,
                    "body": preview.body,
                }
                for preview in email_previews
            ],
            warnings=warnings,
        )

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

    @staticmethod
    def extract_config_id(config_url: str | None) -> str | None:
        if not config_url:
            return None
        parsed = urlparse(config_url.strip())
        if parsed.scheme not in {"http", "https"}:
            return None
        if parsed.netloc.lower() != "configure.bmw.de":
            return None

        path_parts = [part for part in parsed.path.split("/") if part]
        lowered_parts = [part.lower() for part in path_parts]
        if "configid" not in lowered_parts:
            return None

        config_index = lowered_parts.index("configid")
        if config_index + 1 >= len(path_parts):
            return None

        config_id = path_parts[config_index + 1].strip()
        if not config_id:
            return None
        return config_id
