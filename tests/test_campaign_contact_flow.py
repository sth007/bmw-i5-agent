from datetime import UTC, datetime


def _create_campaign(client):
    response = client.post(
        "/api/campaigns/from-config",
        json={
            "campaign_name": "BMW i5 Kontaktkampagne",
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


def _import_dealers(client):
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-contact-001",
                "name": "BMW AG Niederlassung Stuttgart",
                "city": "Stuttgart",
                "email": "stuttgart@bmw.de",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-contact-002",
                "name": "BMW AG Niederlassung Muenchen",
                "city": "Muenchen",
                "email": "muenchen@bmw.de",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-contact-003",
                "name": "BMW AG Niederlassung Hamburg",
                "city": "Hamburg",
                "email": "hamburg@bmw.de",
                "is_published": True,
            },
        ],
    )
    assert response.status_code == 200


def _mark_contact_sent(client, contact: dict, suffix: str) -> None:
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


def test_contact_claim_returns_each_dealer_only_once(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)

    first_claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={
            "limit": 2,
            "reservation_owner": "n8n-exec-1",
            "test_mode": True,
            "test_recipient": "qa@example.org",
        },
    )
    assert first_claim.status_code == 200
    first_contacts = first_claim.json()["contacts"]
    assert len(first_contacts) == 2
    assert all(item["effective_to"] == "qa@example.org" for item in first_contacts)

    second_claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={
            "limit": 3,
            "reservation_owner": "n8n-exec-2",
            "test_mode": False,
        },
    )
    assert second_claim.status_code == 200
    second_contacts = second_claim.json()["contacts"]
    assert len(second_contacts) == 1
    assert second_contacts[0]["dealer_id"] not in {item["dealer_id"] for item in first_contacts}


def test_mark_sent_is_idempotent(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]

    payload = {
        "provider": "gmail",
        "provider_message_id": "gmail-message-1",
        "provider_thread_id": "gmail-thread-1",
        "internet_message_id": "<message-1@example.test>",
        "sent_to": claim["effective_to"],
        "test_mode": False,
        "n8n_execution_id": "n8n-1",
    }
    first = client.post(f"/api/campaign-contacts/{claim['contact_id']}/sent", json=payload)
    second = client.post(f"/api/campaign-contacts/{claim['contact_id']}/sent", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["provider_message_id"] == "gmail-message-1"
    assert second.json()["provider_message_id"] == "gmail-message-1"
    assert second.json()["status"] == "SENT"


def test_register_inbound_email_is_idempotent(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    client.post(
        f"/api/campaign-contacts/{claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-idem",
            "provider_thread_id": "gmail-thread-idem",
            "internet_message_id": "<message-idem@example.test>",
            "sent_to": claim["effective_to"],
            "test_mode": False,
        },
    )

    payload = {
        "mailbox_address": "zaour.ludwigsburger@gmail.com",
        "provider": "gmail",
        "provider_message_id": "inbound-idempotent",
        "provider_thread_id": "gmail-thread-idem",
        "internet_message_id": "<inbound-idempotent@example.test>",
        "sender_email": "stuttgart@bmw.de",
        "subject": claim["subject"],
        "text_body": "Endpreis 74.990,00 EUR",
        "received_at": datetime.now(UTC).isoformat(),
        "raw_metadata": {},
    }
    first = client.post("/api/inbound-emails", json=payload)
    second = client.post("/api/inbound-emails", json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_register_inbound_email_matches_by_thread_and_extracts_price(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    client.post(
        f"/api/campaign-contacts/{claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-1",
            "provider_thread_id": "gmail-thread-1",
            "internet_message_id": "<message-1@example.test>",
            "sent_to": claim["effective_to"],
            "test_mode": False,
        },
    )

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-1",
            "provider_thread_id": "gmail-thread-1",
            "internet_message_id": "Message-ID: <inbound-1@example.test>",
            "sender_email": "stuttgart@bmw.de",
            "subject": f"Subject: {claim['subject']}",
            "text_body": "Endpreis 74.990,00 EUR\nListenpreis 79.990,00 EUR",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    inbound_payload = inbound.json()
    assert inbound_payload["matching_status"] == "MATCHED_BY_THREAD"
    assert inbound_payload["subject"] == claim["subject"]
    assert inbound_payload["internet_message_id"] == "<inbound-1@example.test>"

    extraction = client.post(
        f"/api/inbound-emails/{inbound_payload['id']}/extract-offer",
        json={"attachment_text": []},
    )
    assert extraction.status_code == 200
    body = extraction.json()
    assert body["status"] == "PRICE_EXTRACTED"
    assert body["gross_final_price"] == "74990.00"
    assert body["needs_review"] is False


def test_register_inbound_email_matches_by_in_reply_to(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    client.post(
        f"/api/campaign-contacts/{claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-reference",
            "provider_thread_id": "gmail-thread-reference",
            "internet_message_id": "Message-ID: <message-reference@example.test>",
            "sent_to": claim["effective_to"],
            "test_mode": False,
        },
    )

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-reference",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-reference@example.test>",
            "in_reply_to": "In-Reply-To: <message-reference@example.test>",
            "sender_email": "stuttgart@bmw.de",
            "subject": f"Re: {claim['subject']}",
            "text_body": "Endpreis 73.990,00 EUR",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )

    assert inbound.status_code == 201
    payload = inbound.json()
    assert payload["matching_status"] == "MATCHED_BY_REFERENCE"
    assert payload["campaign_id"] == campaign_id
    assert payload["subject"] == f"Re: {claim['subject']}"


def test_register_inbound_email_matches_by_campaign_token(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    client.post(
        f"/api/campaign-contacts/{claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-token",
            "provider_thread_id": "gmail-thread-token",
            "internet_message_id": "<message-token@example.test>",
            "sent_to": claim["effective_to"],
            "test_mode": False,
        },
    )

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-token",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-token@example.test>",
            "sender_email": "stuttgart@bmw.de",
            "subject": claim["subject"],
            "text_body": "Wir koennen Ihnen einen Endpreis von 75.990,00 EUR anbieten.",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )

    assert inbound.status_code == 201
    assert inbound.json()["matching_status"] == "MATCHED_BY_CAMPAIGN_TOKEN"


