def test_legacy_offer_extract_endpoint_remains_available(client) -> None:
    response = client.post(
        "/offers/extract",
        json={
            "text": "\n".join(
                [
                    "Angebot Nr. 20216449",
                    "Nachlass Modell und Ausstattung (25,7%)",
                    "Händlerleistungen 1.290,00",
                    "Gesamtpreis 56.881,26",
                    "Der Bruttolistenpreis für dieses Fahrzeug beträgt 74.820,00 EUR.",
                    "Verkäufer Linus Hermann",
                ]
            ),
            "campaign_id": "campaign-001",
            "configuration_id": "config-001",
            "dealer_id": "dealer-001",
            "pdf_filename": "angebot.pdf",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["campaign_id"] == "campaign-001"
    assert payload["configuration_id"] == "config-001"
    assert payload["dealer_id"] == "dealer-001"
    assert payload["pdf_filename"] == "angebot.pdf"
    assert payload["offer_price"] == "56881.26"
