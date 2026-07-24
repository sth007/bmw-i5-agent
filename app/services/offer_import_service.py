from datetime import datetime

from sqlalchemy.orm import Session

from app.entities.offer import Offer
from app.repositories.offer_repository import OfferRepository
from app.schemas.offer import OfferImport, OfferImportResult


class OfferImportService:
    """
    Importiert öffentliche Fahrzeugangebote nach PostgreSQL.

    Ein Angebot wird eindeutig über die Kombination
    aus source und external_id identifiziert.
    """

    def __init__(self, db: Session):
        self.repository = OfferRepository(db)

    def import_offers(
        self,
        offers: list[OfferImport],
    ) -> OfferImportResult:
        created = 0
        updated = 0
        unchanged = 0

        try:
            for offer_data in offers:
                existing_offer = self.repository.get_by_external_id(
                    source=offer_data.source,
                    external_id=offer_data.external_id,
                )

                if existing_offer is None:
                    self.repository.add(
                        self._create_offer(offer_data)
                    )
                    created += 1
                    continue

                if self._update_offer(
                    offer=existing_offer,
                    offer_data=offer_data,
                ):
                    updated += 1
                else:
                    unchanged += 1

            self.repository.commit()

        except Exception:
            self.repository.rollback()
            raise

        return OfferImportResult(
            received=len(offers),
            created=created,
            updated=updated,
            unchanged=unchanged,
        )

    @staticmethod
    def _create_offer(
        offer_data: OfferImport,
    ) -> Offer:
        now = datetime.utcnow()

        return Offer(
            source=offer_data.source,
            external_id=offer_data.external_id,
            dealer_id=offer_data.dealer_id,
            title=offer_data.title,
            model=offer_data.model,
            variant=offer_data.variant,
            price=offer_data.price,
            currency=offer_data.currency,
            mileage_km=offer_data.mileage_km,
            first_registration=offer_data.first_registration,
            power_kw=offer_data.power_kw,
            fuel_type=offer_data.fuel_type,
            transmission=offer_data.transmission,
            drivetrain=offer_data.drivetrain,
            color=offer_data.color,
            vin=offer_data.vin,
            url=offer_data.url,
            image_url=offer_data.image_url,
            is_active=True,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _update_offer(
        offer: Offer,
        offer_data: OfferImport,
    ) -> bool:
        now = datetime.utcnow()
        changed = False

        values = {
            "dealer_id": offer_data.dealer_id,
            "title": offer_data.title,
            "model": offer_data.model,
            "variant": offer_data.variant,
            "price": offer_data.price,
            "currency": offer_data.currency,
            "mileage_km": offer_data.mileage_km,
            "first_registration": offer_data.first_registration,
            "power_kw": offer_data.power_kw,
            "fuel_type": offer_data.fuel_type,
            "transmission": offer_data.transmission,
            "drivetrain": offer_data.drivetrain,
            "color": offer_data.color,
            "vin": offer_data.vin,
            "url": offer_data.url,
            "image_url": offer_data.image_url,
            "is_active": True,
        }

        for field_name, new_value in values.items():
            old_value = getattr(offer, field_name)

            if old_value != new_value:
                setattr(offer, field_name, new_value)
                changed = True

        offer.last_seen_at = now

        if changed:
            offer.updated_at = now

        return changed