def test_register_inbound_email_unmatched_without_known_sender_or_token(client) -> None:
    _import_dealers(client)

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-unmatched",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-unmatched@example.test>",
            "sender_email": "unknown@bmw.de",
            "subject": "Allgemeine Rueckmeldung",
            "text_body": "Bitte melden Sie sich.",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )

    assert inbound.status_code == 201
    assert inbound.json()["matching_status"] == "NO_CAMPAIGN"
    assert inbound.json()["processing_status"] == "NEEDS_REVIEW"


def test_register_inbound_email_parses_sender_header(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    client.post(
        f"/api/campaign-contacts/{claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-from",
            "provider_thread_id": "gmail-thread-from",
            "internet_message_id": "<message-from@example.test>",
            "sent_to": claim["effective_to"],
            "test_mode": False,
        },
    )

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-from",
            "provider_thread_id": "gmail-thread-from",
            "internet_message_id": "<inbound-from@example.test>",
            "sender_email": "BMW Stuttgart <stuttgart@bmw.de>",
            "subject": claim["subject"],
            "text_body": "Endpreis 72.990,00 EUR",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    assert inbound.json()["sender_email"] == "stuttgart@bmw.de"


def test_register_inbound_email_matches_by_references_header(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    client.post(
        f"/api/campaign-contacts/{claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-refs",
            "provider_thread_id": "gmail-thread-refs",
            "internet_message_id": "<message-refs@example.test>",
            "sent_to": claim["effective_to"],
            "test_mode": False,
        },
    )

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-refs",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-refs@example.test>",
            "references": "References: <foo@example.test> <message-refs@example.test>",
            "sender_email": "stuttgart@bmw.de",
            "subject": f"Re: {claim['subject']}",
            "text_body": "Endpreis 72.500,00 EUR",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    assert inbound.json()["matching_status"] == "MATCHED_BY_REFERENCE"


