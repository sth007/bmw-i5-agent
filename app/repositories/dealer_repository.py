from sqlalchemy import and_, func, or_
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
            .order_by(Dealer.updated_at.desc(), Dealer.created_at.desc())
            .all()
        )

    def list_published_with_email(self, limit: int) -> list[Dealer]:
        return (
            self.db.query(Dealer)
            .filter(Dealer.is_published.is_(True))
            .filter(Dealer.email.is_not(None))
            .filter(func.length(func.trim(Dealer.email)) > 0)
            .order_by(Dealer.id.asc())
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        return int(
            self.db.query(func.count(Dealer.id)).scalar() or 0
        )

    def active_count(self) -> int:
        return int(
            self.db.query(func.count(Dealer.id))
            .filter(Dealer.is_published.is_(True))
            .scalar()
            or 0
        )

    def distinct_city_count(self) -> int:
        return int(
            self.db.query(func.count(func.distinct(Dealer.city)))
            .filter(Dealer.city.is_not(None))
            .filter(func.length(func.trim(Dealer.city)) > 0)
            .scalar()
            or 0
        )

    def duplicate_bmw_id_count(self) -> int:
        duplicate_rows = (
            self.db.query(Dealer.bmw_dealer_id)
            .filter(Dealer.bmw_dealer_id.is_not(None))
            .group_by(Dealer.bmw_dealer_id)
            .having(func.count(Dealer.id) > 1)
            .all()
        )
        return len(duplicate_rows)

    def invalid_count(self) -> int:
        return int(
            self.db.query(func.count(Dealer.id))
            .filter(
                or_(
                    Dealer.name.is_(None),
                    func.length(func.trim(Dealer.name)) == 0,
                    Dealer.city.is_(None),
                    func.length(func.trim(Dealer.city)) == 0,
                    Dealer.bmw_dealer_id.is_(None),
                    func.length(func.trim(Dealer.bmw_dealer_id)) == 0,
                    and_(
                        or_(Dealer.email.is_(None), func.length(func.trim(Dealer.email)) == 0),
                        or_(Dealer.phone.is_(None), func.length(func.trim(Dealer.phone)) == 0),
                    ),
                )
            )
            .scalar()
            or 0
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
