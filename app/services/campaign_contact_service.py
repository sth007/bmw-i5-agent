from __future__ import annotations

import re
from email.utils import parseaddr
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.entities.campaign_dealer_contact import CampaignDealerContact
from app.entities.dealer_offer import DealerOffer
from app.entities.inbound_email import InboundEmail
from app.repositories.campaign_contact_repository import CampaignContactRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.dealer_offer_repository import DealerOfferRepository
from app.repositories.dealer_repository import DealerRepository
from app.repositories.inbound_email_repository import InboundEmailRepository
from app.schemas.campaign import (
    CampaignContactClaimRequest,
    CampaignContactClaimResponse,
    CampaignContactSentRequest,
    CampaignContactStateResponse,
    InboundEmailCreateRequest,
    InboundEmailDebugMatchResponse,
    InboundEmailResponse,
    InboundOfferExtractionRequest,
    InboundOfferExtractionResponse,
    ReviewQueueItemResponse,
)
from app.services.dealer_selection_service import DealerSelectionService
from app.services.email_template_service import DEFAULT_CUSTOMER_NAME, EmailTemplateService
from app.services.single_campaign_service import MultipleCampaignsError, SingleCampaignService


CONTACTABLE_STATUSES = {
    "RESERVED",
    "SENT",
    "REPLIED",
    "OFFER_EXTRACTED",
    "NEEDS_REVIEW",
    "SEND_FAILED",
    "SEND_STATE_UNKNOWN",
    "SKIPPED",
}
CAMPAIGN_TOKEN_PATTERN = re.compile(r"\[BMW-CAMP:([0-9a-fA-F-]+)\]")


