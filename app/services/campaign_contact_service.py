from __future__ import annotations

import re
from email.utils import parseaddr
from datetime import UTC, datetime
from decimal import Decimal
from html import unescape
import unicodedata
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
from app.services.campaign_comparison_service import CampaignComparisonService
from app.services.dealer_selection_service import DealerSelectionService
from app.services.feature_normalization_service import FeatureNormalizationService
from app.services.email_template_service import DEFAULT_CUSTOMER_NAME, EmailTemplateService
from app.services.single_campaign_service import MultipleCampaignsError, SingleCampaignService
from app.entities.dealer_offer_feature import DealerOfferFeature


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
EMAIL_PATTERN = re.compile(r"(?i)(?:mailto:)?([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})")
PHONE_PATTERN = re.compile(r"(?:(?:\+|00)\d[\d\s/().\-]{6,}\d|\b0\d[\d\s/().\-]{6,}\d\b)")
POSTAL_CODE_PATTERN = re.compile(r"\b\d{5}\b")
URL_PATTERN = re.compile(r"(?i)\bhttps?://[^\s<>()]+")
GENERIC_DOMAIN_SUFFIXES = {"gmail.com", "gmx.de", "web.de", "outlook.com", "hotmail.com", "icloud.com"}
CORPORATE_DOMAINS = {"bmw.de", "mini.de"}
NAME_TITLES_PATTERN = re.compile(r"\b(herr|frau|dr|prof|dipl\.-ing)\b", flags=re.IGNORECASE)
LEGAL_FORM_PATTERN = re.compile(r"\b(gmbh|ag|kg|mbh|e\.k\.?|ohg|gbr)\b", flags=re.IGNORECASE)
COMPANY_STOPWORDS = {"bmw", "autohaus", "niederlassung", "filiale", "betrieb", "gruppe", "zentrum"}
QUOTE_SPLIT_PATTERN = re.compile(
    r"(?im)^\s*(from:|von:|to:|an:|gesendet:|betreff:|subject:|-----original message-----|weitergeleitete nachricht|forwarded message)\s*"
)
BASE64_IMAGE_PATTERN = re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=\s]+", flags=re.IGNORECASE)
SCRIPT_STYLE_PATTERN = re.compile(r"(?is)<(script|style)\b.*?>.*?</\1>")
TAG_PATTERN = re.compile(r"(?is)<[^>]+>")