def test_register_inbound_email_matches_forwarded_mail_via_signature_email(client) -> None:
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-forward-001",
                "name": "BMW Stuttgart Filiale Rosensteinpark",
                "street": "Pragstraße 140",
                "postal_code": "70376",
                "city": "Stuttgart",
                "email": "linus.hermann@bmw.de",
                "phone": "+49-711-1318-5312",
                "is_published": True,
            }
        ],
    )
    assert response.status_code == 200
    campaign_id = _create_campaign(client)
    contact = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    _mark_contact_sent(client, contact, "forward-signature")

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "campaign_id_hint": campaign_id,
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-forward-signature",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-forward-signature@example.test>",
            "sender_raw": "From: Zaour Assadov <zaour@assadov.de>",
            "sender_email": "zaour@assadov.de",
            "subject": "WG: Interesse BMW i5",
            "text_body": (
                "Hallo Herr Assadov,\n"
                "guenstiger ist diese Option leider nicht.\n\n"
                "Mit freundlichen Gruessen\n"
                "Linus Hermann\n"
                "BMW Stuttgart\n"
                "Filiale Rosensteinpark\n"
                "Pragstraße 140\n"
                "70376 Stuttgart\n"
                "Tel.: +49-711-1318-5312\n"
                "Mail: Linus.Hermann@bmw.de\n"
            ),
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    payload = inbound.json()
    assert payload["campaign_id"] == campaign_id
    assert payload["dealer_id"] is not None
    assert payload["campaign_dealer_contact_id"] == contact["contact_id"]
    assert payload["matching_status"] == "MATCHED"
    assert payload["can_extract"] is True

    debug = client.get(f"/api/inbound-emails/{payload['id']}/debug-match")
    assert debug.status_code == 200
    debug_payload = debug.json()
    assert debug_payload["matching_method"] == "content_email"
    assert debug_payload["matching_score"] >= 70
    assert any("email matched" in reason.lower() for reason in debug_payload["matching_reasons"])


def test_register_inbound_email_matches_by_company_and_address_without_email(client) -> None:
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-address-001",
                "name": "Autohaus Beispiel Stuttgart GmbH",
                "street": "Pragstraße 140",
                "postal_code": "70376",
                "city": "Stuttgart",
                "email": "stuttgart-verkauf@example.de",
                "is_published": True,
            }
        ],
    )
    assert response.status_code == 200
    campaign_id = _create_campaign(client)
    contact = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    _mark_contact_sent(client, contact, "address-only")

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "campaign_id_hint": campaign_id,
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-address-only",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-address-only@example.test>",
            "sender_email": "zaour@assadov.de",
            "subject": "Rueckmeldung",
            "text_body": (
                "Autohaus Beispiel Stuttgart\n"
                "Pragstraße 140\n"
                "70376 Stuttgart\n"
                "Bitte melden Sie sich wegen des Angebots.\n"
            ),
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    payload = inbound.json()
    assert payload["campaign_dealer_contact_id"] == contact["contact_id"]
    assert payload["matching_status"] == "MATCHED"
    assert payload["can_extract"] is True


def test_register_inbound_email_does_not_match_on_generic_bmw_signals_only(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)
    contacts = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 3, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"]
    for index, contact in enumerate(contacts, start=1):
        _mark_contact_sent(client, contact, f"generic-{index}")

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "campaign_id_hint": campaign_id,
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-generic-bmw",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-generic-bmw@example.test>",
            "sender_email": "zaour@assadov.de",
            "subject": "Rueckmeldung",
            "text_body": "BMW\nKontaktieren Sie uns bitte unter kontakt@bmw.de.",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    assert inbound.json()["matching_status"] == "NEEDS_DEALER_ASSIGNMENT"
    assert inbound.json()["can_extract"] is False


def test_register_inbound_email_ignores_mailbox_address_in_history(client) -> None:
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-ignore-001",
                "name": "BMW Hamburg",
                "city": "Hamburg",
                "email": "hamburg@bmw.de",
                "is_published": True,
            }
        ],
    )
    assert response.status_code == 200
    campaign_id = _create_campaign(client)
    contact = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    _mark_contact_sent(client, contact, "ignore-mailbox")

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "campaign_id_hint": campaign_id,
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-ignore-mailbox",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-ignore-mailbox@example.test>",
            "sender_email": "zaour@assadov.de",
            "subject": "Rueckmeldung",
            "text_body": (
                "Von: zaour.ludwigsburger@gmail.com\n"
                "An: zaour.ludwigsburger@gmail.com\n"
                "Bitte antworten Sie an hamburg@bmw.de\n"
            ),
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    assert inbound.json()["campaign_dealer_contact_id"] == contact["contact_id"]
    assert inbound.json()["matching_status"] == "MATCHED"


