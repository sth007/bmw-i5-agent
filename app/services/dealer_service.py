from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.entities.dealer import Dealer
from app.repositories.dealer_repository import DealerRepository
from app.schemas.dealer import DealerImport, DealerUpdate


class DealerService:
    def __init__(self, db: Session):
        self.repository = DealerRepository(db)

    def get_all_dealers(self) -> list[Dealer]:
        return self.repository.get_all()

    def get_dealer(self, dealer_id: int) -> Dealer | None:
        return self.repository.get_by_id(dealer_id)

    def get_dealer_count(self) -> int:
        return self.repository.count()

    def get_dealer_statistics(self) -> dict[str, int]:
        dealer_count = self.repository.count()
        active_dealer_count = self.repository.active_count()
        duplicate_bmw_dealer_id_count = self.repository.duplicate_bmw_id_count()
        invalid_record_count = self.repository.invalid_count()
        return {
            "dealer_count": dealer_count,
            "active_dealer_count": active_dealer_count,
            "inactive_dealer_count": max(0, dealer_count - active_dealer_count),
            "distinct_city_count": self.repository.distinct_city_count(),
            "duplicate_bmw_dealer_id_count": duplicate_bmw_dealer_id_count,
            "invalid_record_count": invalid_record_count,
        }

    def create_dealer(
        self,
        name: str,
        bmw_dealer_id: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        city: str | None = None,
    ) -> Dealer:
        name = name.strip()

        if not name:
            raise ValueError("Der Händlername darf nicht leer sein.")

        dealer_identifier = (bmw_dealer_id or "").strip() or f"manual-{uuid4().hex[:12]}"

        dealer = Dealer(
            bmw_dealer_id=dealer_identifier,
            name=name,
            email=email.strip() if email else None,
            phone=phone.strip() if phone else None,
            city=city.strip() if city else None,
        )

        self.repository.add(dealer)
        self.repository.commit()
        self.repository.refresh(dealer)

        return dealer

    def update_dealer(
        self,
        dealer_id: int,
        payload: DealerUpdate,
    ) -> Dealer | None:
        dealer = self.repository.get_by_id(dealer_id)
        if dealer is None:
            return None

        updates = payload.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            if isinstance(value, str):
                value = value.strip() or None
            if field_name == "email" and value is not None:
                value = str(value)
            if field_name == "new_car_email" and value is not None:
                value = str(value)
            if field_name == "used_car_email" and value is not None:
                value = str(value)
            setattr(dealer, field_name, value)

        self.repository.commit()
        self.repository.refresh(dealer)
        return dealer

    def delete_dealer(self, dealer_id: int) -> bool:
        dealer = self.repository.get_by_id(dealer_id)
        if dealer is None:
            return False

        self.repository.delete(dealer)
        self.repository.commit()
        return True

    def import_dealers(
    self,
    dealers: list[DealerImport],
    ) -> dict[str, int]:
    
        created = 0
        updated = 0
    
        try:
        
            for item in dealers:
            
                existing = self.repository.get_by_bmw_id(
                    item.bmw_dealer_id
                )
    
                if existing is None:
                
                    dealer = Dealer(
                        bmw_dealer_id=item.bmw_dealer_id,
                        distribution_partner_id=item.distribution_partner_id,
                        outlet_id=item.outlet_id,
                        name=item.name,
                        street=item.street,
                        postal_code=item.postal_code,
                        city=item.city,
                        country=item.country,
                        latitude=item.latitude,
                        longitude=item.longitude,
                        homepage=item.homepage,
                        email=str(item.email) if item.email else None,
                        phone=item.phone,
                        new_car_email=str(item.new_car_email) if item.new_car_email else None,
                        new_car_phone=item.new_car_phone,
                        used_car_email=str(item.used_car_email) if item.used_car_email else None,
                        used_car_phone=item.used_car_phone,
                        new_car_sales=item.new_car_sales,
                        used_car_sales=item.used_car_sales,
                        is_published=item.is_published,
                        last_sync=datetime.utcnow(),
                    )
    
                    self.repository.add(dealer)
    
                    created += 1
    
                else:
                
                    existing.name = item.name
                    existing.street = item.street
                    existing.postal_code = item.postal_code
                    existing.city = item.city
                    existing.country = item.country
    
                    existing.latitude = item.latitude
                    existing.longitude = item.longitude
    
                    existing.homepage = item.homepage
    
                    existing.email = str(item.email) if item.email else None
                    existing.phone = item.phone
    
                    existing.new_car_email = (
                        str(item.new_car_email)
                        if item.new_car_email
                        else None
                    )
    
                    existing.new_car_phone = item.new_car_phone
    
                    existing.used_car_email = (
                        str(item.used_car_email)
                        if item.used_car_email
                        else None
                    )
    
                    existing.used_car_phone = item.used_car_phone
    
                    existing.new_car_sales = item.new_car_sales
                    existing.used_car_sales = item.used_car_sales
                    existing.is_published = item.is_published
    
                    existing.last_sync = datetime.utcnow()
    
                    updated += 1
    
            self.repository.commit()
    
        except Exception:
        
            self.repository.rollback()
            raise
        
        return {
            "received": len(dealers),
            "created": created,
            "updated": updated,
        }