class CampaignContactService:
    def __init__(self, db: Session):
        self.db = db
        self.campaign_repository = CampaignRepository(db)
        self.contact_repository = CampaignContactRepository(db)
        self.dealer_repository = DealerRepository(db)
        self.offer_repository = DealerOfferRepository(db)
        self.inbound_repository = InboundEmailRepository(db)
        self.email_template_service = EmailTemplateService()
        self.single_campaign_service = SingleCampaignService(db)

    def claim_contacts(
        self,
        campaign_id: UUID,
        payload: CampaignContactClaimRequest,
    ) -> CampaignContactClaimResponse:
        campaign = self.campaign_repository.get(campaign_id)
        if campaign is None:
            raise LookupError("Campaign not found")

        self._ensure_contacts_for_campaign(campaign_id)
        if campaign.status == "DRAFT":
            self.single_campaign_service.delete_all_campaigns_except(campaign_id)
            campaign.status = "STARTED"
            campaign.started_at = campaign.started_at or datetime.now(UTC)
            self.campaign_repository.commit()

        now = datetime.now(UTC)
        claimed_contacts = self.contact_repository.list_pending_for_update(campaign_id, payload.limit)
        contacts_payload: list[dict] = []
        for contact in claimed_contacts:
            dealer = contact.dealer
            if dealer is None:
                contact.status = "SKIPPED"
                contact.last_error = "Dealer record missing."
                continue

            rendered = self.email_template_service.render_campaign_request(
                dealer_id=dealer.id,
                campaign_name=campaign.name,
                config_url=campaign.config_url or "",
                dealer_name=dealer.name,
                dealer_email=dealer.email or "",
                customer_name=DEFAULT_CUSTOMER_NAME,
            )
            subject = self._build_subject(campaign_id, rendered.subject)
            effective_to = payload.test_recipient.strip() if payload.test_mode and payload.test_recipient else (dealer.email or "").strip()

            contact.status = "RESERVED"
            contact.reservation_owner = payload.reservation_owner
            contact.reserved_at = now
            contact.recipient_email = dealer.email
            contact.original_subject = subject
            contact.rendered_body = rendered.body

            contacts_payload.append(
                {
                    "contact_id": contact.id,
                    "campaign_id": campaign_id,
                    "dealer_id": dealer.id,
                    "dealer_name": dealer.name,
                    "outbound_message_key": contact.outbound_message_key,
                    "subject": subject,
                    "body": rendered.body,
                    "effective_to": effective_to,
                    "recipient_email": dealer.email,
                    "test_mode": payload.test_mode,
                    "test_email": payload.test_recipient,
                }
            )

        try:
            self.contact_repository.commit()
        except Exception:
            self.contact_repository.rollback()
            raise

        return CampaignContactClaimResponse(campaign_id=campaign_id, contacts=contacts_payload)

    def mark_sent(self, contact_id: UUID, payload: CampaignContactSentRequest) -> CampaignContactStateResponse:
        contact = self.contact_repository.get(contact_id)
        if contact is None:
            raise LookupError("Campaign contact not found")

        if contact.provider_message_id == payload.provider_message_id:
            return CampaignContactStateResponse.model_validate(contact)

        contact.status = "SENT"
        contact.sent_at = contact.sent_at or datetime.now(UTC)
        contact.provider = payload.provider
        contact.provider_message_id = payload.provider_message_id
        contact.provider_thread_id = payload.provider_thread_id
        contact.internet_message_id = self._normalize_message_id(payload.internet_message_id)
        contact.recipient_email = payload.sent_to
        contact.last_error = None

        try:
            self.contact_repository.commit()
        except Exception:
            self.contact_repository.rollback()
            raise
        return CampaignContactStateResponse.model_validate(contact)

    def mark_send_failed(self, contact_id: UUID, error_message: str, unknown_state: bool) -> CampaignContactStateResponse:
        contact = self.contact_repository.get(contact_id)
        if contact is None:
            raise LookupError("Campaign contact not found")

        contact.status = "SEND_STATE_UNKNOWN" if unknown_state else "SEND_FAILED"
        contact.last_error = error_message.strip()

        try:
            self.contact_repository.commit()
        except Exception:
            self.contact_repository.rollback()
            raise
        return CampaignContactStateResponse.model_validate(contact)

    def register_inbound_email(self, payload: InboundEmailCreateRequest) -> InboundEmailResponse:
        existing = self.inbound_repository.get_by_provider_message(payload.provider, payload.provider_message_id)
        if existing is not None:
            return self._build_inbound_response(existing)

        normalized_payload = self._normalize_inbound_payload(payload)
        hinted_campaign = self._resolve_campaign_hint(normalized_payload.campaign_id_hint)
        auto_campaign = hinted_campaign
        if auto_campaign is None:
            auto_campaign = self._resolve_single_campaign_fallback()
        contact, matching_status, _ = self._match_inbound_email(
            normalized_payload,
            auto_campaign.id if auto_campaign is not None else None,
        )
        campaign_id = contact.campaign_id if contact else (auto_campaign.id if auto_campaign is not None else self._extract_campaign_id_from_subject(normalized_payload.subject))
        dealer_id = contact.dealer_id if contact else None
        contact_id = contact.id if contact else None
        processing_status = "REGISTERED" if contact is not None else "RECEIVED"
        if auto_campaign is not None and contact is None:
            if matching_status == "UNMATCHED":
                matching_status = "NEEDS_DEALER_ASSIGNMENT"
            processing_status = "NEEDS_REVIEW"
        elif auto_campaign is None and matching_status == "UNMATCHED":
            matching_status = "NO_CAMPAIGN"
            processing_status = "NEEDS_REVIEW"
        inbound_email = InboundEmail(
            campaign_id=campaign_id,
            dealer_id=dealer_id,
            campaign_dealer_contact_id=contact_id,
            mailbox_address=normalized_payload.mailbox_address,
            provider=normalized_payload.provider,
            provider_message_id=normalized_payload.provider_message_id,
            provider_thread_id=normalized_payload.provider_thread_id,
            internet_message_id=normalized_payload.internet_message_id,
            in_reply_to=normalized_payload.in_reply_to,
            references=normalized_payload.references,
            sender_email=normalized_payload.sender_email,
            sender_name=normalized_payload.sender_name,
            subject=normalized_payload.subject,
            text_body=normalized_payload.text_body,
            html_body=normalized_payload.html_body,
            received_at=normalized_payload.received_at,
            processing_status=processing_status,
            matching_status=matching_status,
            raw_metadata=normalized_payload.raw_metadata,
        )

        try:
            self.inbound_repository.add(inbound_email)
            if contact is not None:
                contact.status = "REPLIED"
                contact.replied_at = contact.replied_at or normalized_payload.received_at
            self.inbound_repository.commit()
        except Exception:
            self.inbound_repository.rollback()
            raise

        return self._build_inbound_response(inbound_email)

    def debug_match(self, inbound_email_id: UUID) -> InboundEmailDebugMatchResponse:
        inbound_email = self.inbound_repository.get(inbound_email_id)
        if inbound_email is None:
            raise LookupError("Inbound email not found")

        payload = InboundEmailCreateRequest(
            mailbox_address=inbound_email.mailbox_address,
            provider=inbound_email.provider,
            provider_message_id=inbound_email.provider_message_id,
            provider_thread_id=inbound_email.provider_thread_id,
            internet_message_id=inbound_email.internet_message_id,
            in_reply_to=inbound_email.in_reply_to,
            references=inbound_email.references,
            sender_email=inbound_email.sender_email,
            sender_name=inbound_email.sender_name,
            subject=inbound_email.subject,
            text_body=inbound_email.text_body,
            html_body=inbound_email.html_body,
            received_at=inbound_email.received_at,
            raw_metadata=inbound_email.raw_metadata,
        )
        _, _, debug = self._match_inbound_email(payload)
        return InboundEmailDebugMatchResponse(
            inbound_email_id=inbound_email.id,
            matching_status=inbound_email.matching_status,
            campaign_id=inbound_email.campaign_id,
            dealer_id=inbound_email.dealer_id,
            campaign_dealer_contact_id=inbound_email.campaign_dealer_contact_id,
            provider_thread_id=inbound_email.provider_thread_id,
            in_reply_to=inbound_email.in_reply_to,
            references=inbound_email.references,
            subject=inbound_email.subject,
            sender_email=inbound_email.sender_email,
            checked=debug["checked"],
            candidate_contacts=debug["candidate_contacts"],
        )

    def extract_offer(
        self,
        inbound_email_id: UUID,
        payload: InboundOfferExtractionRequest | None = None,
    ) -> InboundOfferExtractionResponse:
        inbound_email = self.inbound_repository.get(inbound_email_id)
        if inbound_email is None:
            raise LookupError("Inbound email not found")

        text = self._compose_extraction_text(inbound_email, payload)
        analysis = self._analyse_offer_text(text)

        if inbound_email.campaign_id is None or inbound_email.dealer_id is None:
            inbound_email.processing_status = "NEEDS_REVIEW"
            inbound_email.matching_status = "UNMATCHED" if inbound_email.matching_status == "UNMATCHED" else inbound_email.matching_status
            self.inbound_repository.commit()
            return InboundOfferExtractionResponse(
                inbound_email_id=inbound_email.id,
                status="FAILED",
                gross_final_price=None,
                currency=None,
                price_confidence=None,
                needs_review=True,
                review_reason="Inbound email could not be matched to a campaign contact.",
                dealer_offer_id=None,
            )

        offer = DealerOffer(
            campaign_id=inbound_email.campaign_id,
            dealer_id=inbound_email.dealer_id,
            inbound_email_id=inbound_email.id,
            dealer_name=inbound_email.contact.dealer.name if inbound_email.contact and inbound_email.contact.dealer else (inbound_email.sender_name or inbound_email.sender_email or "Unknown Dealer"),
            source_type="email",
            currency=analysis["currency"] or "EUR",
            raw_response=text.strip() or "(empty email)",
            total_price=analysis["gross_final_price"],
            gross_final_price=analysis["gross_final_price"],
            list_price=analysis["list_price"],
            discount_amount=analysis["discount_amount"],
            discount_percent=analysis["discount_percent"],
            delivery_cost=analysis["delivery_cost"],
            registration_cost=analysis["registration_cost"],
            other_costs=analysis["other_costs"],
            delivery_time_text=analysis["delivery_time_text"],
            valid_until=analysis["valid_until"],
            price_confidence=analysis["price_confidence"],
            extraction_status=analysis["status"],
            missing_fields=analysis["missing_fields"],
            extraction_notes=analysis["review_reason"],
            raw_extraction=self._serialize_json_value(analysis),
            extracted_at=datetime.now(UTC),
        )

        try:
            self.offer_repository.add(offer)
            inbound_email.processing_status = "NEEDS_REVIEW" if analysis["needs_review"] else "PROCESSED"
            if inbound_email.contact is not None:
                inbound_email.contact.status = "NEEDS_REVIEW" if analysis["needs_review"] else "OFFER_EXTRACTED"
            self.offer_repository.commit()
        except Exception:
            self.offer_repository.rollback()
            raise

        return InboundOfferExtractionResponse(
            inbound_email_id=inbound_email.id,
            status=analysis["status"],
            gross_final_price=analysis["gross_final_price"],
            currency=analysis["currency"],
            price_confidence=analysis["price_confidence"],
            needs_review=analysis["needs_review"],
            review_reason=analysis["review_reason"],
            dealer_offer_id=offer.id,
        )

    def review_queue(self, campaign_id: UUID | None) -> list[ReviewQueueItemResponse]:
        items: list[ReviewQueueItemResponse] = []
        for contact in self.contact_repository.list_review_queue(campaign_id):
            items.append(
                ReviewQueueItemResponse(
                    item_type="contact",
                    campaign_id=contact.campaign_id,
                    dealer_id=contact.dealer_id,
                    contact_id=contact.id,
                    inbound_email_id=None,
                    dealer_offer_id=None,
                    status=contact.status,
                    reason=contact.last_error or "Manual review required.",
                    subject=contact.original_subject,
                    sender_email=contact.dealer.email if contact.dealer else None,
                    created_at=contact.updated_at,
                )
            )

        for inbound_email in self.inbound_repository.list_review_queue(campaign_id):
            items.append(
                ReviewQueueItemResponse(
                    item_type="inbound_email",
                    campaign_id=inbound_email.campaign_id,
                    dealer_id=inbound_email.dealer_id,
                    contact_id=inbound_email.campaign_dealer_contact_id,
                    inbound_email_id=inbound_email.id,
                    dealer_offer_id=inbound_email.offers[0].id if inbound_email.offers else None,
                    status=inbound_email.processing_status,
                    reason=f"Matching status: {inbound_email.matching_status}",
                    subject=inbound_email.subject,
                    sender_email=inbound_email.sender_email,
                    created_at=inbound_email.received_at,
                )
            )

        items.sort(key=lambda item: item.created_at, reverse=True)
        return items

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
        if new_contacts:
            self.contact_repository.add_all(new_contacts)
            self.contact_repository.commit()

    @staticmethod
    def _build_subject(campaign_id: UUID, base_subject: str) -> str:
        return f"{base_subject} [BMW-CAMP:{campaign_id}]"

    def _match_inbound_email(
        self,
        payload: InboundEmailCreateRequest,
        campaign_id_hint: UUID | None = None,
    ) -> tuple[CampaignDealerContact | None, str, dict]:
        checked = {
            "thread_match": False,
            "in_reply_to_match": False,
            "references_match": False,
            "campaign_token_match": False,
            "sender_match": False,
        }
        candidate_contacts: list[CampaignDealerContact] = []

        if payload.provider_thread_id:
            thread_matches = self.contact_repository.list_by_provider_thread(payload.provider, payload.provider_thread_id, campaign_id_hint)
            candidate_contacts.extend(thread_matches)
            checked["thread_match"] = len(thread_matches) == 1
            if len(thread_matches) == 1:
                return thread_matches[0], "MATCHED_BY_THREAD", self._debug_payload(checked, thread_matches)
            if len(thread_matches) > 1:
                return None, "AMBIGUOUS", self._debug_payload(checked, thread_matches)

        if payload.in_reply_to:
            in_reply_matches = self.contact_repository.list_by_message_identifiers([payload.in_reply_to], campaign_id_hint)
            candidate_contacts.extend(contact for contact in in_reply_matches if contact not in candidate_contacts)
            checked["in_reply_to_match"] = len(in_reply_matches) == 1
            if len(in_reply_matches) == 1:
                return in_reply_matches[0], "MATCHED_BY_REFERENCE", self._debug_payload(checked, in_reply_matches)
            if len(in_reply_matches) > 1:
                return None, "AMBIGUOUS", self._debug_payload(checked, in_reply_matches)

        reference_identifiers = self._extract_message_ids(payload.references)
        if reference_identifiers:
            reference_matches = self.contact_repository.list_by_message_identifiers(reference_identifiers, campaign_id_hint)
            candidate_contacts.extend(contact for contact in reference_matches if contact not in candidate_contacts)
            checked["references_match"] = len(reference_matches) == 1
            if len(reference_matches) == 1:
                return reference_matches[0], "MATCHED_BY_REFERENCE", self._debug_payload(checked, reference_matches)
            if len(reference_matches) > 1:
                return None, "AMBIGUOUS", self._debug_payload(checked, reference_matches)

        subject_campaign_id = self._extract_campaign_id_from_subject(payload.subject)
        campaign_id = campaign_id_hint or subject_campaign_id
        if campaign_id is not None:
            sender_matches = []
            if payload.sender_email:
                sender_matches = self.contact_repository.list_open_by_sender_email(payload.sender_email, campaign_id)
            candidate_contacts.extend(contact for contact in sender_matches if contact not in candidate_contacts)
            if len(sender_matches) == 1:
                if subject_campaign_id is not None:
                    checked["campaign_token_match"] = True
                    return sender_matches[0], "MATCHED_BY_CAMPAIGN_TOKEN", self._debug_payload(checked, sender_matches)
                checked["sender_match"] = True
                return sender_matches[0], "MATCHED_BY_SENDER", self._debug_payload(checked, sender_matches)
            if len(sender_matches) > 1:
                if subject_campaign_id is not None:
                    checked["campaign_token_match"] = True
                else:
                    checked["sender_match"] = True
                return None, "AMBIGUOUS", self._debug_payload(checked, sender_matches)

        if payload.sender_email:
            sender_matches = self.contact_repository.list_open_by_sender_email(payload.sender_email, campaign_id_hint)
            candidate_contacts.extend(contact for contact in sender_matches if contact not in candidate_contacts)
            if len(sender_matches) == 1:
                checked["sender_match"] = True
                return sender_matches[0], "MATCHED_BY_SENDER", self._debug_payload(checked, sender_matches)
            if len(sender_matches) > 1:
                checked["sender_match"] = True
                return None, "AMBIGUOUS", self._debug_payload(checked, sender_matches)

        return None, "UNMATCHED", self._debug_payload(checked, candidate_contacts)

    @staticmethod
    def _extract_campaign_id_from_subject(subject: str | None) -> UUID | None:
        if not subject:
            return None
        match = CAMPAIGN_TOKEN_PATTERN.search(subject)
        if not match:
            return None
        value = match.group(1).split("-")
        try:
            return UUID("-".join(value[:5]))
        except ValueError:
            return None

    @staticmethod
    def _normalize_inbound_payload(payload: InboundEmailCreateRequest) -> InboundEmailCreateRequest:
        sender_name, sender_email = CampaignContactService._normalize_sender(
            payload.sender_name,
            payload.sender_email,
        )
        return payload.model_copy(
            update={
                "subject": CampaignContactService._normalize_subject(payload.subject),
                "internet_message_id": CampaignContactService._normalize_message_id(payload.internet_message_id),
                "in_reply_to": CampaignContactService._normalize_message_id(payload.in_reply_to),
                "references": CampaignContactService._normalize_references(payload.references),
                "sender_name": sender_name,
                "sender_email": sender_email,
            }
        )

    def _resolve_campaign_hint(self, campaign_id_hint: UUID | None):
        if campaign_id_hint is None:
            return None
        campaign = self.campaign_repository.get(campaign_id_hint)
        if campaign is None:
            raise ValueError("campaign_id_hint does not reference an existing campaign.")
        if campaign.status not in {"STARTED", "COMPLETED"}:
            raise ValueError("campaign_id_hint must reference a STARTED or COMPLETED campaign.")
        return campaign

    def _resolve_single_campaign_fallback(self):
        try:
            campaign = self.single_campaign_service.get_single_campaign()
        except MultipleCampaignsError as exc:
            raise ValueError("AMBIGUOUS_CAMPAIGN_STATE") from exc
        if campaign is None:
            return None
        if campaign.status not in {"STARTED", "COMPLETED"}:
            return None
        return campaign

    @staticmethod
    def _build_inbound_response(inbound_email: InboundEmail) -> InboundEmailResponse:
        return InboundEmailResponse(
            id=inbound_email.id,
            campaign_id=inbound_email.campaign_id,
            dealer_id=inbound_email.dealer_id,
            campaign_dealer_contact_id=inbound_email.campaign_dealer_contact_id,
            mailbox_address=inbound_email.mailbox_address,
            provider=inbound_email.provider,
            provider_message_id=inbound_email.provider_message_id,
            provider_thread_id=inbound_email.provider_thread_id,
            internet_message_id=inbound_email.internet_message_id,
            sender_email=inbound_email.sender_email,
            subject=inbound_email.subject,
            received_at=inbound_email.received_at,
            processing_status=inbound_email.processing_status,
            matching_status=inbound_email.matching_status,
            can_extract=inbound_email.campaign_id is not None and inbound_email.dealer_id is not None,
            created_at=inbound_email.created_at,
            updated_at=inbound_email.updated_at,
        )

    @staticmethod
    def _normalize_subject(subject: str | None) -> str | None:
        if subject is None:
            return None
        normalized = re.sub(r"^\s*subject\s*:\s*", "", subject, flags=re.IGNORECASE).strip()
        return normalized or None

    @staticmethod
    def _normalize_message_id(value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        stripped = re.sub(r"^[a-z\-]+\s*:\s*", "", stripped, flags=re.IGNORECASE)
        match = re.search(r"<[^>]+>", stripped)
        if match:
            return match.group(0)
        return stripped or None

    @staticmethod
    def _extract_message_ids(value: str | None) -> list[str]:
        if not value:
            return []
        stripped = re.sub(r"^\s*references\s*:\s*", "", value.strip(), flags=re.IGNORECASE)
        matches = re.findall(r"<[^>]+>", stripped)
        if matches:
            return matches
        return [stripped] if stripped else []

    @staticmethod
    def _normalize_references(value: str | None) -> str | None:
        identifiers = CampaignContactService._extract_message_ids(value)
        if identifiers:
            return " ".join(identifiers)
        return None

    @staticmethod
    def _normalize_sender(sender_name: str | None, sender_email: str | None) -> tuple[str | None, str | None]:
        raw = sender_email or ""
        parsed_name, parsed_email = parseaddr(raw)
        if parsed_email:
            name = (sender_name or parsed_name or "").strip() or None
            email = parsed_email.strip().lower()
            return name, email
        if sender_email:
            return (sender_name.strip() if sender_name else None), sender_email.strip().lower()
        return (sender_name.strip() if sender_name else None), None

    @staticmethod
    def _debug_payload(checked: dict[str, bool], contacts: list[CampaignDealerContact]) -> dict:
        return {
            "checked": checked,
            "candidate_contacts": [
                {
                    "contact_id": contact.id,
                    "dealer": contact.dealer.name if contact.dealer else "Unknown Dealer",
                    "status": contact.status,
                }
                for contact in contacts
            ],
        }

    @staticmethod
    def _compose_extraction_text(
        inbound_email: InboundEmail,
        payload: InboundOfferExtractionRequest | None,
    ) -> str:
        parts = []
        if payload and payload.attachment_text:
            parts.extend(text.strip() for text in payload.attachment_text if text and text.strip())
        if inbound_email.text_body:
            parts.append(inbound_email.text_body.strip())
        elif inbound_email.html_body:
            parts.append(inbound_email.html_body.strip())
        metadata = inbound_email.raw_metadata or {}
        attachment_text = metadata.get("attachment_text")
        if isinstance(attachment_text, list):
            parts.extend(str(item).strip() for item in attachment_text if str(item).strip())
        return "\n\n".join(part for part in parts if part)

    @staticmethod
    def _analyse_offer_text(text: str) -> dict:
        lowered = text.lower()
        review_reason = None
        if any(keyword in lowered for keyword in ["eingangsbestätigung", "eingangsbestaetigung", "danke für ihre anfrage", "wir melden uns"]):
            return CampaignContactService._analysis(
                status="ACKNOWLEDGEMENT_ONLY",
                confidence=Decimal("0.20"),
                needs_review=True,
                review_reason="Acknowledgement only.",
            )
        if "?" in text or any(keyword in lowered for keyword in ["bitte teilen sie", "barzahlung oder leasing", "barzahlung", "rückfrage", "rueckfrage"]):
            return CampaignContactService._analysis(
                status="QUESTION_FROM_DEALER",
                confidence=Decimal("0.30"),
                needs_review=True,
                review_reason="Dealer asked a follow-up question.",
            )

        amounts = CampaignContactService._extract_amounts(text)
        lease_indicators = [amount for amount in amounts if amount["context"] == "lease"]
        purchase_amounts = [amount for amount in amounts if amount["context"] != "lease"]
        final_amounts = [amount for amount in purchase_amounts if amount["label"] == "final"]
        candidate_amounts = final_amounts or purchase_amounts

        if len(candidate_amounts) == 0:
            return CampaignContactService._analysis(
                status="NO_PRICE",
                confidence=Decimal("0.10"),
                needs_review=True,
                review_reason="No plausible purchase price found.",
            )
        if len(candidate_amounts) > 1:
            top_values = {amount["value"] for amount in candidate_amounts[:3]}
            if len(top_values) > 1:
                return CampaignContactService._analysis(
                    status="AMBIGUOUS",
                    confidence=Decimal("0.55"),
                    needs_review=True,
                    review_reason="Multiple plausible end prices found.",
                    raw={"candidate_prices": [str(amount["value"]) for amount in candidate_amounts[:5]]},
                )

        chosen = candidate_amounts[0]
        confidence = Decimal("0.93") if chosen["label"] == "final" else Decimal("0.78")
        status = "PRICE_EXTRACTED" if confidence >= Decimal("0.80") else "NEEDS_REVIEW"
        needs_review = confidence < Decimal("0.80")
        list_price = next((item["value"] for item in purchase_amounts if item["label"] == "list"), None)
        discount_amount = list_price - chosen["value"] if list_price and list_price > chosen["value"] else None
        discount_percent = (
            (discount_amount / list_price * Decimal("100")).quantize(Decimal("0.0001"))
            if discount_amount and list_price
            else None
        )
        return CampaignContactService._analysis(
            status=status,
            confidence=confidence,
            needs_review=needs_review,
            review_reason="Confidence below threshold." if needs_review else None,
            gross_final_price=chosen["value"],
            list_price=list_price,
            discount_amount=discount_amount,
            discount_percent=discount_percent,
            raw={
                "lease_candidates": [str(item["value"]) for item in lease_indicators],
                "purchase_candidates": [str(item["value"]) for item in purchase_amounts],
            },
        )

    @staticmethod
    def _analysis(
        *,
        status: str,
        confidence: Decimal,
        needs_review: bool,
        review_reason: str | None,
        gross_final_price: Decimal | None = None,
        list_price: Decimal | None = None,
        discount_amount: Decimal | None = None,
        discount_percent: Decimal | None = None,
        raw: dict | None = None,
    ) -> dict:
        return {
            "status": status,
            "currency": "EUR" if gross_final_price is not None else None,
            "gross_final_price": gross_final_price,
            "list_price": list_price,
            "discount_amount": discount_amount,
            "discount_percent": discount_percent,
            "delivery_cost": None,
            "registration_cost": None,
            "other_costs": None,
            "delivery_time_text": None,
            "valid_until": None,
            "price_confidence": confidence,
            "missing_fields": [] if gross_final_price is not None else ["gross_final_price"],
            "needs_review": needs_review,
            "review_reason": review_reason,
            "raw": raw or {},
        }

    @staticmethod
    def _serialize_json_value(value):
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {key: CampaignContactService._serialize_json_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [CampaignContactService._serialize_json_value(item) for item in value]
        return value

    @staticmethod
    def _extract_amounts(text: str) -> list[dict]:
        results = []
        amount_pattern = re.compile(r"(?P<amount>\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})?)\s*(?:€|eur)", flags=re.IGNORECASE)
        for match in amount_pattern.finditer(text):
            raw_amount = match.group("amount").replace(" ", "").replace(".", "").replace(",", ".")
            try:
                value = Decimal(raw_amount)
            except Exception:
                continue
            prefix_window = text[max(0, match.start() - 40) : match.start()].lower()
            suffix_window = text[match.end() : min(len(text), match.end() + 20)].lower()
            context_window = f"{prefix_window} {suffix_window}"
            context = "lease" if any(keyword in context_window for keyword in ["leasingrate", "leasing", "monat", "pro monat", "rate"]) else "purchase"
            normalized_label = "list" if "listenpreis" in prefix_window else "final"
            results.append(
                {
                    "value": value,
                    "label": normalized_label,
                    "context": context,
                }
            )
        results.sort(key=lambda item: (item["context"] == "lease", item["label"] != "final", item["value"]))
        return results
