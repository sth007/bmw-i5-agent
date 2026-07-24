from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.entities.dealer import Dealer
from app.repositories.dealer_repository import DealerRepository


LOGGER = logging.getLogger(__name__)


class DealerSelectionService:
    def __init__(self, db: Session):
        self.repository = DealerRepository(db)

    def select_initial_dealers(self, dealer_limit: int) -> list[Dealer]:
        total_dealers = self.repository.count()
        published_dealers = self.repository.published_count()
        published_with_email = self.repository.published_with_email_count()
        selected_dealers = self.repository.list_published_with_email(dealer_limit)

        LOGGER.info("Selecting dealers...")
        LOGGER.info("Total dealers: %s", total_dealers)
        LOGGER.info("Published: %s", published_dealers)
        LOGGER.info("Published with email: %s", published_with_email)
        LOGGER.info("Selected: %s", len(selected_dealers))

        return selected_dealers

    def select_for_campaign(self, dealer_limit: int) -> list[Dealer]:
        return self.select_initial_dealers(dealer_limit)

    def debug_selection(self, dealer_limit: int) -> dict[str, object]:
        snapshot = self.repository.debug_selection_snapshot(dealer_limit)

        LOGGER.info("Selecting dealers...")
        LOGGER.info("Total dealers: %s", snapshot["total_dealers"])
        LOGGER.info("Published: %s", snapshot["published_dealers"])
        LOGGER.info("Published with email: %s", snapshot["eligible_dealers"])
        LOGGER.info("Selected: %s", snapshot["selected_dealers"])

        return snapshot
