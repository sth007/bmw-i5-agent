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
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["config_id"] == "chtwyiio"
    assert len(payload["dealers"]) == 3
    assert len(payload["email_previews"]) == 3


def test_campaign_from_config_rejects_invalid_bmw_url(client) -> None:
    response = client.post(
        "/api/campaigns/from-config",
        json={
            "campaign_name": "BMW i5 Touring Juli 2026",
            "config_url": "https://example.com/configid/chtwyiio",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid BMW configuration URL."}
