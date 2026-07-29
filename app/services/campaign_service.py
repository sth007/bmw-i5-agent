from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import parse_qs
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.campaign import Campaign
from app.entities.campaign_configuration import CampaignConfiguration
from app.entities.configuration_requirement import ConfigurationRequirement
from app.repositories.campaign_repository import CampaignRepository
from app.schemas.campaign import (
    CampaignCreate,
    CampaignCreateAndStartRequest,
    CampaignCustomerInput,
    CampaignFromPublicConfigRequest,
    CampaignStartResponse,
    CampaignStatusPatch,
)
from app.services.bmw_option_catalog import BMW_MODEL_MAP
from app.services.dealer_selection_service import DealerSelectionService
from app.services.bmw_configuration_parser import BMWConfigurationParserError, BMWConfigurationParserService
from app.services.bmw_configuration_resolver import resolve_bmw_configuration
from app.services.email_template_service import DEFAULT_CUSTOMER_NAME, EmailTemplateService
from app.services.feature_normalization_service import FeatureNormalizationService
from app.services.single_campaign_service import SingleCampaignService
from app.services.vehicle_configuration_formatter import format_configuration_items, get_resolved_configuration


class CampaignService:
    def __init__(self, db: Session):
        self.repository = CampaignRepository(db)
        self.normalizer = FeatureNormalizationService()
        self.single_campaign_service = SingleCampaignService(db)
        self.configuration_parser = BMWConfigurationParserService(db)

    def create_campaign(self, payload: CampaignCreate) -> Campaign:
        self.single_campaign_service.delete_all_campaigns_except(None)
        campaign = Campaign(
            name=payload.name.strip(),
            config_url=payload.configuration.configuration_url,
            config_id=self.extract_config_id(payload.configuration.configuration_url),
            email_body_template=payload.email_body_template.strip() if payload.email_body_template else None,
            notes=payload.notes.strip() if payload.notes else None,
        )
        configuration = CampaignConfiguration(
            configuration_url=payload.configuration.configuration_url,
            model=payload.configuration.model.strip(),
            variant=payload.configuration.variant.strip(),
            package=payload.configuration.package.strip() if payload.configuration.package else None,
            resolved_configuration=None,
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

    def create_and_start_campaign(self, payload: CampaignCreateAndStartRequest) -> CampaignStartResponse:
        cleaned_config_url = (payload.configuration.configuration_url or "").strip()
        if not cleaned_config_url:
            raise ValueError("configuration.configuration_url must not be blank")

        create_payload = CampaignCreate(
            name=payload.campaign_name,
            notes=payload.notes,
            email_body_template=payload.email_body_template,
            configuration=payload.configuration,
        )
        campaign = self.create_campaign(create_payload)

        dealer_selection_service = DealerSelectionService(self.repository.db)
        dealers = dealer_selection_service.select_for_campaign(payload.dealer_limit)

        customer_name = payload.customer.name.strip()
        customer_email = str(payload.customer.email) if payload.customer.email else None
        customer_phone = payload.customer.phone.strip() if payload.customer.phone else None
        campaign.customer_name = customer_name
        campaign.customer_email = customer_email
        campaign.customer_phone = customer_phone
        self.repository.commit()

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
                configuration_items=self._format_configuration_items(campaign.configuration),
                resolved_configuration=self._get_resolved_configuration(campaign.configuration),
                body_template=payload.email_body_template,
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
            config_id=campaign.config_id or self.extract_config_id(cleaned_config_url) or "",
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

    def create_from_public_config(
        self,
        payload: CampaignFromPublicConfigRequest,
    ) -> CampaignStartResponse:
        cleaned_name = payload.campaign_name.strip()
        if not cleaned_name:
            raise ValueError("campaign_name must not be blank")

        public_config = payload.public_configuration
        original_url = (public_config.original_configuration_url or "").strip() or (
            f"https://configure.bmw.de/de_DE/configid/{public_config.config_id.strip()}"
        )
        config_id = public_config.config_id.strip()
        if not config_id:
            raise ValueError("public_configuration.config_id must not be blank")

        option_codes = self._deduplicate_codes(public_config.option_codes)
        model_code = public_config.model_code.strip().upper()
        model_info = BMW_MODEL_MAP.get(model_code, {})
        resolved_configuration = resolve_bmw_configuration(
            model_code=model_code,
            option_codes=option_codes,
            accessories=public_config.accessories,
        )

        campaign_configuration = CampaignConfiguration(
            configuration_url=original_url,
            model=(model_info.get("model_name") or model_code).strip(),
            variant=(model_info.get("variant") or model_code).strip(),
            package=None,
            resolved_configuration=resolved_configuration.model_dump(mode="json"),
            list_price=None,
            maximum_target_price=payload.maximum_target_price,
            payment_preference=payload.payment_preference,
        )
        campaign_configuration.requirements = self._build_requirements_from_public_config(
            model_code=model_code,
            option_codes=option_codes,
            accessories=public_config.accessories,
        )

        self.single_campaign_service.delete_all_campaigns_except(None)
        campaign = Campaign(
            name=cleaned_name,
            config_url=original_url,
            config_id=config_id,
            status="DRAFT",
            email_body_template=payload.email_body_template.strip() if payload.email_body_template else None,
            notes=payload.notes.strip() if payload.notes else None,
        )
        campaign.configuration = campaign_configuration

        try:
            self.repository.add(campaign)
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

        dealers = DealerSelectionService(self.repository.db).select_for_campaign(payload.dealer_limit)

        customer_name = payload.customer.name.strip()
        customer_email = str(payload.customer.email) if payload.customer.email else None
        customer_phone = payload.customer.phone.strip() if payload.customer.phone else None
        campaign.customer_name = customer_name
        campaign.customer_email = customer_email
        campaign.customer_phone = customer_phone
        self.repository.commit()

        email_template_service = EmailTemplateService()
        email_previews = [
            email_template_service.render_campaign_request(
                dealer_id=dealer.id,
                campaign_name=campaign.name,
                config_url=original_url,
                dealer_name=dealer.name,
                dealer_email=dealer.email or "",
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                configuration_items=self._format_configuration_items(campaign.configuration),
                resolved_configuration=self._get_resolved_configuration(campaign.configuration),
                body_template=payload.email_body_template,
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
            config_url=original_url,
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

    def create_from_config(
        self,
        *,
        campaign_name: str,
        config_url: str,
        dealer_limit: int,
        customer: CampaignCustomerInput | None,
        maximum_target_price: Decimal = Decimal("0"),
        payment_preference: str = "cash",
        notes: str | None = None,
        email_body_template: str | None = None,
    ) -> CampaignStartResponse:
        cleaned_name = campaign_name.strip()
        cleaned_config_url = config_url.strip()
        if not cleaned_name:
            raise ValueError("campaign_name must not be blank")
        if not cleaned_config_url:
            raise ValueError("config_url must not be blank")

        try:
            vehicle_configuration = self.configuration_parser.parse_and_store(cleaned_config_url)
        except BMWConfigurationParserError as exc:
            raise ValueError("Invalid BMW configuration URL.") from exc
        config_id = vehicle_configuration.configuration_id or self.extract_config_id(cleaned_config_url)
        self.single_campaign_service.delete_all_campaigns_except(None)
        campaign = Campaign(
            name=cleaned_name,
            config_url=cleaned_config_url,
            config_id=config_id,
            status="DRAFT",
            email_body_template=email_body_template.strip() if email_body_template else None,
            notes=notes.strip() if notes else None,
        )
        campaign.configuration = self._build_campaign_configuration_from_vehicle(
            vehicle_configuration=vehicle_configuration,
            maximum_target_price=maximum_target_price,
            payment_preference=payment_preference,
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
            customer_email = str(customer.email) if customer.email else None
            customer_phone = customer.phone.strip() if customer.phone else None
            campaign.customer_name = customer_name
            campaign.customer_email = customer_email
            campaign.customer_phone = customer_phone
            self.repository.commit()

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
                configuration_items=format_configuration_items(campaign.configuration),
                resolved_configuration=self._get_resolved_configuration(campaign.configuration),
                body_template=email_body_template,
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
            config_id=config_id or "",
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
    def _format_configuration_items(configuration: CampaignConfiguration | None) -> list[str]:
        return format_configuration_items(configuration)

    @staticmethod
    def _get_resolved_configuration(configuration: CampaignConfiguration | None):
        return get_resolved_configuration(configuration)

    @staticmethod
    def extract_config_id(config_url: str | None) -> str | None:
        if not config_url:
            return None
        parsed = urlparse(config_url.strip())
        if parsed.scheme not in {"http", "https"}:
            return None
        if parsed.netloc.lower() != "configure.bmw.de":
            return None

        query_value = parse_qs(parsed.query).get("initialConfigId")
        if query_value and query_value[0].strip():
            return query_value[0].strip()

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

    def _build_campaign_configuration_from_vehicle(
        self,
        *,
        vehicle_configuration,
        maximum_target_price: Decimal,
        payment_preference: str,
    ) -> CampaignConfiguration:
        configuration = CampaignConfiguration(
            vehicle_configuration=vehicle_configuration,
            vehicle_configuration_id=vehicle_configuration.id,
            configuration_url=vehicle_configuration.original_url,
            model=(vehicle_configuration.model_name or vehicle_configuration.model_code or "BMW").strip(),
            variant=(vehicle_configuration.variant or vehicle_configuration.model_code or "BMW").strip(),
            package=None,
            resolved_configuration=vehicle_configuration.normalized_data.get("resolved_configuration"),
            list_price=vehicle_configuration.list_price,
            maximum_target_price=maximum_target_price,
            payment_preference=payment_preference,
        )
        configuration.requirements = [
            self._build_requirement_from_vehicle_feature(feature)
            for feature in vehicle_configuration.features
        ]
        return configuration

    def _build_requirement_from_vehicle_feature(self, feature) -> ConfigurationRequirement:
        normalized_key, normalized_value = self.normalizer.normalize_feature(
            feature.display_label or feature.feature_key,
            feature.feature_value,
        )
        return ConfigurationRequirement(
            feature_key=feature.feature_key,
            feature_value=feature.feature_value,
            normalized_key=normalized_key,
            normalized_value=normalized_value,
            display_label=feature.display_label,
            is_mandatory=feature.is_mandatory,
        )

    def _build_requirements_from_public_config(
        self,
        *,
        model_code: str,
        option_codes: list[str],
        accessories: dict[str, object],
    ) -> list[ConfigurationRequirement]:
        resolved_configuration = resolve_bmw_configuration(
            model_code=model_code,
            option_codes=option_codes,
            accessories=accessories,
        )
        requirements: list[ConfigurationRequirement] = []
        requirements.append(
            self._build_requirement(
                SimpleNamespace(
                    feature_key="vehicle.model_name",
                    feature_value=(resolved_configuration.model.name if resolved_configuration.model else model_code),
                    display_label="Modell",
                    is_mandatory=True,
                )
            )
        )

        if resolved_configuration.color is not None:
            requirements.append(
                self._build_requirement(
                    SimpleNamespace(
                        feature_key="configuration.paint",
                        feature_value=resolved_configuration.color.name,
                        display_label="Außenfarbe",
                        is_mandatory=False,
                    )
                )
            )
        if resolved_configuration.interior is not None:
            requirements.append(
                self._build_requirement(
                    SimpleNamespace(
                        feature_key="configuration.upholstery",
                        feature_value=resolved_configuration.interior.name,
                        display_label="Innenausstattung",
                        is_mandatory=False,
                    )
                )
            )

        for option in resolved_configuration.packages:
            requirements.append(
                self._build_requirement(
                    SimpleNamespace(
                        feature_key=f"configuration.option.{option.code.lower()}",
                        feature_value=option.name,
                        display_label="Paket",
                        is_mandatory=False,
                    )
                )
            )
        for option in resolved_configuration.wheels:
            requirements.append(
                self._build_requirement(
                    SimpleNamespace(
                        feature_key=f"configuration.option.{option.code.lower()}",
                        feature_value=option.name,
                        display_label="Räder",
                        is_mandatory=False,
                    )
                )
            )
        for option in resolved_configuration.driver_assistance:
            requirements.append(
                self._build_requirement(
                    SimpleNamespace(
                        feature_key=f"configuration.option.{option.code.lower()}",
                        feature_value=option.name,
                        display_label="Fahrerassistenz",
                        is_mandatory=False,
                    )
                )
            )
        for option in resolved_configuration.other_options:
            requirements.append(
                self._build_requirement(
                    SimpleNamespace(
                        feature_key=f"configuration.option.{option.code.lower()}",
                        feature_value=option.name,
                        display_label="Sonderausstattung",
                        is_mandatory=False,
                    )
                )
            )
        for accessory in resolved_configuration.accessories:
            requirements.append(
                self._build_requirement(
                    SimpleNamespace(
                        feature_key=f"configuration.accessory.{accessory.code.lower()}",
                        feature_value=accessory.name,
                        display_label="Zubehör",
                        is_mandatory=False,
                    )
                )
            )
        return requirements

    @staticmethod
    def _deduplicate_codes(codes: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for code in codes:
            normalized = code.strip().upper()
            if normalized and normalized not in seen:
                result.append(normalized)
                seen.add(normalized)
        return result