class CampaignContactService:
    def __init__(self, db: Session):
        self.db = db
        self.campaign_repository = CampaignRepository(db)
        self.contact_repository = CampaignContactRepository(db)
        self.dealer_repository = DealerRepository(db)
        self.offer_repository = DealerOfferRepository(db)
        self.inbound_repository = InboundEmailRepository(db)
        self.email_template_service = EmailTemplateService()
        self.feature_normalizer = FeatureNormalizationService()
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
                customer_name=(campaign.customer_name or DEFAULT_CUSTOMER_NAME),
                customer_email=campaign.customer_email,
                customer_phone=campaign.customer_phone,
                configuration_items=self._format_configuration_items(campaign),
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
        contact, matched_dealer_id, matching_status, debug = self._match_inbound_email(
            normalized_payload,
            auto_campaign.id if auto_campaign is not None else None,
        )
        campaign_id = contact.campaign_id if contact else (
            auto_campaign.id if auto_campaign is not None else self._extract_campaign_id_from_subject(normalized_payload.subject)
        )
        dealer_id = contact.dealer_id if contact else matched_dealer_id
        if contact is None and campaign_id is not None and dealer_id is not None:
            contact = self._ensure_inbound_contact(campaign_id, dealer_id, normalized_payload.received_at)
        contact_id = contact.id if contact else None
        processing_status = "REGISTERED"
        if auto_campaign is not None and contact is None and dealer_id is None:
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
            raw_metadata=self._merge_matching_metadata(normalized_payload.raw_metadata, normalized_payload.sender_raw, debug),
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
            sender_raw=(inbound_email.raw_metadata or {}).get("sender_raw"),
            sender_email=inbound_email.sender_email,
            sender_name=inbound_email.sender_name,
            subject=inbound_email.subject,
            text_body=inbound_email.text_body,
            html_body=inbound_email.html_body,
            received_at=inbound_email.received_at,
            raw_metadata=inbound_email.raw_metadata,
        )
        _, _, _, debug = self._match_inbound_email(payload, inbound_email.campaign_id)
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
            matching_method=debug.get("matching_method"),
            matching_score=debug.get("matching_score"),
            matching_candidate_count=debug.get("matching_candidate_count", 0),
            matching_reasons=debug.get("matching_reasons", []),
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

        payload = payload or InboundOfferExtractionRequest()
        if not payload.force_reextract:
            existing_result = self._load_existing_extraction_result(inbound_email)
            if existing_result is not None:
                return existing_result

        text = self._compose_extraction_text(inbound_email, payload)
        attachment_present = self._has_attachment_text(inbound_email, payload)
        analysis = self._precheck_non_offer(inbound_email, text) or self._analyse_offer_text(
            text,
            extracted_from_attachment=attachment_present,
        )
        if inbound_email.campaign_id is None or inbound_email.dealer_id is None:
            analysis = self._analysis(
                processing_result="NEEDS_REVIEW",
                message_type="UNCLEAR",
                confidence=Decimal("0.55"),
                reason="Inbound email could not be matched to a campaign contact.",
                raw=analysis["raw"],
            )

        offer_record = self.offer_repository.get_by_inbound_email(inbound_email.id)
        try:
            self._apply_extraction_result(inbound_email, analysis)
            if analysis["processing_result"] == "OFFER_EXTRACTED":
                offer_record = self._upsert_offer_from_analysis(inbound_email, text, analysis, offer_record)
                if inbound_email.campaign_id is not None:
                    try:
                        CampaignComparisonService(self.db).compare(inbound_email.campaign_id)
                    except ValueError as exc:
                        if str(exc) != "Campaign configuration is missing":
                            raise
            elif offer_record is not None:
                self.db.delete(offer_record)
                offer_record = None
            self.offer_repository.commit()
        except Exception:
            self.offer_repository.rollback()
            raise

        return self._build_extraction_response(inbound_email, analysis, offer_record)

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
    ) -> tuple[CampaignDealerContact | None, int | None, str, dict]:
        checked = {
            "thread_match": False,
            "in_reply_to_match": False,
            "references_match": False,
            "campaign_token_match": False,
            "sender_match": False,
            "content_email_match": False,
            "content_fallback_match": False,
        }
        candidate_contacts: list[CampaignDealerContact] = []

        if payload.provider_thread_id:
            thread_matches = self.contact_repository.list_by_provider_thread(payload.provider, payload.provider_thread_id, campaign_id_hint)
            candidate_contacts.extend(thread_matches)
            checked["thread_match"] = len(thread_matches) == 1
            if len(thread_matches) == 1:
                return thread_matches[0], thread_matches[0].dealer_id, "MATCHED_BY_THREAD", self._debug_payload(
                    checked,
                    self._technical_candidates(thread_matches, 80, "thread"),
                    matching_method="thread",
                    matching_score=80,
                    matching_reasons=["provider thread matched exactly"],
                )
            if len(thread_matches) > 1:
                return None, None, "AMBIGUOUS", self._debug_payload(
                    checked,
                    self._technical_candidates(thread_matches, 80, "thread"),
                    matching_method="thread",
                )

        if payload.in_reply_to:
            in_reply_matches = self.contact_repository.list_by_message_identifiers([payload.in_reply_to], campaign_id_hint)
            candidate_contacts.extend(contact for contact in in_reply_matches if contact not in candidate_contacts)
            checked["in_reply_to_match"] = len(in_reply_matches) == 1
            if len(in_reply_matches) == 1:
                return in_reply_matches[0], in_reply_matches[0].dealer_id, "MATCHED_BY_REFERENCE", self._debug_payload(
                    checked,
                    self._technical_candidates(in_reply_matches, 100, "in_reply_to"),
                    matching_method="in_reply_to",
                    matching_score=100,
                    matching_reasons=["in-reply-to matched sent message id exactly"],
                )
            if len(in_reply_matches) > 1:
                return None, None, "AMBIGUOUS", self._debug_payload(
                    checked,
                    self._technical_candidates(in_reply_matches, 100, "in_reply_to"),
                    matching_method="in_reply_to",
                )

        reference_identifiers = self._extract_message_ids(payload.references)
        if reference_identifiers:
            reference_matches = self.contact_repository.list_by_message_identifiers(reference_identifiers, campaign_id_hint)
            candidate_contacts.extend(contact for contact in reference_matches if contact not in candidate_contacts)
            checked["references_match"] = len(reference_matches) == 1
            if len(reference_matches) == 1:
                return reference_matches[0], reference_matches[0].dealer_id, "MATCHED_BY_REFERENCE", self._debug_payload(
                    checked,
                    self._technical_candidates(reference_matches, 90, "references"),
                    matching_method="references",
                    matching_score=90,
                    matching_reasons=["references header matched sent message id exactly"],
                )
            if len(reference_matches) > 1:
                return None, None, "AMBIGUOUS", self._debug_payload(
                    checked,
                    self._technical_candidates(reference_matches, 90, "references"),
                    matching_method="references",
                )

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
                    return sender_matches[0], sender_matches[0].dealer_id, "MATCHED_BY_CAMPAIGN_TOKEN", self._debug_payload(
                        checked,
                        self._technical_candidates(sender_matches, 75, "campaign_token"),
                        matching_method="campaign_token",
                        matching_score=75,
                        matching_reasons=["campaign token and direct sender email matched"],
                    )
                checked["sender_match"] = True
                return sender_matches[0], sender_matches[0].dealer_id, "MATCHED_BY_SENDER", self._debug_payload(
                    checked,
                    self._technical_candidates(sender_matches, 75, "sender_email"),
                    matching_method="sender_email",
                    matching_score=75,
                    matching_reasons=["direct sender email matched campaign contact"],
                )
            if len(sender_matches) > 1:
                if subject_campaign_id is not None:
                    checked["campaign_token_match"] = True
                else:
                    checked["sender_match"] = True
                return None, None, "AMBIGUOUS", self._debug_payload(
                    checked,
                    self._technical_candidates(sender_matches, 75, "sender_email"),
                    matching_method="sender_email",
                )

        if payload.sender_email:
            sender_matches = self.contact_repository.list_open_by_sender_email(payload.sender_email, campaign_id_hint)
            candidate_contacts.extend(contact for contact in sender_matches if contact not in candidate_contacts)
            if len(sender_matches) == 1:
                checked["sender_match"] = True
                return sender_matches[0], sender_matches[0].dealer_id, "MATCHED_BY_SENDER", self._debug_payload(
                    checked,
                    self._technical_candidates(sender_matches, 75, "sender_email"),
                    matching_method="sender_email",
                    matching_score=75,
                    matching_reasons=["direct sender email matched campaign contact"],
                )
            if len(sender_matches) > 1:
                checked["sender_match"] = True
                return None, None, "AMBIGUOUS", self._debug_payload(
                    checked,
                    self._technical_candidates(sender_matches, 75, "sender_email"),
                    matching_method="sender_email",
                )

        if campaign_id is not None:
            content_match = self._match_contact_by_content(payload, campaign_id)
            checked["content_email_match"] = any(
                "email matched" in reason.lower() for candidate in content_match["candidate_contacts"] for reason in candidate["reasons"]
            )
            checked["content_fallback_match"] = content_match["matching_score"] > 0
            if content_match["match"] is not None:
                return content_match["match"], content_match["match"].dealer_id, "MATCHED", self._debug_payload(
                    checked,
                    content_match["candidate_contacts"],
                    matching_method=content_match["matching_method"],
                    matching_score=content_match["matching_score"],
                    matching_reasons=content_match["matching_reasons"],
                )
            if content_match["status"] == "AMBIGUOUS":
                return None, None, "AMBIGUOUS", self._debug_payload(
                    checked,
                    content_match["candidate_contacts"],
                    matching_method=content_match["matching_method"],
                    matching_score=content_match["matching_score"],
                    matching_reasons=content_match["matching_reasons"],
                )

            dealer_match = self._match_dealer_by_content(payload, campaign_id)
            checked["content_email_match"] = checked["content_email_match"] or any(
                "email matched" in reason.lower() for candidate in dealer_match["candidate_contacts"] for reason in candidate["reasons"]
            )
            checked["content_fallback_match"] = checked["content_fallback_match"] or dealer_match["matching_score"] > 0
            if dealer_match["dealer_id"] is not None:
                return None, dealer_match["dealer_id"], "MATCHED_BY_DEALER_DB", self._debug_payload(
                    checked,
                    dealer_match["candidate_contacts"],
                    matching_method=dealer_match["matching_method"],
                    matching_score=dealer_match["matching_score"],
                    matching_reasons=dealer_match["matching_reasons"],
                )
            if dealer_match["status"] == "AMBIGUOUS":
                return None, None, "AMBIGUOUS", self._debug_payload(
                    checked,
                    dealer_match["candidate_contacts"],
                    matching_method=dealer_match["matching_method"],
                    matching_score=dealer_match["matching_score"],
                    matching_reasons=dealer_match["matching_reasons"],
                )

        return None, None, "UNMATCHED", self._debug_payload(
            checked,
            self._technical_candidates(candidate_contacts, None, None),
        )

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
                "sender_raw": CampaignContactService._normalize_sender_raw(payload.sender_raw),
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
            message_type=inbound_email.message_type,
            extraction_confidence=inbound_email.extraction_confidence,
            extraction_reason=inbound_email.extraction_reason,
            processed_at=inbound_email.processed_at,
            can_extract=inbound_email.campaign_id is not None and inbound_email.dealer_id is not None,
            created_at=inbound_email.created_at,
            updated_at=inbound_email.updated_at,
        )

    @staticmethod
    def _normalize_sender_raw(sender_raw: str | None) -> str | None:
        if sender_raw is None:
            return None
        normalized = re.sub(r"^\s*from\s*:\s*", "", sender_raw, flags=re.IGNORECASE).strip()
        return normalized or None

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
    def _debug_payload(
        checked: dict[str, bool],
        contacts: list[dict],
        *,
        matching_method: str | None = None,
        matching_score: int | None = None,
        matching_reasons: list[str] | None = None,
    ) -> dict:
        return {
            "checked": checked,
            "matching_method": matching_method,
            "matching_score": matching_score,
            "matching_candidate_count": len(contacts),
            "matching_reasons": matching_reasons or [],
            "candidate_contacts": contacts,
        }

    @staticmethod
    def _technical_candidates(
        contacts: list[CampaignDealerContact],
        score: int | None,
        reason: str | None,
    ) -> list[dict]:
        return [
            {
                "contact_id": contact.id,
                "dealer_id": contact.dealer_id,
                "dealer": contact.dealer.name if contact.dealer else "Unknown Dealer",
                "status": contact.status,
                "score": score,
                "reasons": [reason] if reason else [],
            }
            for contact in contacts
        ]

    @staticmethod
    def _merge_matching_metadata(raw_metadata: dict | None, sender_raw: str | None, debug: dict) -> dict | None:
        metadata = dict(raw_metadata or {})
        if sender_raw:
            metadata["sender_raw"] = sender_raw
        if debug.get("matching_method"):
            metadata["matching_diagnostics"] = {
                "matching_method": debug.get("matching_method"),
                "matching_score": debug.get("matching_score"),
                "matching_candidate_count": debug.get("matching_candidate_count", 0),
                "matching_reasons": debug.get("matching_reasons", []),
            }
        return metadata or None

    def _match_contact_by_content(self, payload: InboundEmailCreateRequest, campaign_id: UUID) -> dict:
        contacts = self.contact_repository.list_open_for_campaign(campaign_id)
        if not contacts:
            return {
                "match": None,
                "status": "UNMATCHED",
                "matching_method": None,
                "matching_score": 0,
                "matching_reasons": [],
                "candidate_contacts": [],
            }

        message_context = self._build_message_context(payload)
        candidates = []
        for contact in contacts:
            candidate = self._score_contact_candidate(contact, payload, message_context)
            if candidate["score"] > 0:
                candidates.append(candidate)

        candidates.sort(key=lambda item: (-item["score"], -len(item["independent_signals"]), str(item["contact"].id)))
        candidate_payloads = [self._candidate_payload(item) for item in candidates]
        if not candidates:
            return {
                "match": None,
                "status": "UNMATCHED",
                "matching_method": None,
                "matching_score": 0,
                "matching_reasons": [],
                "candidate_contacts": [],
            }

        best = candidates[0]
        second_score = candidates[1]["score"] if len(candidates) > 1 else 0
        if self._is_content_match_acceptable(best["score"], len(best["independent_signals"]), second_score):
            return {
                "match": best["contact"],
                "status": "MATCHED",
                "matching_method": best["matching_method"],
                "matching_score": best["score"],
                "matching_reasons": best["reasons"],
                "candidate_contacts": candidate_payloads,
            }

        if len(candidates) > 1:
            return {
                "match": None,
                "status": "AMBIGUOUS",
                "matching_method": best["matching_method"],
                "matching_score": best["score"],
                "matching_reasons": best["reasons"],
                "candidate_contacts": candidate_payloads,
            }

        return {
            "match": None,
            "status": "UNMATCHED",
            "matching_method": best["matching_method"],
            "matching_score": best["score"],
            "matching_reasons": best["reasons"],
            "candidate_contacts": candidate_payloads,
        }

    def _match_dealer_by_content(self, payload: InboundEmailCreateRequest, campaign_id: UUID) -> dict:
        dealers = self.dealer_repository.get_all()
        if not dealers:
            return {
                "dealer_id": None,
                "status": "UNMATCHED",
                "matching_method": None,
                "matching_score": 0,
                "matching_reasons": [],
                "candidate_contacts": [],
            }

        existing_contact_dealer_ids = {
            contact.dealer_id
            for contact in self.contact_repository.list_open_for_campaign(campaign_id)
        }
        message_context = self._build_message_context(payload)
        candidates = []
        for dealer in dealers:
            if dealer.id in existing_contact_dealer_ids:
                continue
            candidate = self._score_dealer_candidate(dealer, payload, message_context)
            if candidate["score"] > 0:
                candidates.append(candidate)

        candidates.sort(key=lambda item: (-item["score"], -len(item["independent_signals"]), item["dealer"].id))
        candidate_payloads = [self._dealer_candidate_payload(item) for item in candidates]
        if not candidates:
            return {
                "dealer_id": None,
                "status": "UNMATCHED",
                "matching_method": None,
                "matching_score": 0,
                "matching_reasons": [],
                "candidate_contacts": [],
            }

        best = candidates[0]
        second_score = candidates[1]["score"] if len(candidates) > 1 else 0
        if self._is_content_match_acceptable(best["score"], len(best["independent_signals"]), second_score):
            return {
                "dealer_id": best["dealer"].id,
                "status": "MATCHED",
                "matching_method": best["matching_method"],
                "matching_score": best["score"],
                "matching_reasons": best["reasons"],
                "candidate_contacts": candidate_payloads,
            }

        if len(candidates) > 1:
            return {
                "dealer_id": None,
                "status": "AMBIGUOUS",
                "matching_method": best["matching_method"],
                "matching_score": best["score"],
                "matching_reasons": best["reasons"],
                "candidate_contacts": candidate_payloads,
            }

        return {
            "dealer_id": None,
            "status": "UNMATCHED",
            "matching_method": best["matching_method"],
            "matching_score": best["score"],
            "matching_reasons": best["reasons"],
            "candidate_contacts": candidate_payloads,
        }

    def _score_dealer_candidate(self, dealer, payload: InboundEmailCreateRequest, context: dict) -> dict:
        candidate = self._score_candidate_for_dealer(dealer, context)
        candidate["dealer"] = dealer
        return candidate

    @staticmethod
    def _is_content_match_acceptable(score: int, independent_signal_count: int, second_score: int) -> bool:
        if score >= 70 and score - second_score >= 20:
            return True
        return score >= 60 and independent_signal_count >= 2 and score - second_score >= 20

    def _build_message_context(self, payload: InboundEmailCreateRequest) -> dict:
        html_text = self._html_to_text(payload.html_body)
        combined_text = "\n\n".join(
            part for part in [payload.text_body or "", html_text] if part and part.strip()
        )
        current_text, quoted_text = self._split_current_and_quoted_text(combined_text)
        ignored_emails = self._ignored_user_emails(payload)
        current_emails = self._extract_emails(current_text, ignored_emails)
        quoted_emails = self._extract_emails(quoted_text, ignored_emails)
        sender_raw_emails = self._extract_emails(payload.sender_raw or "", ignored_emails)
        sender_email_values = self._extract_emails(payload.sender_email or "", ignored_emails)
        current_phones = self._extract_phone_numbers(current_text)
        quoted_phones = self._extract_phone_numbers(quoted_text)
        sender_domains = {
            self._email_domain(value)
            for value in current_emails | quoted_emails | sender_raw_emails | sender_email_values
            if self._email_domain(value)
        }
        url_domains = self._extract_url_domains(combined_text)
        current_text_normalized = self._normalize_text_for_search(current_text)
        quoted_text_normalized = self._normalize_text_for_search(quoted_text)
        return {
            "current_text": current_text,
            "quoted_text": quoted_text,
            "current_text_normalized": current_text_normalized,
            "quoted_text_normalized": quoted_text_normalized,
            "current_emails": current_emails | sender_raw_emails | sender_email_values,
            "quoted_emails": quoted_emails,
            "current_phones": current_phones,
            "quoted_phones": quoted_phones,
            "postal_codes": set(POSTAL_CODE_PATTERN.findall(combined_text)),
            "domains": sender_domains,
            "url_domains": url_domains,
        }

    def _score_contact_candidate(self, contact: CampaignDealerContact, payload: InboundEmailCreateRequest, context: dict) -> dict:
        dealer = contact.dealer
        if dealer is None:
            return {"contact": contact, "score": 0, "reasons": [], "independent_signals": set(), "matching_method": None}

        candidate = self._score_candidate_for_dealer(dealer, context)
        candidate["contact"] = contact
        return candidate

    def _score_candidate_for_dealer(self, dealer, context: dict) -> dict:
        score = 0
        reasons: list[str] = []
        independent_signals: set[str] = set()
        dealer_emails = self._dealer_emails(dealer)
        current_email_matches = sorted(context["current_emails"] & dealer_emails)
        quoted_email_matches = sorted(context["quoted_emails"] & dealer_emails)
        if current_email_matches:
            score += 70
            independent_signals.add("content_email")
            reasons.append(f"current content email matched: {current_email_matches[0]}")
        elif quoted_email_matches:
            score += 55
            independent_signals.add("quoted_email")
            reasons.append(f"quoted content email matched: {quoted_email_matches[0]}")

        dealer_phones = self._dealer_phones(dealer)
        phone_match = sorted((context["current_phones"] | context["quoted_phones"]) & dealer_phones)
        if phone_match:
            score += 45
            independent_signals.add("phone")
            reasons.append("phone number matched")

        company_match_score, company_reason = self._company_match_score(dealer, context["current_text_normalized"], context["quoted_text_normalized"])
        if company_match_score:
            score += company_match_score
            independent_signals.add("company")
            reasons.append(company_reason)

        if dealer.postal_code and dealer.city:
            normalized_city = self._normalize_text_for_search(dealer.city)
            if dealer.postal_code in context["postal_codes"] and normalized_city and normalized_city in context["current_text_normalized"]:
                score += 25
                independent_signals.add("postal_city")
                reasons.append("postal code and city matched")

        street_reason = self._street_match_reason(dealer, context["current_text_normalized"])
        if street_reason:
            score += 25
            independent_signals.add("street")
            reasons.append(street_reason)

        if {"company", "postal_city", "street"}.issubset(independent_signals):
            score += 20
            independent_signals.add("address_cluster")
            reasons.append("dealer company and full address cluster matched")

        dealer_domains = {self._email_domain(email) for email in dealer_emails if self._email_domain(email)}
        matched_domains = {
            domain
            for domain in context["domains"] & dealer_domains
            if domain and domain not in GENERIC_DOMAIN_SUFFIXES and domain not in CORPORATE_DOMAINS
        }
        if matched_domains:
            score += 10
            independent_signals.add("domain")
            reasons.append(f"dealer domain matched: {sorted(matched_domains)[0]}")

        homepage_domains = self._dealer_homepage_domains(dealer)
        matched_homepage_domains = context["url_domains"] & homepage_domains
        if matched_homepage_domains:
            score += 20
            independent_signals.add("homepage")
            reasons.append(f"dealer homepage domain matched: {sorted(matched_homepage_domains)[0]}")

        if (
            "company" in independent_signals
            and ("street" in independent_signals or "postal_city" in independent_signals)
            and any(domain in CORPORATE_DOMAINS for domain in context["domains"])
        ):
            score += 15
            independent_signals.add("corporate_signature")
            reasons.append("corporate BMW signature matched dealer location")

        matching_method = None
        if current_email_matches or quoted_email_matches:
            matching_method = "content_email"
        elif matched_homepage_domains:
            matching_method = "homepage"
        elif street_reason or ("postal_city" in independent_signals and "company" in independent_signals):
            matching_method = "name_company_address"
        elif phone_match:
            matching_method = "signature"
        elif matched_domains:
            matching_method = "content_email"

        return {
            "contact": None,
            "score": score,
            "reasons": reasons,
            "independent_signals": independent_signals,
            "matching_method": matching_method,
        }

    def _company_match_score(self, dealer, current_text_normalized: str, quoted_text_normalized: str) -> tuple[int, str | None]:
        normalized_name = self._normalize_text_for_search(dealer.name)
        simplified_name = self._normalize_company_name(dealer.name)
        current_tokens = set(current_text_normalized.split())
        quoted_tokens = set(quoted_text_normalized.split())
        distinctive_tokens = [
            token for token in simplified_name.split() if len(token) > 2 and token not in COMPANY_STOPWORDS
        ]
        if simplified_name and len(simplified_name) >= 10 and simplified_name in current_text_normalized:
            return 35, "dealer company name matched in current message"
        if len(distinctive_tokens) >= 2 and all(token in current_tokens for token in distinctive_tokens[:3]):
            return 35, "dealer company tokens matched in current message"
        if simplified_name and len(simplified_name) >= 10 and simplified_name in quoted_text_normalized:
            return 20, "dealer company name matched in quoted message"
        if normalized_name and normalized_name in current_text_normalized and simplified_name != "bmw":
            return 20, "dealer name matched in current message"
        if len(distinctive_tokens) >= 2 and all(token in quoted_tokens for token in distinctive_tokens[:3]):
            return 20, "dealer company tokens matched in quoted message"
        return 0, None

    @staticmethod
    def _street_match_reason(dealer, current_text_normalized: str) -> str | None:
        if not dealer.street:
            return None
        street_tokens = CampaignContactService._split_street_components(dealer.street)
        if not street_tokens:
            return None
        street_name, house_number = street_tokens
        if street_name and house_number and street_name in current_text_normalized and house_number in current_text_normalized:
            return "street and house number matched"
        return None

    @staticmethod
    def _split_street_components(street: str) -> tuple[str | None, str | None]:
        normalized = CampaignContactService._normalize_text_for_search(street)
        normalized = normalized.replace("strasse", "str").replace("straße", "str")
        match = re.search(r"(.+?)\s+(\d+[a-zA-Z]?)$", normalized)
        if not match:
            return normalized or None, None
        return match.group(1).strip(), match.group(2).strip()

    @staticmethod
    def _candidate_payload(candidate: dict) -> dict:
        contact = candidate["contact"]
        return {
            "contact_id": contact.id,
            "dealer_id": contact.dealer_id,
            "dealer": contact.dealer.name if contact.dealer else "Unknown Dealer",
            "status": contact.status,
            "score": candidate["score"],
            "reasons": candidate["reasons"],
        }

    @staticmethod
    def _dealer_candidate_payload(candidate: dict) -> dict:
        dealer = candidate["dealer"]
        return {
            "contact_id": None,
            "dealer_id": dealer.id,
            "dealer": dealer.name,
            "status": "DEALER_DB_ONLY",
            "score": candidate["score"],
            "reasons": candidate["reasons"],
        }

    def _ensure_inbound_contact(
        self,
        campaign_id: UUID,
        dealer_id: int,
        received_at: datetime,
    ) -> CampaignDealerContact:
        existing = self.contact_repository.get_by_campaign_and_dealer(campaign_id, dealer_id)
        if existing is not None:
            return existing

        dealer = self.dealer_repository.get_by_id(dealer_id)
        if dealer is None:
            raise LookupError("Dealer not found")

        recipient_email = next(
            (
                value.strip()
                for value in [dealer.email, dealer.new_car_email, dealer.used_car_email]
                if value and value.strip()
            ),
            None,
        )
        contact = CampaignDealerContact(
            campaign_id=campaign_id,
            dealer_id=dealer.id,
            status="REPLIED",
            recipient_email=recipient_email,
            replied_at=received_at,
            outbound_message_key=f"campaign:{campaign_id}:dealer:{dealer.id}:inbound-only",
        )
        contact.dealer = dealer
        return self.contact_repository.add(contact)

    @staticmethod
    def _dealer_emails(dealer) -> set[str]:
        return {
            value.strip().lower()
            for value in [dealer.email, dealer.new_car_email, dealer.used_car_email]
            if value and value.strip()
        }

    @staticmethod
    def _dealer_homepage_domains(dealer) -> set[str]:
        values = set()
        for value in [dealer.homepage]:
            domain = CampaignContactService._normalize_domain_from_url(value)
            if domain:
                values.add(domain)
        return values

    @staticmethod
    def _dealer_phones(dealer) -> set[str]:
        return {
            value
            for value in [
                CampaignContactService._normalize_phone(dealer.phone),
                CampaignContactService._normalize_phone(dealer.new_car_phone),
                CampaignContactService._normalize_phone(dealer.used_car_phone),
            ]
            if value
        }

    @staticmethod
    def _ignored_user_emails(payload: InboundEmailCreateRequest) -> set[str]:
        ignored = {payload.mailbox_address.strip().lower()}
        metadata = payload.raw_metadata or {}
        for key in ["known_user_emails", "user_emails", "ignored_emails"]:
            values = metadata.get(key)
            if isinstance(values, list):
                ignored.update(str(value).strip().lower() for value in values if str(value).strip())
        return ignored

    @staticmethod
    def _extract_emails(value: str, ignored: set[str]) -> set[str]:
        matches = set()
        for match in EMAIL_PATTERN.findall(value or ""):
            normalized = match.strip().strip(" <>[]()\"'").lower()
            if normalized and normalized not in ignored:
                matches.add(normalized)
        return matches

    @staticmethod
    def _extract_phone_numbers(value: str) -> set[str]:
        return {
            normalized
            for normalized in (
                CampaignContactService._normalize_phone(match.group(0))
                for match in PHONE_PATTERN.finditer(value or "")
            )
            if normalized
        }

    @staticmethod
    def _extract_url_domains(value: str) -> set[str]:
        domains = set()
        for match in URL_PATTERN.findall(value or ""):
            domain = CampaignContactService._normalize_domain_from_url(match)
            if domain:
                domains.add(domain)
        return domains

    @staticmethod
    def _normalize_phone(value: str | None) -> str | None:
        if not value:
            return None
        normalized = re.sub(r"[^\d+]", "", value)
        if normalized.startswith("00"):
            normalized = f"+{normalized[2:]}"
        if normalized.startswith("+49"):
            normalized = f"0{normalized[3:]}"
        if len(normalized) < 7:
            return None
        return normalized

    @staticmethod
    def _email_domain(email: str | None) -> str | None:
        if not email or "@" not in email:
            return None
        return email.rsplit("@", 1)[1].lower()

    @staticmethod
    def _normalize_domain_from_url(value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().lower()
        normalized = re.sub(r"^[a-z]+://", "", normalized)
        normalized = normalized.split("/", 1)[0]
        normalized = normalized.split("?", 1)[0]
        normalized = normalized.split("#", 1)[0]
        normalized = normalized.split(":", 1)[0]
        normalized = normalized.strip()
        if normalized.startswith("www."):
            normalized = normalized[4:]
        return normalized or None

    @staticmethod
    def _html_to_text(html_body: str | None) -> str:
        if not html_body:
            return ""
        text = BASE64_IMAGE_PATTERN.sub(" ", html_body)
        text = SCRIPT_STYLE_PATTERN.sub(" ", text)
        text = re.sub(r"(?i)mailto:", "", text)
        text = TAG_PATTERN.sub(" ", text)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()[:12000]

    @staticmethod
    def _split_current_and_quoted_text(text: str) -> tuple[str, str]:
        if not text:
            return "", ""
        marker_match = QUOTE_SPLIT_PATTERN.search(text)
        if marker_match is None:
            return text[:12000], ""
        marker = marker_match.group(1).lower()
        if marker_match.start() < 120 and marker not in {"-----original message-----", "weitergeleitete nachricht", "forwarded message"}:
            return text[:12000], ""
        index = marker_match.start()
        return text[:index].strip()[:12000], text[index:].strip()[:12000]

    @staticmethod
    def _normalize_text_for_search(value: str | None) -> str:
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKC", value).lower()
        normalized = normalized.replace("ß", "ss")
        normalized = NAME_TITLES_PATTERN.sub(" ", normalized)
        normalized = re.sub(r"[^\w\s@]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    @staticmethod
    def _normalize_company_name(value: str | None) -> str:
        normalized = CampaignContactService._normalize_text_for_search(value)
        normalized = LEGAL_FORM_PATTERN.sub(" ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

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
    def _has_attachment_text(
        inbound_email: InboundEmail,
        payload: InboundOfferExtractionRequest | None,
    ) -> bool:
        if payload and any(text and text.strip() for text in payload.attachment_text):
            return True
        metadata = inbound_email.raw_metadata or {}
        attachment_text = metadata.get("attachment_text")
        return isinstance(attachment_text, list) and any(str(item).strip() for item in attachment_text)

    @staticmethod
    def _analyse_offer_text(text: str, *, extracted_from_attachment: bool = False) -> dict:
        lowered = text.lower()
        normalized = CampaignContactService._normalize_text_for_matching(text)

        if CampaignContactService._is_outbound_copy(normalized):
            return CampaignContactService._analysis(
                processing_result="NO_OFFER",
                message_type="OUTBOUND_COPY",
                confidence=Decimal("1.00"),
            )
        if CampaignContactService._contains_any(
            normalized,
            [
                "abwesenheitsnotiz",
                "automatic reply",
                "automatische antwort",
                "out of office",
                "ihre nachricht ist bei uns eingegangen",
                "wir haben ihre nachricht erhalten",
                "vielen dank fuer ihre anfrage. wir melden uns",
            ],
        ):
            return CampaignContactService._analysis(
                processing_result="NO_OFFER",
                message_type="AUTO_REPLY",
                confidence=Decimal("0.97"),
                reason="Automatic acknowledgement without a concrete offer.",
            )
        if CampaignContactService._contains_any(
            normalized,
            [
                "wir koennen derzeit kein angebot erstellen",
                "das fahrzeug ist nicht verfuegbar",
                "wir fuehren dieses modell nicht",
                "leider koennen wir ihre anfrage nicht bearbeiten",
            ],
        ):
            return CampaignContactService._analysis(
                processing_result="NO_OFFER",
                message_type="DECLINE",
                confidence=Decimal("0.96"),
                reason="Dealer declined or cannot provide an offer.",
            )

        structured_cash_offer = CampaignContactService._extract_bmw_cash_offer(
            text,
            extracted_from_attachment=extracted_from_attachment,
        )
        if structured_cash_offer is not None:
            return CampaignContactService._analysis(
                processing_result="OFFER_EXTRACTED",
                message_type="OFFER",
                confidence=structured_cash_offer["quality"]["confidence"],
                offer=structured_cash_offer,
                raw={"strategy": "structured_bmw_offer"},
            )

        amounts = CampaignContactService._extract_amounts(text)
        lease_indicators = [amount for amount in amounts if amount["context"] == "lease"]
        purchase_amounts = [amount for amount in amounts if amount["context"] != "lease"]
        final_amounts = [amount for amount in purchase_amounts if amount["label"] == "final"]
        candidate_amounts = final_amounts or purchase_amounts
        looks_like_question = "?" in text or CampaignContactService._contains_any(
            normalized,
            [
                "bitte teilen sie",
                "barzahlung oder leasing",
                "privat- oder firmenkauf",
                "welche laufzeit",
                "wie viele kilometer",
                "bitte senden sie die konfiguration erneut",
                "rueckfrage",
            ],
        )

        lease_offer = CampaignContactService._extract_lease_offer(text)

        if len(candidate_amounts) == 0:
            if looks_like_question:
                return CampaignContactService._analysis(
                    processing_result="NO_OFFER",
                    message_type="QUESTION_FROM_DEALER",
                    confidence=Decimal("0.97"),
                    reason="Dealer asked follow-up questions without a concrete offer.",
                )
            if lease_offer is not None:
                return CampaignContactService._analysis(
                    processing_result="NO_OFFER",
                    message_type="LEASING_OR_FINANCING_IRRELEVANT",
                    confidence=Decimal("0.95"),
                    reason="Leasing or financing examples are ignored for offer ranking.",
                    raw={"lease_offer": lease_offer},
                )
            return CampaignContactService._analysis(
                processing_result="NO_OFFER",
                message_type="NO_COMMERCIAL_TERMS",
                confidence=Decimal("0.93"),
                reason="No concrete commercial offer data found.",
            )
        if len(candidate_amounts) > 1:
            top_values = {amount["value"] for amount in candidate_amounts[:3]}
            if len(top_values) > 1:
                return CampaignContactService._analysis(
                    processing_result="NEEDS_REVIEW",
                    message_type="UNCLEAR",
                    confidence=Decimal("0.55"),
                    reason="Multiple plausible end prices found.",
                    raw={"candidate_prices": [str(amount["value"]) for amount in candidate_amounts[:5]]},
                )

        chosen = candidate_amounts[0]
        confidence = Decimal("0.93") if chosen["label"] == "final" else Decimal("0.78")
        list_price = next((item["value"] for item in purchase_amounts if item["label"] == "list"), None)
        discount_amount = list_price - chosen["value"] if list_price and list_price > chosen["value"] else None
        discount_percent = (
            (discount_amount / list_price * Decimal("100")).quantize(Decimal("0.0001"))
            if discount_amount and list_price
            else None
        )
        cash_offer = {
            "offer_type": "CASH",
            "pricing": {
                "currency": "EUR",
                "list_price": list_price,
                "discount_amount": discount_amount,
                "discount_percent": discount_percent,
                "vehicle_price": chosen["value"],
                "transfer_cost": None,
                "registration_cost": None,
                "additional_costs": None,
                "total_cash_price": chosen["value"],
                "monthly_rate": None,
                "down_payment": None,
                "final_payment": None,
                "annual_percentage_rate": None,
                "term_months": None,
                "annual_mileage_km": None,
                "total_lease_cost": None,
                "total_financing_cost": None,
            },
            "source": {
                "extracted_from_email": not extracted_from_attachment,
                "extracted_from_attachment": extracted_from_attachment,
            },
            "quality": {
                "confidence": confidence,
                "missing_fields": [],
                "warnings": [],
                "evidence": CampaignContactService._build_evidence(
                    "pricing.total_cash_price",
                    chosen["excerpt"],
                    chosen["value"],
                    source="attachment_text" if extracted_from_attachment else "email_text",
                ),
            },
        }
        if confidence < Decimal("0.80"):
            return CampaignContactService._analysis(
                processing_result="NEEDS_REVIEW",
                message_type="UNCLEAR",
                confidence=confidence,
                reason="Price found, but the final offer price is not explicit enough.",
                offer=cash_offer,
                missing_fields=["pricing.total_cash_price"],
                raw={
                    "lease_candidates": [str(item["value"]) for item in lease_indicators],
                    "purchase_candidates": [str(item["value"]) for item in purchase_amounts],
                },
            )
        return CampaignContactService._analysis(
            processing_result="OFFER_EXTRACTED",
            message_type="OFFER",
            confidence=confidence,
            offer=cash_offer,
            raw={
                "lease_candidates": [str(item["value"]) for item in lease_indicators],
                "purchase_candidates": [str(item["value"]) for item in purchase_amounts],
            },
        )

    @staticmethod
    def _analysis(
        *,
        processing_result: str,
        message_type: str,
        confidence: Decimal,
        reason: str | None = None,
        offer: dict | None = None,
        missing_fields: list[str] | None = None,
        raw: dict | None = None,
    ) -> dict:
        pricing = offer.get("pricing", {}) if offer else {}
        gross_final_price = pricing.get("total_cash_price") or pricing.get("vehicle_price")
        needs_review = processing_result == "NEEDS_REVIEW"
        return {
            "processing_result": processing_result,
            "message_type": message_type,
            "status": processing_result,
            "currency": pricing.get("currency"),
            "gross_final_price": gross_final_price,
            "list_price": pricing.get("list_price"),
            "discount_amount": pricing.get("discount_amount"),
            "discount_percent": pricing.get("discount_percent"),
            "delivery_cost": None,
            "registration_cost": None,
            "other_costs": None,
            "delivery_time_text": None,
            "valid_until": None,
            "price_confidence": confidence if gross_final_price is not None else None,
            "confidence": confidence,
            "offer": offer,
            "missing_fields": missing_fields or [],
            "needs_review": needs_review,
            "review_reason": reason,
            "reason": reason,
            "raw": raw or {},
        }

    @staticmethod
    def _normalize_text_for_matching(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        return normalized.lower()

    @staticmethod
    def _contains_any(text: str, phrases: list[str]) -> bool:
        return any(phrase in text for phrase in phrases)

    @staticmethod
    def _is_outbound_copy(text: str) -> bool:
        return "[test]" in text or "testversand - diese e-mail wurde nicht an den handler gesendet" in text

    @staticmethod
    def _precheck_non_offer(inbound_email: InboundEmail, text: str) -> dict | None:
        sender_email = (inbound_email.sender_email or "").strip().lower()
        mailbox_address = inbound_email.mailbox_address.strip().lower()
        subject = (inbound_email.subject or "").strip().lower()
        normalized_text = CampaignContactService._normalize_text_for_matching(text)

        if sender_email and sender_email == mailbox_address:
            return CampaignContactService._analysis(
                processing_result="NO_OFFER",
                message_type="OUTBOUND_COPY",
                confidence=Decimal("1.00"),
                reason="Sender and mailbox address are identical.",
            )
        if subject.startswith("[test]") or CampaignContactService._is_outbound_copy(normalized_text):
            return CampaignContactService._analysis(
                processing_result="NO_OFFER",
                message_type="OUTBOUND_COPY",
                confidence=Decimal("1.00"),
                reason="Detected internal test or outbound copy.",
            )
        return None

    @staticmethod
    def _build_evidence(field: str, excerpt: str, value: Decimal, *, source: str = "email_text") -> list[dict]:
        cleaned_excerpt = " ".join(excerpt.split())
        return [{"field": field, "value": value, "source": source, "excerpt": cleaned_excerpt[:200]}]

    @staticmethod
    def _extract_bmw_cash_offer(text: str, *, extracted_from_attachment: bool) -> dict | None:
        segment = CampaignContactService._primary_offer_segment(text)

        total_cash_price = CampaignContactService._extract_labeled_line_amount(segment, "Gesamtpreis")
        if total_cash_price is None:
            return None

        vehicle_price = CampaignContactService._extract_labeled_line_amount(segment, "Modell")
        equipment_price = CampaignContactService._extract_labeled_line_amount(segment, "Ausstattung")
        dealer_services = CampaignContactService._extract_labeled_line_amount(segment, "Händlerleistungen")
        list_price = CampaignContactService._extract_labeled_amount(
            segment,
            r"(?is)Bruttolistenpreis.*?betr(?:ä|ae)?gt\s+(?P<amount>\d{1,3}(?:[.\s]\d{3})*(?:,\d{2}))\s*EUR",
        )
        if list_price is None:
            sum_model_equipment = CampaignContactService._extract_labeled_line_amount(segment, "Summe Modell und Ausstattung")
            list_price = sum_model_equipment

        discount_amount = CampaignContactService._extract_labeled_line_amount(segment, "Nachlass", absolute=True)
        discount_percent_match = re.search(
            r"(?is)Nachlass[^(]*\(([\d,]+)%\)",
            segment,
        )
        discount_percent = (
            Decimal(discount_percent_match.group(1).replace(",", "."))
            if discount_percent_match is not None
            else None
        )
        if discount_amount is None and list_price and total_cash_price and list_price > total_cash_price:
            discount_amount = list_price - total_cash_price
        if discount_percent is None and list_price and discount_amount:
            discount_percent = ((discount_amount / list_price) * Decimal("100")).quantize(Decimal("0.0001"))

        evidence = []
        source = "attachment_text" if extracted_from_attachment else "email_text"
        evidence.extend(
            CampaignContactService._build_evidence(
                "pricing.total_cash_price",
                CampaignContactService._excerpt_around_keyword(segment, "Gesamtpreis"),
                total_cash_price,
                source=source,
            )
        )
        if list_price is not None:
            evidence.extend(
                CampaignContactService._build_evidence(
                    "pricing.list_price",
                    CampaignContactService._excerpt_around_keyword(segment, "Bruttolistenpreis"),
                    list_price,
                    source=source,
                )
            )
        if discount_amount is not None:
            evidence.extend(
                CampaignContactService._build_evidence(
                    "pricing.discount_amount",
                    CampaignContactService._excerpt_around_keyword(segment, "Nachlass"),
                    discount_amount,
                    source=source,
                )
            )

        return {
            "offer_type": "CASH",
            "pricing": {
                "currency": "EUR",
                "list_price": list_price,
                "discount_amount": discount_amount,
                "discount_percent": discount_percent,
                "vehicle_price": vehicle_price or total_cash_price,
                "transfer_cost": None,
                "registration_cost": None,
                "additional_costs": dealer_services,
                "total_cash_price": total_cash_price,
                "monthly_rate": None,
                "down_payment": None,
                "final_payment": None,
                "annual_percentage_rate": None,
                "term_months": None,
                "annual_mileage_km": None,
                "total_lease_cost": None,
                "total_financing_cost": None,
                "equipment_price": equipment_price,
            },
            "source": {
                "extracted_from_email": not extracted_from_attachment,
                "extracted_from_attachment": extracted_from_attachment,
            },
            "quality": {
                "confidence": Decimal("0.99"),
                "missing_fields": [],
                "warnings": [],
                "evidence": evidence,
            },
        }

    @staticmethod
    def _primary_offer_segment(text: str) -> str:
        split_markers = [
            r"(?i)\bBMW Financial Services\b",
            r"(?i)\bLeasingbeispiel\b",
            r"(?i)\bInformation über den Energieverbrauch\b",
            r"(?i)\bMögliche CO\s*-?Kosten\b",
        ]
        split_index = len(text)
        for pattern in split_markers:
            match = re.search(pattern, text)
            if match is not None:
                split_index = min(split_index, match.start())
        return text[:split_index]

    @staticmethod
    def _extract_labeled_amount(text: str, pattern: str, *, absolute: bool = False) -> Decimal | None:
        match = re.search(pattern, text)
        if match is None:
            return None
        raw = match.group("amount").replace(" ", "").replace(".", "").replace(",", ".")
        try:
            value = Decimal(raw)
        except Exception:
            return None
        return abs(value) if absolute else value

    @staticmethod
    def _extract_labeled_line_amount(text: str, label: str, *, absolute: bool = False) -> Decimal | None:
        escaped = re.escape(label)
        for line in text.splitlines():
            if not re.search(escaped, line, flags=re.IGNORECASE):
                continue
            amount = CampaignContactService._extract_last_amount_from_text(line)
            if amount is not None:
                return abs(amount) if absolute else amount
        return None

    @staticmethod
    def _extract_last_amount_from_text(text: str) -> Decimal | None:
        matches = re.findall(r"-?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})", text)
        if not matches:
            return None
        raw = matches[-1].replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return Decimal(raw)
        except Exception:
            return None

    @staticmethod
    def _excerpt_around_keyword(text: str, keyword: str, radius: int = 120) -> str:
        match = re.search(re.escape(keyword), text, flags=re.IGNORECASE)
        if match is None:
            return text[:radius]
        start = max(0, match.start() - radius // 2)
        end = min(len(text), match.end() + radius // 2)
        return text[start:end]

    @staticmethod
    def _extract_lease_offer(text: str) -> dict | None:
        lowered = text.lower()
        if not any(keyword in lowered for keyword in ["leasing", "leasingrate", "monat"]):
            return None
        monthly_rate_match = re.search(r"(?i)(?:leasingrate|rate)\s+(\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})?)\s*(?:€|eur)", text)
        term_match = re.search(r"(?i)(\d{1,3})\s*monate", text)
        mileage_match = re.search(r"(?i)(\d{1,3}(?:[.\s]\d{3})*)\s*km", text)
        if monthly_rate_match is None and term_match is None:
            return None
        monthly_rate = (
            Decimal(monthly_rate_match.group(1).replace(" ", "").replace(".", "").replace(",", "."))
            if monthly_rate_match is not None
            else None
        )
        term_months = int(term_match.group(1)) if term_match is not None else None
        annual_mileage = int(mileage_match.group(1).replace(".", "").replace(" ", "")) if mileage_match is not None else None
        return {
            "offer_type": "LEASING",
            "pricing": {
                "currency": "EUR",
                "list_price": None,
                "discount_amount": None,
                "discount_percent": None,
                "vehicle_price": None,
                "transfer_cost": None,
                "registration_cost": None,
                "additional_costs": None,
                "total_cash_price": None,
                "monthly_rate": monthly_rate,
                "down_payment": None,
                "final_payment": None,
                "annual_percentage_rate": None,
                "term_months": term_months,
                "annual_mileage_km": annual_mileage,
                "total_lease_cost": None,
                "total_financing_cost": None,
            },
            "source": {
                "extracted_from_email": True,
                "extracted_from_attachment": False,
            },
            "quality": {
                "confidence": Decimal("0.91"),
                "missing_fields": [],
                "warnings": [],
                "evidence": [],
            },
        }

    def _load_existing_extraction_result(self, inbound_email: InboundEmail) -> InboundOfferExtractionResponse | None:
        metadata = inbound_email.raw_metadata or {}
        stored = metadata.get("offer_extraction")
        if not isinstance(stored, dict):
            return None
        offer_record = self.offer_repository.get_by_inbound_email(inbound_email.id)
        analysis = self._deserialize_analysis(stored)
        return self._build_extraction_response(inbound_email, analysis, offer_record)

    def _apply_extraction_result(self, inbound_email: InboundEmail, analysis: dict) -> None:
        inbound_email.processing_status = analysis["processing_result"]
        inbound_email.message_type = analysis["message_type"]
        inbound_email.extraction_confidence = analysis["confidence"]
        inbound_email.extraction_reason = analysis["reason"]
        inbound_email.processed_at = datetime.now(UTC)
        metadata = dict(inbound_email.raw_metadata or {})
        metadata["offer_extraction"] = self._serialize_json_value(analysis)
        inbound_email.raw_metadata = metadata
        if inbound_email.contact is not None:
            inbound_email.contact.status = analysis["processing_result"]

    def _upsert_offer_from_analysis(
        self,
        inbound_email: InboundEmail,
        text: str,
        analysis: dict,
        existing_offer: DealerOffer | None,
    ) -> DealerOffer:
        offer_data = analysis["offer"] or {}
        pricing = offer_data.get("pricing", {})
        offer = existing_offer or DealerOffer(
            campaign_id=inbound_email.campaign_id,
            dealer_id=inbound_email.dealer_id,
            inbound_email_id=inbound_email.id,
            dealer_name=inbound_email.contact.dealer.name if inbound_email.contact and inbound_email.contact.dealer else (inbound_email.sender_name or inbound_email.sender_email or "Unknown Dealer"),
            source_type="email",
            raw_response=text.strip() or "(empty email)",
        )
        offer.campaign_id = inbound_email.campaign_id
        offer.dealer_id = inbound_email.dealer_id
        offer.dealer_name = (
            inbound_email.contact.dealer.name
            if inbound_email.contact and inbound_email.contact.dealer
            else (inbound_email.sender_name or inbound_email.sender_email or "Unknown Dealer")
        )
        offer.source_type = "email"
        offer.currency = pricing.get("currency") or "EUR"
        offer.raw_response = text.strip() or "(empty email)"
        offer.vehicle_price = pricing.get("vehicle_price")
        offer.transfer_cost = pricing.get("transfer_cost")
        offer.registration_cost = pricing.get("registration_cost")
        offer.total_price = pricing.get("total_cash_price") or pricing.get("vehicle_price") or pricing.get("monthly_rate")
        offer.cash_price = pricing.get("total_cash_price")
        offer.financing_total_cost = pricing.get("total_financing_cost")
        offer.offer_valid_until = None
        offer.gross_final_price = pricing.get("total_cash_price") or pricing.get("vehicle_price")
        offer.list_price = pricing.get("list_price")
        offer.discount_amount = pricing.get("discount_amount")
        offer.discount_percent = pricing.get("discount_percent")
        offer.delivery_cost = pricing.get("transfer_cost")
        offer.other_costs = pricing.get("additional_costs")
        offer.valid_until = None
        offer.price_confidence = analysis["confidence"]
        offer.extraction_status = analysis["processing_result"]
        offer.missing_fields = analysis["missing_fields"]
        offer.extraction_notes = analysis["reason"]
        offer.raw_extraction = self._serialize_json_value(analysis)
        offer.extracted_at = datetime.now(UTC)
        campaign = self.campaign_repository.get(inbound_email.campaign_id) if inbound_email.campaign_id is not None else None
        offer.features = self._extract_offer_features(campaign, text)
        if existing_offer is None:
            self.offer_repository.add(offer)
        return offer

    def _build_extraction_response(
        self,
        inbound_email: InboundEmail,
        analysis: dict,
        offer_record: DealerOffer | None,
    ) -> InboundOfferExtractionResponse:
        offer_payload = self._serialize_json_value(analysis["offer"])
        price_comparison = self._build_price_comparison(inbound_email, offer_record)
        if offer_payload is not None:
            offer_payload["configuration"] = self._build_offer_configuration(inbound_email, offer_record)
            offer_payload["price_comparison"] = price_comparison

        return InboundOfferExtractionResponse(
            inbound_email_id=inbound_email.id,
            processing_result=analysis["processing_result"],
            message_type=analysis["message_type"],
            confidence=analysis["confidence"],
            offer=offer_payload,
            price_comparison=price_comparison,
            reason=analysis["reason"],
            status=analysis["processing_result"],
            gross_final_price=analysis["gross_final_price"],
            currency=analysis["currency"],
            price_confidence=analysis["price_confidence"],
            needs_review=analysis["needs_review"],
            review_reason=analysis["review_reason"],
            dealer_offer_id=offer_record.id if offer_record is not None else None,
        )

    def _deserialize_analysis(self, value: dict) -> dict:
        return {
            "processing_result": value["processing_result"],
            "message_type": value["message_type"],
            "status": value["status"],
            "currency": value.get("currency"),
            "gross_final_price": self._deserialize_decimal(value.get("gross_final_price")),
            "list_price": self._deserialize_decimal(value.get("list_price")),
            "discount_amount": self._deserialize_decimal(value.get("discount_amount")),
            "discount_percent": self._deserialize_decimal(value.get("discount_percent")),
            "delivery_cost": self._deserialize_decimal(value.get("delivery_cost")),
            "registration_cost": self._deserialize_decimal(value.get("registration_cost")),
            "other_costs": self._deserialize_decimal(value.get("other_costs")),
            "delivery_time_text": value.get("delivery_time_text"),
            "valid_until": value.get("valid_until"),
            "price_confidence": self._deserialize_decimal(value.get("price_confidence")),
            "confidence": self._deserialize_decimal(value.get("confidence")) or Decimal("0"),
            "offer": self._deserialize_nested_decimals(value.get("offer")),
            "missing_fields": value.get("missing_fields", []),
            "needs_review": value.get("needs_review", False),
            "review_reason": value.get("review_reason"),
            "reason": value.get("reason"),
            "raw": self._deserialize_nested_decimals(value.get("raw", {})),
        }

    @staticmethod
    def _deserialize_nested_decimals(value):
        if isinstance(value, str):
            try:
                return Decimal(value)
            except Exception:
                return value
        if isinstance(value, dict):
            return {key: CampaignContactService._deserialize_nested_decimals(item) for key, item in value.items()}
        if isinstance(value, list):
            return [CampaignContactService._deserialize_nested_decimals(item) for item in value]
        return value

    @staticmethod
    def _deserialize_decimal(value) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _serialize_json_value(value):
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {key: CampaignContactService._serialize_json_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [CampaignContactService._serialize_json_value(item) for item in value]
        return value

    def _build_offer_configuration(
        self,
        inbound_email: InboundEmail,
        offer_record: DealerOffer | None,
    ) -> dict | None:
        campaign = self.campaign_repository.get(inbound_email.campaign_id) if inbound_email.campaign_id is not None else None
        configuration = getattr(campaign, "configuration", None)
        extracted = self._extract_actual_offer_values(offer_record.raw_response if offer_record is not None else "")

        requested = None
        if configuration is not None:
            requested = {
                "model": configuration.model,
                "variant": configuration.variant,
                "configuration_url": configuration.configuration_url,
                "requirements": [
                    {
                        "feature_key": requirement.feature_key,
                        "feature_value": requirement.feature_value,
                        "display_label": requirement.display_label,
                        "is_mandatory": requirement.is_mandatory,
                    }
                    for requirement in configuration.requirements
                ],
            }

        extracted_payload = extracted or None
        if requested is None and extracted_payload is None:
            return None
        return {
            "requested": requested,
            "extracted": extracted_payload,
        }

    def _build_price_comparison(
        self,
        inbound_email: InboundEmail,
        offer_record: DealerOffer | None,
    ) -> dict | None:
        if inbound_email.campaign_id is None or offer_record is None or offer_record.total_price is None:
            return None

        offers = [
            item
            for item in self.offer_repository.list_by_campaign(inbound_email.campaign_id)
            if item.total_price is not None
        ]
        if not offers:
            return None

        current_price = offer_record.total_price
        previous_prices = [item.total_price for item in offers if item.id != offer_record.id and item.total_price is not None]
        previous_lowest_price = min(previous_prices) if previous_prices else None
        lowest_overall_price = min(item.total_price for item in offers if item.total_price is not None)
        tied_lowest_count = sum(1 for item in offers if item.total_price == lowest_overall_price)

        return {
            "current_offer_price": current_price,
            "previous_lowest_price": previous_lowest_price,
            "lowest_price_in_campaign": lowest_overall_price,
            "has_previous_offers": bool(previous_prices),
            "matches_or_beats_previous_lowest": (
                None if previous_lowest_price is None else current_price <= previous_lowest_price
            ),
            "lower_than_previous_lowest": (
                previous_lowest_price is not None and current_price < previous_lowest_price
            ),
            "equal_to_previous_lowest": (
                previous_lowest_price is not None and current_price == previous_lowest_price
            ),
            "is_lowest_overall": current_price == lowest_overall_price,
            "is_tied_lowest_overall": current_price == lowest_overall_price and tied_lowest_count > 1,
        }

    def _extract_offer_features(self, campaign, text: str) -> list[DealerOfferFeature]:
        if campaign is None or campaign.configuration is None:
            return []

        normalized_text = self.feature_normalizer.normalize_value(text) or ""
        actual_values = self._extract_actual_offer_values(text)
        features: list[DealerOfferFeature] = []
        seen_keys: set[str] = set()

        for requirement in campaign.configuration.requirements:
            actual_value = self._resolve_offer_feature_value(requirement, normalized_text, actual_values)
            if actual_value is None:
                continue
            normalized_key, normalized_value = self.feature_normalizer.normalize_feature(
                requirement.feature_key,
                actual_value,
            )
            if normalized_key in seen_keys:
                continue
            seen_keys.add(normalized_key)
            features.append(
                DealerOfferFeature(
                    feature_key=requirement.feature_key,
                    feature_value=actual_value,
                    normalized_key=normalized_key,
                    normalized_value=normalized_value,
                    display_label=requirement.display_label,
                    is_available=True,
                )
            )
        return features

    def _resolve_offer_feature_value(self, requirement, normalized_text: str, actual_values: dict[str, str | None]) -> str | None:
        expected_value = requirement.feature_value.strip() if requirement.feature_value else None
        expected_normalized = requirement.normalized_value or self.feature_normalizer.normalize_value(expected_value)
        if expected_normalized and expected_normalized in normalized_text:
            return expected_value

        key_blob = self.feature_normalizer.normalize_key(
            f"{requirement.feature_key} {(requirement.display_label or '')}"
        )
        if any(token in key_blob for token in ["variant", "drive", "antrieb"]):
            return actual_values.get("variant")
        if any(token in key_blob for token in ["karosserie", "body"]):
            return actual_values.get("body")
        if "modellcode" in key_blob or key_blob.endswith("_code"):
            return actual_values.get("model_code")
        if "modell" in key_blob or "model" in key_blob:
            return actual_values.get("model_name")
        return None

    @staticmethod
    def _extract_actual_offer_values(text: str) -> dict[str, str | None]:
        match = re.search(
            r"(?im)^\s*(?:BMW\s+)?(?P<series>i5)\s+(?P<variant>eDrive40|xDrive40)\s+(?P<body>Touring)\s*(?:\((?P<code>[A-Z0-9]+)[^)]*\))?",
            text,
        )
        if match is None:
            return {}
        series = match.group("series")
        variant = match.group("variant")
        body = match.group("body")
        return {
            "model_name": f"BMW {series} {variant} {body}",
            "variant": variant,
            "body": body,
            "model_code": match.group("code"),
        }

    @staticmethod
    def _format_configuration_items(campaign) -> list[str]:
        configuration = getattr(campaign, "configuration", None)
        if configuration is None:
            return []
        items: list[str] = []
        for requirement in configuration.requirements:
            label = (requirement.display_label or requirement.feature_key).strip()
            if requirement.feature_value:
                items.append(f"{label}: {requirement.feature_value.strip()}")
            else:
                items.append(label)
        return items

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
            excerpt_start = max(0, match.start() - 80)
            excerpt_end = min(len(text), match.end() + 80)
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
                    "excerpt": text[excerpt_start:excerpt_end],
                }
            )
        results.sort(key=lambda item: (item["context"] == "lease", item["label"] != "final", item["value"]))
        return results
