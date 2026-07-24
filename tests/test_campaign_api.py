from decimal import Decimal


def test_campaign_end_to_end_api_flow(client) -> None:
    create_campaign_response = client.post(
        "/campaigns",
        json={
            "name": "BMW i5 Kampagne",
            "notes": "Juli Runde",
            "configuration": {
                "model": "BMW i5",
                "variant": "eDrive40",
                "maximum_target_price": "70000.00",
                "payment_preference": "either",
                "requirements": [
                    {
                        "feature_key": "Lackierung",
                        "feature_value": "Black Sapphire",
                        "is_mandatory": True,
                    },
                    {
                        "feature_key": "Panoramadach",
                        "feature_value": "ja",
                        "is_mandatory": False,
                    },
                ],
            },
        },
    )
    assert create_campaign_response.status_code == 201
    campaign = create_campaign_response.json()
    campaign_id = campaign["id"]

    list_response = client.get("/campaigns")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    patch_response = client.patch(
        f"/campaigns/{campaign_id}/status",
        json={"status": "active"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "active"

    exact_offer_response = client.post(
        f"/campaigns/{campaign_id}/offers",
        json={
            "dealer_name": "Autohaus Exact",
            "source_type": "manual",
            "vehicle_price": "64000.00",
            "transfer_cost": "1000.00",
            "raw_response": "Manuell erfasst",
            "features": [
                {"feature_key": "Lackierung", "feature_value": "Black Sapphire"},
                {"feature_key": "Panoramadach", "feature_value": "ja"},
            ],
        },
    )
    assert exact_offer_response.status_code == 201

    extracted_offer_response = client.post(
        f"/campaigns/{campaign_id}/offers/extract",
        json={
            "dealer_name": "Autohaus Alternative",
            "source_type": "pdf",
            "text": "\n".join(
                [
                    "Gesamtpreis: 63000,00",
                    "Lackierung: Black Sapphire",
                ]
            ),
        },
    )
    assert extracted_offer_response.status_code == 201

    offers_response = client.get(f"/campaigns/{campaign_id}/offers")
    assert offers_response.status_code == 200
    assert len(offers_response.json()) == 2

    comparison_response = client.get(f"/campaigns/{campaign_id}/comparison")
    assert comparison_response.status_code == 200
    comparison = comparison_response.json()

    assert comparison["ranked_offers"][0]["category"] == "exact"
    assert comparison["ranked_offers"][0]["is_cheapest_exact"] is True
    assert comparison["ranked_offers"][1]["category"] == "alternative"
    assert Decimal(comparison["campaign"]["cheapest_exact_price"]) == Decimal("65000.00")
    assert Decimal(comparison["campaign"]["cheapest_overall_price"]) == Decimal("63000.00")
