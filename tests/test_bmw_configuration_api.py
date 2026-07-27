from __future__ import annotations

FULL_CONFIGURATION_URL = (
    "https://configure.bmw.de/de_DE/configure/"
    "G61E/51HH/FKSFU,P0A90,S0337,S03G9,S09QV/SE000001"
    "?initialConfigId=chtwyiio&effectDate=2026-09-08"
)


def test_parse_bmw_configuration_endpoint_returns_normalized_payload(client) -> None:
    response = client.post(
        "/api/configurations/parse-bmw",
        json={"configuration_url": FULL_CONFIGURATION_URL},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"]["configuration_id"] == "chtwyiio"
    assert payload["vehicle"]["series_code"] == "G61E"
    assert payload["vehicle"]["model_code"] == "51HH"
    assert payload["configuration"]["paint"]["code"] == "P0A90"
    assert payload["configuration"]["upholstery"]["code"] == "FKSFU"
    assert payload["configuration"]["options"][0]["code"] == "S0337"
    assert payload["parser"]["status"] == "PARTIALLY_PARSED"
    assert payload["dealer_request"]["subject"] == "Anfrage Barkauf – BMW i5 xDrive40 Touring"


def test_parse_bmw_configuration_endpoint_rejects_invalid_host(client) -> None:
    response = client.post(
        "/api/configurations/parse-bmw",
        json={"configuration_url": "https://example.com/configid/chtwyiio"},
    )

    assert response.status_code == 422
