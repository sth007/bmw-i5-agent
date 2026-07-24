from sqlalchemy.orm import Session

from app.entities.dealer import Dealer
from app.repositories.dealer_repository import DealerRepository
from app.schemas.dealer import DealerImport
from datetime import datetime


class DealerService:
    def __init__(self, db: Session):
        self.repository = DealerRepository(db)

    def get_all_dealers(self) -> list[Dealer]:
        return self.repository.get_all()

    def get_dealer(self, dealer_id: int) -> Dealer | None:
        return self.repository.get_by_id(dealer_id)

    def create_dealer(
        self,
        name: str,
        email: str | None = None,
        phone: str | None = None,
        city: str | None = None,
    ) -> Dealer:
        name = name.strip()

        if not name:
            raise ValueError("Der Händlername darf nicht leer sein.")

        dealer = Dealer(
            name=name,
            email=email.strip() if email else None,
            phone=phone.strip() if phone else None,
            city=city.strip() if city else None,
        )

        self.repository.add(dealer)
        self.repository.commit()
        self.repository.refresh(dealer)

        return dealer

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