def test_register_inbound_email_matches_dealer_from_database_without_prior_contact(client) -> None:
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-known-001",
                "name": "BMW Hamburg",
                "city": "Hamburg",
                "email": "hamburg@bmw.de",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-known-002",
                "name": "BMW Stuttgart Filiale Rosensteinpark",
                "street": "Pragstraße 140",
                "postal_code": "70376",
                "city": "Stuttgart",
                "email": None,
                "new_car_email": "linus.hermann@bmw.de",
                "phone": "+49 711 1318 5312",
                "is_published": False,
            },
        ],
    )
    assert response.status_code == 200

    campaign_id = _create_campaign(client)
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    _mark_contact_sent(client, claim, "known-db-only")

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "campaign_id_hint": campaign_id,
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-db-only-dealer",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-db-only-dealer@example.test>",
            "sender_email": "zaour@assadov.de",
            "subject": "Rueckmeldung",
            "text_body": (
                "Hallo Herr Assadov,\n\n"
                "Mit freundlichen Gruessen\n"
                "Linus Hermann\n"
                "BMW Stuttgart\n"
                "Filiale Rosensteinpark\n"
                "Pragstraße 140\n"
                "70376 Stuttgart\n"
                "Tel.: +49 711 1318 5312\n"
                "Mail: Linus.Hermann@bmw.de\n"
            ),
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )

    assert inbound.status_code == 201
    payload = inbound.json()
    assert payload["campaign_id"] == str(campaign_id)
    assert payload["dealer_id"] is not None
    assert payload["campaign_dealer_contact_id"] is not None
    assert payload["matching_status"] == "MATCHED_BY_DEALER_DB"
    assert payload["can_extract"] is True


def test_register_inbound_email_matches_dealer_from_homepage_and_signature_cluster(client) -> None:
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-homepage-001",
                "name": "BMW AG Niederlassung Stuttgart Filiale Rosensteinpark",
                "street": "Pragstr. 140",
                "postal_code": "70376",
                "city": "Stuttgart",
                "homepage": "http://www.bmw-stuttgart.de/",
                "email": "bmw-stuttgart@bmw.de",
                "new_car_email": "online-sales-na-nl-3@bmw.de",
                "phone": "+49-711-13188000",
                "is_published": True,
            }
        ],
    )
    assert response.status_code == 200

    campaign_id = _create_campaign(client)
    client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    )

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "campaign_id_hint": campaign_id,
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-homepage-cluster",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-homepage-cluster@example.test>",
            "sender_email": "zaour@assadov.de",
            "subject": "Rueckmeldung",
            "text_body": (
                "Mit freundlichen Gruessen\n"
                "Linus Hermann\n"
                "BMW Stuttgart\n"
                "Filiale Rosensteinpark\n"
                "Verkauf Neue Automobile\n"
                "Pragstraße 140\n"
                "70376 Stuttgart\n"
                "Tel.: +49-711-1318-5312\n"
                "Mail: Linus.Hermann@bmw.de\n"
                "Web: http://www.bmw-stuttgart.de/\n"
            ),
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )

    assert inbound.status_code == 201
    payload = inbound.json()
    assert payload["campaign_id"] == str(campaign_id)
    assert payload["dealer_id"] is not None
    assert payload["campaign_dealer_contact_id"] is not None
    assert payload["matching_status"] == "MATCHED_BY_DEALER_DB"
    assert payload["can_extract"] is True


def test_register_inbound_email_ignores_base64_html_noise(client) -> None:
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-html-001",
                "name": "BMW Stuttgart",
                "city": "Stuttgart",
                "email": "stuttgart-signature@bmw.de",
                "is_published": True,
            }
        ],
    )
    assert response.status_code == 200
    campaign_id = _create_campaign(client)
    contact = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    _mark_contact_sent(client, contact, "html-base64")

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "campaign_id_hint": campaign_id,
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-html-base64",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-html-base64@example.test>",
            "sender_email": "zaour@assadov.de",
            "subject": "Rueckmeldung",
            "html_body": (
                "<html><body>"
                "<img src=\"data:image/png;base64,QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo=\" />"
                "<p>Kontakt: stuttgart-signature@bmw.de</p>"
                "</body></html>"
            ),
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    assert inbound.json()["campaign_dealer_contact_id"] == contact["contact_id"]
    assert inbound.json()["matching_status"] == "MATCHED"


