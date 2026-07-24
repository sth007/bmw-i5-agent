from sqlalchemy import and_, func, inspect, or_, text
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
            self._published_with_email_query()
            .order_by(Dealer.id.asc())
            .limit(limit)
            .all()
        )

    def published_with_email_count(self) -> int:
        return int(
            self._published_with_email_query()
            .count()
            or 0
        )

    def published_count(self) -> int:
        return int(
            self.db.query(func.count(Dealer.id))
            .filter(Dealer.is_published.is_(True))
            .scalar()
            or 0
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

    def debug_selection_snapshot(self, limit: int) -> dict[str, object]:
        table_exists = inspect(self.db.bind).has_table(Dealer.__tablename__) if self.db.bind else False
        database_name = self.db.execute(text("SELECT current_database()")).scalar_one_or_none()

        if not table_exists:
            return {
                "table_exists": False,
                "database_name": database_name,
                "total_dealers": 0,
                "published_dealers": 0,
                "dealers_with_email": 0,
                "eligible_dealers": 0,
                "selected_dealers": 0,
                "dealers_with_any_contact_email": 0,
                "suspicious_test_dealers": 0,
                "selection_sql": "Dealer table does not exist.",
                "sample": [],
                "warnings": [
                    "Dealer table 'dealer' does not exist in the current database. Run Alembic migrations and verify the API points to the expected PostgreSQL database."
                ],
            }

        selected_query = self._published_with_email_query().order_by(Dealer.id.asc()).limit(limit)
        selected_dealers = selected_query.all()

        published_with_any_email = int(
            self.db.query(func.count(Dealer.id))
            .filter(Dealer.is_published.is_(True))
            .filter(
                or_(
                    and_(Dealer.email.is_not(None), func.length(func.trim(Dealer.email)) > 0),
                    and_(Dealer.new_car_email.is_not(None), func.length(func.trim(Dealer.new_car_email)) > 0),
                    and_(Dealer.used_car_email.is_not(None), func.length(func.trim(Dealer.used_car_email)) > 0),
                )
            )
            .scalar()
            or 0
        )

        primary_email_count = int(
            self.db.query(func.count(Dealer.id))
            .filter(Dealer.email.is_not(None))
            .filter(func.length(func.trim(Dealer.email)) > 0)
            .scalar()
            or 0
        )
        suspicious_test_dealers = int(
            self.db.query(func.count(Dealer.id))
            .filter(
                or_(
                    Dealer.email.ilike("%@example.com"),
                    Dealer.name.op("~")(r"^Dealer [0-9]+$"),
                    and_(
                        Dealer.bmw_dealer_id.is_(None),
                        Dealer.email.is_not(None),
                        Dealer.email.ilike("%@example.com"),
                    ),
                )
            )
            .scalar()
            or 0
        )
        warnings: list[str] = []
        if suspicious_test_dealers:
            warnings.append(
                "Suspicious test dealers were found in the current database. Campaign selection may return dummy data until they are removed."
            )

        return {
            "table_exists": True,
            "database_name": database_name,
            "total_dealers": self.count(),
            "published_dealers": self.published_count(),
            "dealers_with_email": primary_email_count,
            "eligible_dealers": self.published_with_email_count(),
            "selected_dealers": len(selected_dealers),
            "dealers_with_any_contact_email": published_with_any_email,
            "suspicious_test_dealers": suspicious_test_dealers,
            "selection_sql": str(
                selected_query.statement.compile(compile_kwargs={"literal_binds": True})
            ),
            "sample": [
                {
                    "id": dealer.id,
                    "name": dealer.name,
                    "email": dealer.email,
                    "new_car_email": dealer.new_car_email,
                    "used_car_email": dealer.used_car_email,
                    "is_published": dealer.is_published,
                }
                for dealer in selected_dealers[: min(5, limit)]
            ],
            "warnings": warnings,
        }

    def _published_with_email_query(self):
        return (
            self.db.query(Dealer)
            .filter(Dealer.is_published.is_(True))
            .filter(Dealer.email.is_not(None))
            .filter(func.length(func.trim(Dealer.email)) > 0)
        )
