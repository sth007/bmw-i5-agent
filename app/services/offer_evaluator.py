from app.domain.dealer_offer import DealerOffer


class OfferEvaluator:
    def best_offer(
        self,
        offers: list[DealerOffer],
    ) -> DealerOffer:

        if not offers:
            raise ValueError("Keine Angebote vorhanden")

        return min(
            offers,
            key=lambda offer: offer.offer_price,
        )