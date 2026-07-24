from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.campaign import Campaign
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.dealer_offer_repository import DealerOfferRepository
from app.schemas.campaign import CampaignComparisonResponse, CampaignResponse, OfferComparisonResponse, RequirementMatchResponse
from app.services.campaign_offer_ranking_service import CampaignOfferRankingService
from app.services.offer_comparison_service import OfferComparisonService


class CampaignComparisonService:
    def __init__(self, db: Session):
        self.db = db
        self.campaign_repository = CampaignRepository(db)
        self.offer_repository = DealerOfferRepository(db)
        self.comparison_service = OfferComparisonService()
        self.ranking_service = CampaignOfferRankingService()

    def compare(self, campaign_id: UUID) -> CampaignComparisonResponse | None:
        campaign = self.campaign_repository.get(campaign_id)
        if campaign is None:
            return None
        if campaign.configuration is None:
            raise ValueError("Campaign configuration is missing")

        comparisons = [
            self.comparison_service.compare(campaign.configuration, offer)
            for offer in self.offer_repository.list_by_campaign(campaign_id)
        ]
        ranking = self.ranking_service.rank(comparisons)
        self._persist_summary(campaign, ranking)
        refreshed_campaign = self.campaign_repository.get(campaign_id) or campaign

        return CampaignComparisonResponse(
            campaign=CampaignResponse.model_validate(refreshed_campaign),
            ranked_offers=[
                OfferComparisonResponse(
                    offer_id=item.comparison.offer.id,
                    dealer_name=item.comparison.offer.dealer_name,
                    category=item.comparison.category,
                    score=item.comparison.score,
                    total_price=item.comparison.offer.total_price,
                    price_delta_to_cheapest_overall=item.price_delta_to_cheapest_overall,
                    price_delta_to_cheapest_exact=item.price_delta_to_cheapest_exact,
                    price_delta_to_cheapest_alternative=item.price_delta_to_cheapest_alternative,
                    is_cheapest_exact=item.is_cheapest_exact,
                    is_cheapest_alternative=item.is_cheapest_alternative,
                    is_cheapest_overall=item.is_cheapest_overall,
                    matches=[
                        RequirementMatchResponse(
                            requirement_id=match.requirement.id,
                            feature_key=match.requirement.feature_key,
                            expected_value=match.requirement.feature_value,
                            actual_value=match.offer_feature.feature_value if match.offer_feature else None,
                            status=match.status,
                            is_mandatory=match.requirement.is_mandatory,
                        )
                        for match in item.comparison.matches
                    ],
                )
                for item in ranking.ranked_offers
            ],
            cheapest_exact_offer_id=ranking.cheapest_exact_offer_id,
            cheapest_alternative_offer_id=ranking.cheapest_alternative_offer_id,
            cheapest_overall_offer_id=ranking.cheapest_overall_offer_id,
        )

    def _persist_summary(self, campaign: Campaign, ranking) -> None:
        cheapest_exact_price = self._price_for_offer_id(ranking, ranking.cheapest_exact_offer_id)
        cheapest_alternative_price = self._price_for_offer_id(ranking, ranking.cheapest_alternative_offer_id)
        cheapest_overall_price = self._price_for_offer_id(ranking, ranking.cheapest_overall_offer_id)
        campaign.cheapest_exact_price = cheapest_exact_price
        campaign.cheapest_alternative_price = cheapest_alternative_price
        campaign.cheapest_overall_price = cheapest_overall_price
        self.campaign_repository.commit()

    @staticmethod
    def _price_for_offer_id(ranking, offer_id) -> Decimal | None:
        if offer_id is None:
            return None
        for item in ranking.ranked_offers:
            if item.comparison.offer.id == offer_id:
                return item.comparison.offer.total_price
        return None
