from datetime import UTC, datetime


def _import_dealers(client, count: int) -> None:
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": f"bmw-dispatch-{index:03d}",
                "name": f"BMW Händler {index:03d}",
                "city": f"Stadt {index:03d}",
                "email": f"dealer{index:03d}@bmw.example",
                "is_published": True,
            }
            for index in range(1, count + 1)
        ],
    )
    assert response.status_code == 200


def _create_campaign(client, name: str = "BMW Dispatch Kampagne") -> str:
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


def _claim_contact(client, campaign_id: str, limit: int = 1, owner: str = "n8n-1") -> dict:
    response = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": limit, "reservation_owner": owner, "test_mode": False},
    )
    assert response.status_code == 200
    return response.json()


def _mark_sent(client, contact: dict, suffix: str) -> None:
    response = client.post(
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
    assert response.status_code == 200


def test_dispatch_status_counts_and_batch_claims(client) -> None:
    _import_dealers(client, 159)
    campaign_id = _create_campaign(client, "BMW Batch Juli 2026")

    batch_sizes = []
    for index in range(1, 10):
        claim = _claim_contact(client, campaign_id, limit=30, owner=f"n8n-{index}")
        contact_count = len(claim["contacts"])
        if contact_count == 0:
            break
        batch_sizes.append(contact_count)

    assert batch_sizes == [30, 30, 30, 30, 30, 9]

    status_response = client.get(f"/api/campaigns/{campaign_id}/dispatch-status")
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["campaign_status"] == "STARTED"
    assert payload["total_contacts"] == 159
    assert payload["pending"] == 0
    assert payload["reserved"] == 159
    assert payload["has_more_sendable_contacts"] is False
    assert payload["can_complete"] is False


def test_campaign_with_pending_contacts_cannot_be_completed(client) -> None:
    _import_dealers(client, 1)
    campaign_id = _create_campaign(client)

    response = client.post(f"/api/campaigns/{campaign_id}/complete", json={"completed_by": "n8n"})
    assert response.status_code == 409
    assert response.json()["remaining_sendable_contacts"] == 1


def test_campaign_with_reserved_contacts_cannot_be_completed(client) -> None:
    _import_dealers(client, 1)
    campaign_id = _create_campaign(client)
    _claim_contact(client, campaign_id, limit=1)

    response = client.post(f"/api/campaigns/{campaign_id}/complete", json={"completed_by": "n8n"})
    assert response.status_code == 409
    assert response.json()["remaining_reserved_contacts"] == 1


def test_campaign_with_send_failed_contacts_cannot_be_completed(client) -> None:
    _import_dealers(client, 1)
    campaign_id = _create_campaign(client)
    claim = _claim_contact(client, campaign_id, limit=1)["contacts"][0]
    client.post(
        f"/api/campaign-contacts/{claim['contact_id']}/send-failed",
        json={"error_message": "SMTP failed", "unknown_state": False},
    )

    response = client.post(f"/api/campaigns/{campaign_id}/complete", json={"completed_by": "n8n"})
    assert response.status_code == 409
    assert response.json()["remaining_failed_contacts"] == 1


def test_campaign_with_send_state_unknown_contacts_cannot_be_completed(client) -> None:
    _import_dealers(client, 1)
    campaign_id = _create_campaign(client)
    claim = _claim_contact(client, campaign_id, limit=1)["contacts"][0]
    client.post(
        f"/api/campaign-contacts/{claim['contact_id']}/send-failed",
        json={"error_message": "Unknown state", "unknown_state": True},
    )

    response = client.post(f"/api/campaigns/{campaign_id}/complete", json={"completed_by": "n8n"})
    assert response.status_code == 409
    assert response.json()["remaining_failed_contacts"] == 1


def test_complete_campaign_is_idempotent_and_sets_completed_at_once(client) -> None:
    _import_dealers(client, 1)
    campaign_id = _create_campaign(client)
    contact = _claim_contact(client, campaign_id, limit=1)["contacts"][0]
    _mark_sent(client, contact, "complete")

    first = client.post(
        f"/api/campaigns/{campaign_id}/complete",
        json={"completed_by": "n8n", "n8n_execution_id": "12345"},
    )
    second = client.post(
        f"/api/campaigns/{campaign_id}/complete",
        json={"completed_by": "n8n", "n8n_execution_id": "99999"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "COMPLETED"
    assert datetime.fromisoformat(first.json()["completed_at"].replace("Z", "+00:00")) == datetime.fromisoformat(
        second.json()["completed_at"].replace("Z", "+00:00")
    )


def test_latest_relevant_campaign_ignores_draft_and_returns_latest_started_or_completed(client) -> None:
    _import_dealers(client, 1)
    started_campaign_id = _create_campaign(client, "Started Campaign")
    started_contact = _claim_contact(client, started_campaign_id, limit=1)["contacts"][0]
    _mark_sent(client, started_contact, "latest-started")

    draft_campaign_id = _create_campaign(client, "Draft Campaign")
    assert draft_campaign_id != started_campaign_id

    latest = client.get("/api/campaigns/latest-relevant")
    assert latest.status_code == 404


def test_latest_relevant_campaign_returns_single_completed_campaign(client) -> None:
    _import_dealers(client, 1)
    campaign_id = _create_campaign(client, "Completed Campaign")
    contact = _claim_contact(client, campaign_id, limit=1)["contacts"][0]
    _mark_sent(client, contact, "latest-completed")

    complete = client.post(
        f"/api/campaigns/{campaign_id}/complete",
        json={"completed_by": "n8n", "n8n_execution_id": "single-completed"},
    )
    assert complete.status_code == 200

    latest = client.get("/api/campaigns/latest-relevant")
    assert latest.status_code == 200
    assert latest.json()["campaign_id"] == campaign_id


def test_inbound_email_matches_completed_campaign_with_hint(client) -> None:
    _import_dealers(client, 1)
    campaign_id = _create_campaign(client, "Completed Campaign")
    contact = _claim_contact(client, campaign_id, limit=1)["contacts"][0]
    _mark_sent(client, contact, "completed-hint")
    complete = client.post(
        f"/api/campaigns/{campaign_id}/complete",
        json={"completed_by": "n8n", "n8n_execution_id": "321"},
    )
    assert complete.status_code == 200

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "campaign_id_hint": campaign_id,
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-completed-hint",
            "provider_thread_id": "gmail-thread-completed-hint",
            "internet_message_id": "<inbound-completed-hint@example.test>",
            "sender_email": "dealer001@bmw.example",
            "subject": contact["subject"],
            "text_body": "Endpreis 71.990,00 EUR",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    assert inbound.json()["campaign_id"] == campaign_id
    assert inbound.json()["matching_status"] == "MATCHED_BY_THREAD"


def test_inbound_email_with_known_campaign_but_unknown_dealer_needs_assignment(client) -> None:
    _import_dealers(client, 1)
    campaign_id = _create_campaign(client, "Known Campaign Unknown Dealer")
    contact = _claim_contact(client, campaign_id, limit=1)["contacts"][0]
    _mark_sent(client, contact, "needs-assignment")

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "campaign_id_hint": campaign_id,
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-needs-assignment",
            "provider_thread_id": "different-thread",
            "internet_message_id": "<inbound-needs-assignment@example.test>",
            "sender_email": "unknown@bmw.example",
            "subject": "Rueckmeldung ohne Match",
            "text_body": "Bitte melden Sie sich.",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    payload = inbound.json()
    assert payload["campaign_id"] == campaign_id
    assert payload["dealer_id"] is None
    assert payload["campaign_dealer_contact_id"] is None
    assert payload["matching_status"] == "NEEDS_DEALER_ASSIGNMENT"
    assert payload["processing_status"] == "NEEDS_REVIEW"


def test_inbound_email_without_hint_uses_single_started_campaign(client) -> None:
    _import_dealers(client, 1)
    campaign_id = _create_campaign(client, "Started Without Hint")
    contact = _claim_contact(client, campaign_id, limit=1)["contacts"][0]
    _mark_sent(client, contact, "started-no-hint")

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-started-no-hint",
            "provider_thread_id": "gmail-thread-started-no-hint",
            "internet_message_id": "<inbound-started-no-hint@example.test>",
            "sender_email": "dealer001@bmw.example",
            "subject": contact["subject"],
            "text_body": "Endpreis 70.490,00 EUR",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    payload = inbound.json()
    assert payload["campaign_id"] == campaign_id
    assert payload["matching_status"] == "MATCHED_BY_THREAD"
    assert payload["can_extract"] is True


def test_inbound_email_without_hint_uses_single_completed_campaign(client) -> None:
    _import_dealers(client, 1)
    campaign_id = _create_campaign(client, "Completed Without Hint")
    contact = _claim_contact(client, campaign_id, limit=1)["contacts"][0]
    _mark_sent(client, contact, "completed-no-hint")
    complete = client.post(
        f"/api/campaigns/{campaign_id}/complete",
        json={"completed_by": "n8n", "n8n_execution_id": "completed-no-hint"},
    )
    assert complete.status_code == 200

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-completed-no-hint",
            "provider_thread_id": "gmail-thread-completed-no-hint",
            "internet_message_id": "<inbound-completed-no-hint@example.test>",
            "sender_email": "dealer001@bmw.example",
            "subject": contact["subject"],
            "text_body": "Endpreis 70.990,00 EUR",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    payload = inbound.json()
    assert payload["campaign_id"] == campaign_id
    assert payload["matching_status"] == "MATCHED_BY_THREAD"
    assert payload["can_extract"] is True
