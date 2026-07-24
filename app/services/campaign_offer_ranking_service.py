from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.services.offer_comparison_service import OfferComparison


@dataclass(frozen=True)
class RankedOffer:
    comparison: OfferComparison
    price_delta_to_cheapest_overall: Decimal | None
    price_delta_to_cheapest_exact: Decimal | None
    price_delta_to_cheapest_alternative: Decimal | None
    is_cheapest_exact: bool
    is_cheapest_alternative: bool
    is_cheapest_overall: bool


@dataclass(frozen=True)
class RankingResult:
    ranked_offers: list[RankedOffer]
    cheapest_exact_offer_id: UUID | None
    cheapest_alternative_offer_id: UUID | None
    cheapest_overall_offer_id: UUID | None


class CampaignOfferRankingService:
    CATEGORY_RANK = {"exact": 0, "alternative": 1, "incompatible": 2}

    def rank(self, comparisons: list[OfferComparison]) -> RankingResult:
        cheapest_exact = self._cheapest(comparisons, "exact")
        cheapest_alternative = self._cheapest(comparisons, "alternative")
        cheapest_overall = self._cheapest(comparisons, None)

        sorted_comparisons = sorted(
            comparisons,
            key=lambda item: self._sort_key(item),
        )

        ranked = [
            RankedOffer(
                comparison=item,
                price_delta_to_cheapest_overall=self._delta(item, cheapest_overall),
                price_delta_to_cheapest_exact=self._delta(item, cheapest_exact),
                price_delta_to_cheapest_alternative=self._delta(item, cheapest_alternative),
                is_cheapest_exact=bool(cheapest_exact and item.offer.id == cheapest_exact.offer.id),
                is_cheapest_alternative=bool(
                    cheapest_alternative and item.offer.id == cheapest_alternative.offer.id
                ),
                is_cheapest_overall=bool(cheapest_overall and item.offer.id == cheapest_overall.offer.id),
            )
            for item in sorted_comparisons
        ]

        return RankingResult(
            ranked_offers=ranked,
            cheapest_exact_offer_id=cheapest_exact.offer.id if cheapest_exact else None,
            cheapest_alternative_offer_id=cheapest_alternative.offer.id if cheapest_alternative else None,
            cheapest_overall_offer_id=cheapest_overall.offer.id if cheapest_overall else None,
        )

    def _sort_key(self, comparison: OfferComparison) -> tuple[int, Decimal, Decimal]:
        price = comparison.offer.total_price or Decimal("999999999.99")
        if comparison.category == "exact":
            return self.CATEGORY_RANK[comparison.category], price, Decimal(-comparison.score)
        if comparison.category == "alternative":
            return self.CATEGORY_RANK[comparison.category], Decimal(-comparison.score), price
        return self.CATEGORY_RANK[comparison.category], Decimal(-comparison.score), price

    @staticmethod
    def _delta(current: OfferComparison, reference: OfferComparison | None) -> Decimal | None:
        if reference is None or current.offer.total_price is None or reference.offer.total_price is None:
            return None
        return current.offer.total_price - reference.offer.total_price

    @staticmethod
    def _cheapest(
        comparisons: list[OfferComparison],
        category: str | None,
    ) -> OfferComparison | None:
        candidates = [
            comparison
            for comparison in comparisons
            if comparison.offer.total_price is not None and (category is None or comparison.category == category)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda item: item.offer.total_price)
