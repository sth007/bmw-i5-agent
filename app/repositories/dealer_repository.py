from sqlalchemy.orm import Session

from app.entities.dealer import Dealer


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
            .filter(Dealer.bmw_dealer_id == bmw_dealer_id)
            .first()
        )

    def get_all(self) -> list[Dealer]:
        return (
            self.db.query(Dealer)
            .order_by(Dealer.name)
            .all()
        )

    def delete(self, dealer: Dealer) -> None:
        self.db.delete(dealer)

    def add(self, dealer: Dealer) -> Dealer:
        self.db.add(dealer)
        self.db.flush()
        return dealer

    def flush(self) -> None:
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, dealer: Dealer) -> Dealer:
        self.db.refresh(dealer)
        return dealer
