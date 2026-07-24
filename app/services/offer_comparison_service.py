from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.entities.campaign_configuration import CampaignConfiguration
from app.entities.configuration_requirement import ConfigurationRequirement
from app.entities.dealer_offer import DealerOffer
from app.entities.dealer_offer_feature import DealerOfferFeature


@dataclass(frozen=True)
class RequirementMatch:
    requirement: ConfigurationRequirement
    offer_feature: DealerOfferFeature | None
    status: str


@dataclass(frozen=True)
class OfferComparison:
    offer: DealerOffer
    category: str
    score: int
    matches: list[RequirementMatch]


class OfferComparisonService:
    def compare(
        self,
        configuration: CampaignConfiguration,
        offer: DealerOffer,
    ) -> OfferComparison:
        feature_map = {feature.normalized_key: feature for feature in offer.features}
        matches: list[RequirementMatch] = []

        for requirement in configuration.requirements:
            feature = feature_map.get(requirement.normalized_key)
            status = self._match_status(requirement, feature)
            matches.append(RequirementMatch(requirement=requirement, offer_feature=feature, status=status))

        category = self._category(matches)
        score = self._score(matches, category)
        return OfferComparison(offer=offer, category=category, score=score, matches=matches)

    @staticmethod
    def _match_status(
        requirement: ConfigurationRequirement,
        feature: DealerOfferFeature | None,
    ) -> str:
        if feature is None or feature.is_available is False:
            return "missing" if requirement.is_mandatory else "alternative"
        if requirement.normalized_value is None:
            return "exact"
        if feature.normalized_value == requirement.normalized_value:
            return "exact"
        return "incompatible" if requirement.is_mandatory else "alternative"

    @staticmethod
    def _category(matches: list[RequirementMatch]) -> str:
        if all(match.status == "exact" for match in matches):
            return "exact"
        if any(match.requirement.is_mandatory and match.status != "exact" for match in matches):
            return "incompatible"
        return "alternative"

    @staticmethod
    def _score(matches: list[RequirementMatch], category: str) -> int:
        if not matches:
            return 100
        exact = sum(1 for match in matches if match.status == "exact")
        alternative = sum(1 for match in matches if match.status == "alternative")
        ratio = Decimal(exact) / Decimal(len(matches))
        alt_ratio = Decimal(alternative) / Decimal(len(matches))
        if category == "exact":
            return 100
        if category == "alternative":
            return min(99, max(60, int((ratio * 100) + (alt_ratio * 20))))
        return min(59, max(0, int(ratio * 59)))
