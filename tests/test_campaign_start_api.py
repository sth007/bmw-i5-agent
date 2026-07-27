def test_start_campaign_creates_draft_and_email_previews(client) -> None:
    import_payload = [
        {
            "bmw_dealer_id": "bmw-start-001",
            "name": "BMW AG Niederlassung Stuttgart",
            "city": "Stuttgart",
            "email": "bmw-stuttgart@bmw.de",
            "is_published": True,
        },
        {
            "bmw_dealer_id": "bmw-start-002",
            "name": "BMW AG Niederlassung Muenchen",
            "city": "Muenchen",
            "email": "bmw-muenchen@bmw.de",
            "is_published": True,
        },
        {
            "bmw_dealer_id": "bmw-start-003",
            "name": "BMW AG Niederlassung Hamburg",
            "city": "Hamburg",
            "email": "bmw-hamburg@bmw.de",
            "is_published": False,
        },
    ]
    dealer_import_response = client.post("/dealers/import", json=import_payload)
    assert dealer_import_response.status_code == 200

    response = client.post(
        "/api/campaigns/start",
        json={
            "campaign_name": "BMW i5 Touring Juli 2026",
            "config_url": "https://configure.bmw.de/de_DE/configid/chtwyiio",
            "dealer_limit": 2,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["campaign_name"] == "BMW i5 Touring Juli 2026"
    assert payload["config_id"] == "chtwyiio"
    assert payload["status"] == "DRAFT"
    assert len(payload["dealers"]) == 2
    assert [dealer["dealer_id"] for dealer in payload["dealers"]] == [1, 2]
    assert payload["email_previews"][0]["to"] == "bmw-stuttgart@bmw.de"
    assert payload["email_previews"][0]["dealer_name"] == "BMW AG Niederlassung Stuttgart"
    assert payload["email_previews"][0]["subject"] == "Anfrage zu meiner BMW Wunschkonfiguration"
    assert "https://configure.bmw.de/de_DE/configid/chtwyiio" in payload["email_previews"][0]["body"]


def test_campaign_from_config_uses_default_dealer_limit(client) -> None:
    dealer_import_response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-from-config-001",
                "name": "Dealer 1",
                "city": "Stuttgart",
                "email": "dealer1@example.com",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-from-config-002",
                "name": "Dealer 2",
                "city": "Muenchen",
                "email": "dealer2@example.com",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-from-config-003",
                "name": "Dealer 3",
                "city": "Hamburg",
                "email": "dealer3@example.com",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-from-config-004",
                "name": "Dealer 4",
                "city": "Berlin",
                "email": "dealer4@example.com",
                "is_published": True,
            },
        ],
    )
    assert dealer_import_response.status_code == 200

    response = client.post(
        "/api/campaigns/from-config",
        json={
            "campaign_name": "BMW i5 Touring Juli 2026",
            "config_url": "https://configure.bmw.de/de_DE/configid/chtwyiio",
            "customer": {
                "name": "Max Mustermann",
                "email": "max.mustermann@example.de",
                "phone": "+49 170 1234567",
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["config_id"] == "chtwyiio"
    assert len(payload["dealers"]) == 3
    assert len(payload["email_previews"]) == 3
    assert payload["dealers"][0]["email"] == payload["email_previews"][0]["to"]
    assert "Max Mustermann" in payload["email_previews"][0]["body"]
    assert payload["warnings"] == []


def test_campaign_from_config_rejects_invalid_bmw_url(client) -> None:
    response = client.post(
        "/api/campaigns/from-config",
        json={
            "campaign_name": "BMW i5 Touring Juli 2026",
            "config_url": "https://example.com/configid/chtwyiio",
            "customer": {
                "name": "Max Mustermann",
                "email": "max.mustermann@example.de",
            },
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid BMW configuration URL."}


def test_campaign_from_config_rejects_invalid_customer_email(client) -> None:
    response = client.post(
        "/api/campaigns/from-config",
        json={
            "campaign_name": "BMW i5 Touring Juli 2026",
            "config_url": "https://configure.bmw.de/de_DE/configid/chtwyiio",
            "customer": {
                "name": "Max Mustermann",
                "email": "not-an-email",
            },
        },
    )

    assert response.status_code == 422


def test_campaign_from_config_rejects_blank_customer_name(client) -> None:
    response = client.post(
        "/api/campaigns/from-config",
        json={
            "campaign_name": "BMW i5 Touring Juli 2026",
            "config_url": "https://configure.bmw.de/de_DE/configid/chtwyiio",
            "customer": {
                "name": "",
                "email": "max.mustermann@example.de",
            },
        },
    )

    assert response.status_code == 422


def test_campaign_from_config_returns_warning_when_no_eligible_dealers_exist(client) -> None:
    dealer_import_response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-from-config-001",
                "name": "Dealer 1",
                "city": "Stuttgart",
                "email": "dealer1@example.com",
                "is_published": False,
            },
            {
                "bmw_dealer_id": "bmw-from-config-002",
                "name": "Dealer 2",
                "city": "Muenchen",
                "email": "dealer2@example.com",
                "is_published": False,
            },
        ],
    )
    assert dealer_import_response.status_code == 200

    response = client.post(
        "/api/campaigns/from-config",
        json={
            "campaign_name": "BMW i5 Touring Juli 2026",
            "config_url": "https://configure.bmw.de/de_DE/configid/chtwyiio",
            "customer": {
                "name": "Max Mustermann",
                "email": "max.mustermann@example.de",
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["dealers"] == []
    assert payload["email_previews"] == []
    assert payload["warnings"] == ["No eligible dealers with a valid email address were found."]


def test_campaign_from_public_config_creates_campaign_and_previews(client) -> None:
    dealer_import_response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-public-config-001",
                "name": "Dealer 1",
                "city": "Stuttgart",
                "email": "dealer1@example.com",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-public-config-002",
                "name": "Dealer 2",
                "city": "Muenchen",
                "email": "dealer2@example.com",
                "is_published": True,
            },
        ],
    )
    assert dealer_import_response.status_code == 200

    response = client.post(
        "/api/campaigns/from-public-config",
        json={
            "campaign_name": "BMW i5 Zaour",
            "dealer_limit": 2,
            "customer": {
                "name": "Zaour Assadov",
                "email": "bmw.agent@assadov.de",
                "phone": "+49 176 99791071",
            },
            "notes": "Nur Barkauf-Angebote relevant.",
            "maximum_target_price": 57000,
            "payment_preference": "cash",
            "public_configuration": {
                "config_id": "chtwyiio",
                "effect_date": "2026-09-08",
                "model_code": "51HH",
                "option_codes": ["FKSFU", "P0A90", "S0337", "S03G9", "S05AS"],
                "accessories": {
                    "SE000001": {
                        "accessoryId": "SE000001",
                        "quantity": 1,
                    }
                },
                "original_configuration_url": "https://configure.bmw.de/de_DE/configid/chtwyiio",
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["campaign_name"] == "BMW i5 Zaour"
    assert payload["config_id"] == "chtwyiio"
    assert payload["status"] == "DRAFT"
    assert len(payload["dealers"]) == 2
    assert len(payload["email_previews"]) == 2
    assert "BMW i5 xDrive40 Touring" in payload["email_previews"][0]["body"]
    assert "Sophistograu Brillanteffekt metallic" in payload["email_previews"][0]["body"]


def test_create_and_start_campaign_persists_configuration_and_returns_previews(client) -> None:
    dealer_import_response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-create-start-001",
                "name": "Dealer 1",
                "city": "Stuttgart",
                "email": "dealer1@example.com",
                "is_published": True,
            },
            {
                "bmw_dealer_id": "bmw-create-start-002",
                "name": "Dealer 2",
                "city": "Muenchen",
                "email": "dealer2@example.com",
                "is_published": True,
            },
        ],
    )
    assert dealer_import_response.status_code == 200

    response = client.post(
        "/api/campaigns/create-and-start",
        json={
            "campaign_name": "BMW i5 Zaour",
            "dealer_limit": 2,
            "customer": {
                "name": "Zaour Assadov",
                "email": "zaour.ludwigsburger@anaxo.de",
                "phone": "+49 176 99791071",
            },
            "notes": "Nur Barkauf-Angebote relevant.",
            "configuration": {
                "configuration_url": "https://configure.bmw.de/de_DE/configid/chtwyiio",
                "model": "BMW i5 Touring",
                "variant": "eDrive40",
                "list_price": 74820,
                "maximum_target_price": 57000,
                "payment_preference": "cash",
                "requirements": [
                    {
                        "feature_key": "must_have.color",
                        "feature_value": "Cape York Gruen",
                        "display_label": "Farbe",
                        "is_mandatory": True,
                    },
                    {
                        "feature_key": "optional.audio",
                        "feature_value": "harman/kardon",
                        "display_label": "Sound",
                        "is_mandatory": False,
                    },
                ],
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["campaign_name"] == "BMW i5 Zaour"
    assert payload["config_id"] == "chtwyiio"
    assert len(payload["dealers"]) == 2
    assert len(payload["email_previews"]) == 2
    assert "Zaour Assadov" in payload["email_previews"][0]["body"]

    campaign_response = client.get(f"/campaigns/{payload['campaign_id']}")
    assert campaign_response.status_code == 200
    campaign = campaign_response.json()
    assert campaign["name"] == "BMW i5 Zaour"
    assert campaign["notes"] == "Nur Barkauf-Angebote relevant."
    assert campaign["configuration"]["model"] == "BMW i5 Touring"
    assert campaign["configuration"]["payment_preference"] == "cash"
    assert len(campaign["configuration"]["requirements"]) == 2


def test_claim_contacts_uses_persisted_customer_and_configuration_in_email(client) -> None:
    dealer_import_response = client.post(
        "/dealers/import",
        json=[
            {
                "bmw_dealer_id": "bmw-claim-config-001",
                "name": "Dealer 1",
                "city": "Stuttgart",
                "email": "dealer1@example.com",
                "is_published": True,
            }
        ],
    )
    assert dealer_import_response.status_code == 200

    create_response = client.post(
        "/api/campaigns/create-and-start",
        json={
            "campaign_name": "BMW i5 Zaour",
            "dealer_limit": 1,
            "customer": {
                "name": "Zaour Assadov",
                "email": "zaour.ludwigsburger@anaxo.de",
                "phone": "+49 176 99791071",
            },
            "configuration": {
                "configuration_url": "https://configure.bmw.de/de_DE/configid/chtwyiio",
                "model": "BMW i5 Touring",
                "variant": "eDrive40",
                "list_price": 76600,
                "maximum_target_price": 57000,
                "payment_preference": "cash",
                "requirements": [
                    {
                        "feature_key": "vehicle.variant",
                        "feature_value": "BMW i5 eDrive40 Touring",
                        "display_label": "Variante",
                        "is_mandatory": True,
                    },
                    {
                        "feature_key": "exterior.color",
                        "feature_value": "Sophistograu Brillanteffekt metallic",
                        "display_label": "Außenfarbe",
                        "is_mandatory": True,
                    },
                ],
            },
        },
    )
    assert create_response.status_code == 201
    campaign_id = create_response.json()["campaign_id"]

    claim_response = client.post(
        f"/api/campaigns/{campaign_id}/contacts/claim",
        json={"limit": 1, "reservation_owner": "n8n-1", "test_mode": False},
    )
    assert claim_response.status_code == 200
    body = claim_response.json()["contacts"][0]["body"]
    assert "Zaour Assadov" in body
    assert "Variante: BMW i5 eDrive40 Touring" in body
    assert "Außenfarbe: Sophistograu Brillanteffekt metallic" in body
