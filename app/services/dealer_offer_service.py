from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.dealer_offer import DealerOffer
from app.entities.dealer_offer_feature import DealerOfferFeature
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.dealer_offer_repository import DealerOfferRepository
from app.schemas.campaign import DealerOfferCreate
from app.services.feature_normalization_service import FeatureNormalizationService


class DealerOfferService:
    def __init__(self, db: Session):
        self.db = db
        self.campaign_repository = CampaignRepository(db)
        self.repository = DealerOfferRepository(db)
        self.normalizer = FeatureNormalizationService()

    def create_offer(self, campaign_id: UUID, payload: DealerOfferCreate) -> DealerOffer:
        campaign = self.campaign_repository.get(campaign_id)
        if campaign is None:
            raise LookupError("Campaign not found")

        offer = DealerOffer(
            campaign_id=campaign_id,
            dealer_name=payload.dealer_name.strip(),
            dealer_reference=payload.dealer_reference.strip() if payload.dealer_reference else None,
            source_type=payload.source_type,
            currency=payload.currency.upper(),
            vehicle_price=payload.vehicle_price,
            transfer_cost=payload.transfer_cost,
            registration_cost=payload.registration_cost,
            total_price=self._derive_total_price(
                payload.total_price,
                payload.vehicle_price,
                payload.transfer_cost,
                payload.registration_cost,
            ),
            cash_price=payload.cash_price,
            financing_required=payload.financing_required,
            financing_total_cost=payload.financing_total_cost,
            delivery_date=payload.delivery_date,
            production_date=payload.production_date,
            model_year=payload.model_year,
            holding_period_months=payload.holding_period_months,
            day_registration=payload.day_registration,
            trade_in_required=payload.trade_in_required,
            offer_valid_until=payload.offer_valid_until,
            raw_response=payload.raw_response.strip(),
        )
        offer.features = [self._build_feature(item) for item in payload.features]

        try:
            self.repository.add(offer)
            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

        return self.repository.get(offer.id) or offer

    def list_offers(self, campaign_id: UUID) -> list[DealerOffer]:
        return self.repository.list_by_campaign(campaign_id)

    def _build_feature(self, item) -> DealerOfferFeature:
        normalized_key, normalized_value = self.normalizer.normalize_feature(
            item.feature_key,
            item.feature_value,
        )
        return DealerOfferFeature(
            feature_key=item.feature_key.strip(),
            feature_value=item.feature_value.strip() if item.feature_value else None,
            normalized_key=normalized_key,
            normalized_value=normalized_value,
            display_label=item.display_label.strip() if item.display_label else None,
            is_available=item.is_available,
        )

    @staticmethod
    def _derive_total_price(
        total_price: Decimal | None,
        vehicle_price: Decimal | None,
        transfer_cost: Decimal | None,
        registration_cost: Decimal | None,
    ) -> Decimal | None:
        if total_price is not None:
            return total_price
        parts = [vehicle_price, transfer_cost, registration_cost]
        if not any(part is not None for part in parts):
            return None
        return sum((part or Decimal("0")) for part in parts)


class OfferExtractionService:
    def __init__(self, db: Session):
        self.dealer_offer_service = DealerOfferService(db)

    def extract_and_create_offer(
        self,
        campaign_id: UUID,
        dealer_name: str,
        dealer_reference: str | None,
        source_type: str,
        text: str,
    ) -> DealerOffer:
        vehicle_price = self._find_decimal(text, [r"fahrzeugpreis[:\s]+([\d\.,]+)", r"listenpreis[:\s]+([\d\.,]+)"])
        total_price = self._find_decimal(text, [r"gesamtpreis[:\s]+([\d\.,]+)", r"endpreis[:\s]+([\d\.,]+)"])
        transfer_cost = self._find_decimal(text, [r"ueberfuehrung[:\s]+([\d\.,]+)", r"transfer[:\s]+([\d\.,]+)"])
        registration_cost = self._find_decimal(text, [r"zulassung[:\s]+([\d\.,]+)"])

        features = []
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            cleaned_key = key.strip()
            cleaned_value = value.strip()
            if cleaned_key.lower() in {"gesamtpreis", "endpreis", "fahrzeugpreis", "listenpreis", "ueberfuehrung", "transfer", "zulassung"}:
                continue
            if cleaned_key and cleaned_value:
                features.append(
                    {
                        "feature_key": cleaned_key,
                        "feature_value": cleaned_value,
                        "display_label": cleaned_key,
                        "is_available": True,
                    }
                )

        payload = DealerOfferCreate(
            dealer_name=dealer_name,
            dealer_reference=dealer_reference,
            source_type=source_type,
            vehicle_price=vehicle_price,
            transfer_cost=transfer_cost,
            registration_cost=registration_cost,
            total_price=total_price,
            raw_response=text,
            features=features,
        )
        offer = self.dealer_offer_service.create_offer(campaign_id, payload)
        offer.extracted_at = datetime.now(timezone.utc)
        self.dealer_offer_service.repository.commit()
        return self.dealer_offer_service.repository.get(offer.id) or offer

    @staticmethod
    def _find_decimal(text: str, patterns: list[str]) -> Decimal | None:
        import re

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                normalized = match.group(1).replace(".", "").replace(",", ".")
                return Decimal(normalized)
        return None
