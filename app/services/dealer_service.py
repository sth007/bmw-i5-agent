from sqlalchemy.orm import Session

from app.entities.dealer import Dealer
from app.repositories.dealer_repository import DealerRepository
from app.schemas.dealer import DealerImport


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

        return self.repository.create(dealer)

    def import_dealers(
    self,
    dealers: list[DealerImport],
    ) -> dict[str, int]:
        return {
        "received": len(dealers),
        }