def test_register_inbound_email_technical_match_wins_over_conflicting_signature(client) -> None:
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-conflict-001",
                "name": "BMW Stuttgart",
                "city": "Stuttgart",
                "email": "stuttgart@bmw.de",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-conflict-002",
                "name": "BMW Muenchen",
                "city": "Muenchen",
                "email": "muenchen@bmw.de",
                "is_published": True,
            },
        ],
    )
    assert response.status_code == 200
    campaign_id = _create_campaign(client)
    contacts = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 2, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"]
    first_contact, second_contact = contacts
    _mark_contact_sent(client, first_contact, "conflict-stuttgart")
    _mark_contact_sent(client, second_contact, "conflict-muenchen")

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "campaign_id_hint": campaign_id,
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-conflict-technical",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-conflict-technical@example.test>",
            "in_reply_to": "<message-conflict-stuttgart@example.test>",
            "sender_email": "zaour@assadov.de",
            "subject": "Rueckmeldung",
            "text_body": "Mit freundlichen Gruessen\nBMW Muenchen\nMail: muenchen@bmw.de",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    payload = inbound.json()
    assert payload["campaign_dealer_contact_id"] == first_contact["contact_id"]
    assert payload["matching_status"] == "MATCHED_BY_REFERENCE"


def test_register_inbound_email_keeps_review_when_second_candidate_too_close(client) -> None:
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-close-001",
                "name": "Autohaus Beispiel Stuttgart GmbH",
                "street": "Pragstraße 140",
                "postal_code": "70376",
                "city": "Stuttgart",
                "email": "close1@example.de",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-close-002",
                "name": "Autohaus Beispiel Stuttgart GmbH",
                "street": "Pragstraße 140",
                "postal_code": "70376",
                "city": "Stuttgart",
                "email": "close2@example.de",
                "is_published": True,
            },
        ],
    )
    assert response.status_code == 200
    campaign_id = _create_campaign(client)
    contacts = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 2, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"]
    for index, contact in enumerate(contacts, start=1):
        _mark_contact_sent(client, contact, f"close-score-{index}")

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "campaign_id_hint": campaign_id,
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-close-score",
            "provider_thread_id": None,
            "internet_message_id": "<inbound-close-score@example.test>",
            "sender_email": "zaour@assadov.de",
            "subject": "Rueckmeldung",
            "text_body": "Autohaus Beispiel Stuttgart\nPragstraße 140\n70376 Stuttgart",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    assert inbound.json()["matching_status"] == "AMBIGUOUS"


def test_register_inbound_email_ambiguous_with_multiple_candidates(client) -> None:
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-dup-001",
                "name": "BMW AG Niederlassung Stuttgart 1",
                "city": "Stuttgart",
                "email": "shared@bmw.de",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-dup-002",
                "name": "BMW AG Niederlassung Stuttgart 2",
                "city": "Stuttgart",
                "email": "shared@bmw.de",
                "is_published": True,
            },
        ],
    )
    assert response.status_code == 200
    campaign_id = _create_campaign(client)
    claims = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 2, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"]
    first_claim, second_claim = claims
    client.post(
        f"/api/campaign-contacts/{first_claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-amb-1",
            "provider_thread_id": "gmail-thread-ambiguous",
            "internet_message_id": "<message-amb-1@example.test>",
            "sent_to": first_claim["effective_to"],
            "test_mode": False,
        },
    )
    client.post(
        f"/api/campaign-contacts/{second_claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-amb-2",
            "provider_thread_id": "gmail-thread-ambiguous",
            "internet_message_id": "<message-amb-2@example.test>",
            "sent_to": second_claim["effective_to"],
            "test_mode": False,
        },
    )

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-amb",
            "provider_thread_id": "gmail-thread-ambiguous",
            "internet_message_id": "<inbound-amb@example.test>",
            "sender_email": "unknown@bmw.de",
            "subject": "Rueckmeldung ohne Kampagnentoken",
            "text_body": "Bitte melden Sie sich.",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    )
    assert inbound.status_code == 201
    assert inbound.json()["matching_status"] == "AMBIGUOUS"


def test_debug_match_shows_checked_steps_and_candidates(client) -> None:
    response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-debug-001",
                "name": "BMW Debug 1",
                "city": "Stuttgart",
                "email": "debug-shared@bmw.de",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-debug-002",
                "name": "BMW Debug 2",
                "city": "Stuttgart",
                "email": "debug-shared@bmw.de",
                "is_published": True,
            },
        ],
    )
    assert response.status_code == 200
    campaign_id = _create_campaign(client)
    claims = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 2, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"]
    first_claim, second_claim = claims
    client.post(
        f"/api/campaign-contacts/{first_claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-debug-1",
            "provider_thread_id": "gmail-thread-debug-ambiguous",
            "internet_message_id": "<message-debug-1@example.test>",
            "sent_to": first_claim["effective_to"],
            "test_mode": False,
        },
    )
    client.post(
        f"/api/campaign-contacts/{second_claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-debug-2",
            "provider_thread_id": "gmail-thread-debug-ambiguous",
            "internet_message_id": "<message-debug-2@example.test>",
            "sent_to": second_claim["effective_to"],
            "test_mode": False,
        },
    )

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-debug",
            "provider_thread_id": "gmail-thread-debug-ambiguous",
            "internet_message_id": "<inbound-debug@example.test>",
            "sender_email": "unknown@bmw.de",
            "subject": "Rueckmeldung ohne Kampagnentoken",
            "text_body": "Bitte melden Sie sich.",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    ).json()

    debug = client.get(f"/api/inbound-emails/{inbound['id']}/debug-match")
    assert debug.status_code == 200
    payload = debug.json()
    assert payload["matching_status"] == "AMBIGUOUS"
    assert payload["checked"]["thread_match"] is False
    assert len(payload["candidate_contacts"]) == 2


