from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.campaign_dealer_contact import CampaignDealerContact
from app.repositories.campaign_contact_repository import CampaignContactRepository
from app.repositories.campaign_repository import CampaignRepository
from app.schemas.campaign import CampaignCompletionResponse, CampaignDispatchStatusResponse
from app.services.dealer_selection_service import DealerSelectionService
from app.services.single_campaign_service import SingleCampaignService


BLOCKING_COMPLETION_STATUSES = {"PENDING", "RESERVED", "SEND_FAILED", "SEND_STATE_UNKNOWN"}


class CampaignCompletionBlockedError(Exception):
    def __init__(self, pending: int, reserved: int, failed: int):
        super().__init__("Campaign cannot be completed while sendable contacts remain.")
        self.pending = pending
        self.reserved = reserved
        self.failed = failed


class CampaignDispatchService:
    def __init__(self, db: Session):
        self.db = db
        self.campaign_repository = CampaignRepository(db)
        self.contact_repository = CampaignContactRepository(db)
        self.single_campaign_service = SingleCampaignService(db)

    def get_dispatch_status(self, campaign_id: UUID) -> CampaignDispatchStatusResponse:
        campaign = self.campaign_repository.get(campaign_id)
        if campaign is None:
            raise LookupError("Campaign not found")

        self._ensure_contacts_for_campaign(campaign_id)
        counts = self.contact_repository.status_counts(campaign_id)
        total_contacts = self.contact_repository.total_count(campaign_id)
        pending = counts.get("PENDING", 0)
        reserved = counts.get("RESERVED", 0)
        send_failed = counts.get("SEND_FAILED", 0)
        send_state_unknown = counts.get("SEND_STATE_UNKNOWN", 0)

        return CampaignDispatchStatusResponse(
            campaign_id=campaign.id,
            campaign_status=campaign.status,
            total_contacts=total_contacts,
            pending=pending,
            reserved=reserved,
            sent=counts.get("SENT", 0),
            replied=counts.get("REPLIED", 0),
            offer_extracted=counts.get("OFFER_EXTRACTED", 0),
            needs_review=counts.get("NEEDS_REVIEW", 0),
            skipped=counts.get("SKIPPED", 0),
            send_failed=send_failed,
            send_state_unknown=send_state_unknown,
            has_more_sendable_contacts=pending > 0,
            can_complete=(pending + reserved + send_failed + send_state_unknown) == 0,
        )

    def can_complete(self, campaign_id: UUID) -> bool:
        status = self.get_dispatch_status(campaign_id)
        return status.can_complete

    def complete_campaign(
        self,
        campaign_id: UUID,
        completed_by: str | None = None,
        execution_id: str | None = None,
    ) -> CampaignCompletionResponse:
        campaign = self.campaign_repository.get(campaign_id)
        if campaign is None:
            raise LookupError("Campaign not found")

        self._ensure_contacts_for_campaign(campaign_id)
        counts = self.contact_repository.status_counts(campaign_id)
        pending = counts.get("PENDING", 0)
        reserved = counts.get("RESERVED", 0)
        failed = counts.get("SEND_FAILED", 0) + counts.get("SEND_STATE_UNKNOWN", 0)

        if campaign.status == "COMPLETED" and campaign.completed_at is not None:
            return CampaignCompletionResponse(
                campaign_id=campaign.id,
                status=campaign.status,
                completed_at=campaign.completed_at,
                remaining_sendable_contacts=pending,
            )

        if pending or reserved or failed:
            raise CampaignCompletionBlockedError(pending=pending, reserved=reserved, failed=failed)

        self.single_campaign_service.delete_all_campaigns_except(campaign_id)
        campaign.status = "COMPLETED"
        campaign.completed_at = campaign.completed_at or datetime.now(UTC)
        if completed_by and campaign.completed_by is None:
            campaign.completed_by = completed_by.strip()
        if execution_id and campaign.completion_execution_id is None:
            campaign.completion_execution_id = execution_id.strip()

        try:
            self.campaign_repository.commit()
        except Exception:
            self.campaign_repository.rollback()
            raise

        return CampaignCompletionResponse(
            campaign_id=campaign.id,
            status=campaign.status,
            completed_at=campaign.completed_at,
            remaining_sendable_contacts=pending,
        )

    def _ensure_contacts_for_campaign(self, campaign_id: UUID) -> None:
        eligible_dealers = DealerSelectionService(self.db).select_for_campaign(1000)
        existing_contacts = self.contact_repository.list_by_campaign_dealer_ids(
            campaign_id,
            [dealer.id for dealer in eligible_dealers],
        )
        existing_dealer_ids = {contact.dealer_id for contact in existing_contacts}
        new_contacts = []
        for dealer in eligible_dealers:
            if dealer.id in existing_dealer_ids:
                continue
            new_contacts.append(
                CampaignDealerContact(
                    campaign_id=campaign_id,
                    dealer_id=dealer.id,
                    status="PENDING",
                    recipient_email=dealer.email,
                    outbound_message_key=f"campaign:{campaign_id}:dealer:{dealer.id}:initial-request",
                )
            )
        if not new_contacts:
            return
        self.contact_repository.add_all(new_contacts)
        self.contact_repository.commit()
