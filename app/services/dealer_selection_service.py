from __future__ import annotations

from sqlalchemy.orm import Session

from app.entities.dealer import Dealer
from app.repositories.dealer_repository import DealerRepository


class DealerSelectionService:
    def __init__(self, db: Session):
        self.repository = DealerRepository(db)

    def select_initial_dealers(self, dealer_limit: int) -> list[Dealer]:
        return self.repository.list_published_with_email(dealer_limit)

    def select_for_campaign(self, dealer_limit: int) -> list[Dealer]:
        return self.select_initial_dealers(dealer_limit)