def test_extract_offer_marks_question_and_acknowledgement_for_review(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    client.post(
        f"/api/campaign-contacts/{claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-2",
            "provider_thread_id": "gmail-thread-2",
            "internet_message_id": "<message-2@example.test>",
            "sent_to": claim["effective_to"],
            "test_mode": False,
        },
    )

    question = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-q",
            "provider_thread_id": "gmail-thread-2",
            "sender_email": "stuttgart@bmw.de",
            "subject": claim["subject"],
            "text_body": "Ist fuer Sie Barzahlung oder Leasing interessant?",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    ).json()
    question_extract = client.post(
        f"/api/inbound-emails/{question['id']}/extract-offer",
        json={"attachment_text": []},
    )
    assert question_extract.status_code == 200
    assert question_extract.json()["status"] == "QUESTION_FROM_DEALER"
    assert question_extract.json()["needs_review"] is True

    ack = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-ack",
            "provider_thread_id": "gmail-thread-ack",
            "sender_email": "stuttgart@bmw.de",
            "subject": claim["subject"],
            "text_body": "Vielen Dank fuer Ihre Anfrage. Wir melden uns.",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    ).json()
    ack_extract = client.post(
        f"/api/inbound-emails/{ack['id']}/extract-offer",
        json={"attachment_text": []},
    )
    assert ack_extract.status_code == 200
    assert ack_extract.json()["status"] == "ACKNOWLEDGEMENT_ONLY"
    assert ack_extract.json()["needs_review"] is True


def test_extract_offer_does_not_treat_leasing_rate_as_purchase_price(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]
    client.post(
        f"/api/campaign-contacts/{claim['contact_id']}/sent",
        json={
            "provider": "gmail",
            "provider_message_id": "gmail-message-lease",
            "provider_thread_id": "gmail-thread-lease",
            "internet_message_id": "<message-lease@example.test>",
            "sent_to": claim["effective_to"],
            "test_mode": False,
        },
    )

    inbound = client.post(
        "/api/inbound-emails",
        json={
            "mailbox_address": "zaour.ludwigsburger@gmail.com",
            "provider": "gmail",
            "provider_message_id": "inbound-lease",
            "provider_thread_id": "gmail-thread-lease",
            "sender_email": "stuttgart@bmw.de",
            "subject": claim["subject"],
            "text_body": "Leasingrate 799,00 EUR pro Monat bei 48 Monaten Laufzeit.",
            "received_at": datetime.now(UTC).isoformat(),
            "raw_metadata": {},
        },
    ).json()

    extraction = client.post(
        f"/api/inbound-emails/{inbound['id']}/extract-offer",
        json={"attachment_text": []},
    )
    assert extraction.status_code == 200
    assert extraction.json()["status"] == "NO_PRICE"
    assert extraction.json()["gross_final_price"] is None
    assert extraction.json()["needs_review"] is True


def test_review_queue_returns_needs_review_items_on_both_routes(client) -> None:
    _import_dealers(client)
    campaign_id = _create_campaign(client)
    claim = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    ).json()["contacts"][0]

    client.post(
        f"/api/campaign-contacts/{claim['contact_id']}/send-failed",
        json={"error_message": "SMTP timeout", "unknown_state": True},
    )

    old_route = client.get(f"/api/inbound-emails/review-queue?campaign_id={campaign_id}")
    new_route = client.get(f"/api/review-queue?campaign_id={campaign_id}")
    assert old_route.status_code == 200
    assert new_route.status_code == 200
    assert any(item["status"] == "SEND_STATE_UNKNOWN" for item in old_route.json())
    assert any(item["status"] == "SEND_STATE_UNKNOWN" for item in new_route.json())
