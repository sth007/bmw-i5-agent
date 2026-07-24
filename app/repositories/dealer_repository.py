from sqlalchemy.orm import Session

from app.entities.dealer import Dealer
from app.schemas.dealer import DealerImport


class DealerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, dealer_id: int) -> Dealer | None:
        return (
            self.db.query(Dealer)
            .filter(Dealer.id == dealer_id)
            .first()
        )

    def get_by_bmw_id(
        self,
        bmw_dealer_id: str,
        ) -> Dealer | None:

        return (
            self.db.query(Dealer)
            .filter(
                Dealer.bmw_dealer_id == bmw_dealer_id
            )
            .first()
        )

    def get_all(self) -> list[Dealer]:
        return (
            self.db.query(Dealer)
            .order_by(Dealer.name)
            .all()
        )

    def create(self, dealer: Dealer) -> Dealer:
        self.db.add(dealer)
        self.db.commit()
        self.db.refresh(dealer)
        return dealer