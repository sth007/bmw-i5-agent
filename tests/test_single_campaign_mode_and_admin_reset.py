from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.config import settings
from app.entities.campaign import Campaign
from app.entities.campaign_dealer_contact import CampaignDealerContact
from app.entities.dealer import Dealer
from app.entities.inbound_email import InboundEmail


def _reset_headers() -> dict[str, str]:
    return {"X-Reset-Token": settings.test_reset_token}


def _import_dealers(client, dealers: list[dict]) -> None:
    response = client.post("/dealers/import", json=dealers)
    assert response.status_code == 200


def _create_campaign(client, name: str) -> str:
    response = client.post(
        "/api/campaigns/from-config",
        json={
            "campaign_name": name,
            "config_url": "https://configure.bmw.de/de_DE/configid/chtwyiio",
            "dealer_limit": 3,
            "customer": {
                "name": "Max Mustermann",
                "email": "max.mustermann@example.de",
            },
        },
    )
    assert response.status_code == 201
    return response.json()["campaign_id"]


def _claim_and_mark_sent(client, campaign_id: str, suffix: str) -> dict:
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": f"n8n-{suffix}", "test_mode": False},
    )
    assert claim.status_code == 200
    contact = claim.json()["contacts"][0]
    sent = client.post(
        f"/api/campaign-contacts/{contact['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": f"gmail-message-{suffix}",
            "provider_thread_id": f"gmail-thread-{suffix}",
            "internet_message_id": f"<message-{suffix}@example.test>",
            "sent_to": contact["effective_to"],
            "test_mode": False,
        },
    )
    assert sent.status_code == 200
    return contact


def test_new_campaign_deletes_old_campaign_and_dependent_data_but_keeps_dealers(client, db_session) -> None:
    _import_dealers(
        client,
        [
            {
                "bmw_dealer_id": "bmw-single-001",
                "name": "BMW Single 1",
                "city": "Stuttgart",
                "email": "single1@bmw.de",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-single-002",
                "name": "BMW Single 2",
                "city": "Muenchen",
                "email": "single2@bmw.de",
                "is_published": True,
            },
        ],
    )
    first_campaign_id = _create_campaign(client, "First Campaign")
    first_contact = _claim_and_mark_sent(client, first_campaign_id, "first")

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "single-first-inbound",
            "provider_thread_id": "gmail-thread-first",
            "internet_message_id": "<single-first-inbound@example.test>",
            "sender_email": "single1@bmw.de",
            "subject": first_contact["subject"],
            "text_body": "Endpreis 71.490,00 EUR",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201

    second_campaign_id = _create_campaign(client, "Second Campaign")
    assert second_campaign_id != first_campaign_id

    assert db_session.scalar(select(func.count()).select_from(Campaign)) == 1
    assert db_session.scalar(select(func.count()).select_from(CampaignDealerContact)) == 0
    assert db_session.scalar(select(func.count()).select_from(InboundEmail)) == 0
    assert db_session.scalar(select(func.count()).select_from(Dealer)) == 2

    campaigns = client.get("/campaigns")
    assert campaigns.status_code == 200
    payload = campaigns.json()
    assert len(payload) == 1
    assert payload[0]["id"] == second_campaign_id


def test_reset_status_requires_valid_token_in_development(client) -> None:
    response = client.get("/api/admin/reset-status")
    assert response.status_code == 403

    response = client.get("/api/admin/reset-status", headers={"X-Reset-Token": "wrong"})
    assert response.status_code == 403


def test_reset_endpoints_are_hidden_in_production(client, monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    response = client.get("/api/admin/reset-status", headers=_reset_headers())
    assert response.status_code == 404

    response = client.post(
        "/api/admin/reset-test-state",
        headers=_reset_headers(),
        json={"scope": "campaign_data"},
    )
    assert response.status_code == 404


def test_reset_status_returns_counts(client) -> None:
    _import_dealers(
        client,
        [
            {
                "bmw_dealer_id": "bmw-status-001",
                "name": "BMW Status 1",
                "city": "Stuttgart",
                "email": "status1@bmw.de",
                "is_published": True,
            }
        ],
    )
    _create_campaign(client, "Status Campaign")

    response = client.get("/api/admin/reset-status", headers=_reset_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["environment"] == "development"
    assert payload["reset_enabled"] is True
    assert payload["campaign_count"] == 1
    assert payload["dealer_count"] == 1


def test_campaign_data_reset_keeps_dealers(client, db_session) -> None:
    _import_dealers(
        client,
        [
            {
                "bmw_dealer_id": "bmw-reset-001",
                "name": "BMW Reset 1",
                "city": "Stuttgart",
                "email": "reset1@bmw.de",
                "is_published": True,
            }
        ],
    )
    campaign_id = _create_campaign(client, "Reset Campaign")
    _claim_and_mark_sent(client, campaign_id, "reset")

    response = client.post(
        "/api/admin/reset-test-state",
        headers=_reset_headers(),
        json={"scope": "campaign_data"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "RESET_COMPLETED"
    assert payload["scope"] == "campaign_data"
    assert payload["deleted"]["campaigns"] == 1
    assert db_session.scalar(select(func.count()).select_from(Campaign)) == 0
    assert db_session.scalar(select(func.count()).select_from(Dealer)) == 1


def test_all_application_data_reset_requires_confirm(client) -> None:
    response = client.post(
        "/api/admin/reset-test-state",
        headers=_reset_headers(),
        json={"scope": "all_application_data"},
    )
    assert response.status_code == 400


def test_all_application_data_reset_deletes_dealers(client, db_session) -> None:
    _import_dealers(
        client,
        [
            {
                "bmw_dealer_id": "bmw-reset-all-001",
                "name": "BMW Reset All 1",
                "city": "Stuttgart",
                "email": "resetall1@bmw.de",
                "is_published": True,
            }
        ],
    )
    response = client.post(
        "/api/admin/reset-test-state",
        headers=_reset_headers(),
        json={"scope": "all_application_data", "confirm": "RESET"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["deleted"]["dealers"] == 1
    assert db_session.scalar(select(func.count()).select_from(Dealer)) == 0
