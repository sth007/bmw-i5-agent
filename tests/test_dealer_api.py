import json
from pathlib import Path


def test_dealer_import_list_update_delete_flow(client) -> None:
    import_payload = json.loads(
        Path("tests/data/dealers_import.json").read_text(encoding="utf-8")
    )

    import_response = client.post("/dealers/import", json=import_payload)
    assert import_response.status_code == 200
    assert import_response.json() == {
        "received": 1,
        "created": 1,
        "updated": 0,
    }

    list_response = client.get("/dealers")
    assert list_response.status_code == 200
    dealers = list_response.json()
    assert len(dealers) == 1
    dealer_id = dealers[0]["id"]
    assert dealers[0]["bmw_dealer_id"] == "bmw-1001"

    get_response = client.get(f"/dealers/{dealer_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Autohaus Nord"

    patch_response = client.patch(
        f"/dealers/{dealer_id}",
        json={
            "name": "Autohaus Nordost",
            "city": "Hamburg",
            "is_published": False,
        },
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["name"] == "Autohaus Nordost"
    assert patched["city"] == "Hamburg"
    assert patched["is_published"] is False

    delete_response = client.delete(f"/dealers/{dealer_id}")
    assert delete_response.status_code == 204

    list_after_delete = client.get("/dealers")
    assert list_after_delete.status_code == 200
    assert list_after_delete.json() == []


def test_dealer_import_updates_existing_dealer(client) -> None:
    first_payload = [
        {
            "bmw_dealer_id": "bmw-2001",
            "name": "Autohaus Sued",
            "city": "Muenchen",
            "is_published": True,
        }
    ]
    second_payload = [
        {
            "bmw_dealer_id": "bmw-2001",
            "name": "Autohaus Sued Update",
            "city": "Koeln",
            "is_published": False,
        }
    ]

    first_response = client.post("/dealers/import", json=first_payload)
    assert first_response.status_code == 200
    assert first_response.json()["created"] == 1

    second_response = client.post("/dealers/import", json=second_payload)
    assert second_response.status_code == 200
    assert second_response.json() == {
        "received": 1,
        "created": 0,
        "updated": 1,
    }

    dealers_response = client.get("/dealers")
    assert dealers_response.status_code == 200
    dealer = dealers_response.json()[0]
    assert dealer["name"] == "Autohaus Sued Update"
    assert dealer["city"] == "Koeln"
    assert dealer["is_published"] is False


def test_dealer_count_and_statistics_endpoints(client) -> None:
    payload = [
        {
            "bmw_dealer_id": "bmw-3001",
            "name": "Autohaus West",
            "city": "Duesseldorf",
            "email": "west@example.com",
            "phone": "+49-211-111111",
            "is_published": True,
        },
        {
            "bmw_dealer_id": "bmw-3002",
            "name": "Autohaus Ost",
            "city": "Leipzig",
            "is_published": False,
        },
    ]

    import_response = client.post("/dealers/import", json=payload)
    assert import_response.status_code == 200

    count_response = client.get("/dealers/count")
    assert count_response.status_code == 200
    assert count_response.json() == {"dealer_count": 2}

    statistics_response = client.get("/dealers/statistics")
    assert statistics_response.status_code == 200
    assert statistics_response.json() == {
        "dealer_count": 2,
        "active_dealer_count": 1,
        "inactive_dealer_count": 1,
        "distinct_city_count": 2,
        "duplicate_bmw_dealer_id_count": 0,
        "invalid_record_count": 1,
    }


def test_debug_selection_endpoint_returns_counts_and_sample(client) -> None:
    payload = [
        {
            "bmw_dealer_id": "bmw-debug-001",
            "name": "Autohaus West",
            "city": "Duesseldorf",
            "email": "west@example.com",
            "is_published": True,
        },
        {
            "bmw_dealer_id": "bmw-debug-002",
            "name": "Autohaus Ost",
            "city": "Leipzig",
            "email": "ost@example.com",
            "is_published": True,
        },
        {
            "bmw_dealer_id": "bmw-debug-003",
            "name": "Autohaus Nord",
            "city": "Hamburg",
            "is_published": True,
        },
    ]

    import_response = client.post("/dealers/import", json=payload)
    assert import_response.status_code == 200

    response = client.get("/api/dealers/debug-selection?limit=2")
    assert response.status_code == 200

    data = response.json()
    assert data["total_dealers"] == 3
    assert data["published_dealers"] == 3
    assert data["dealers_with_email"] == 2
    assert data["eligible_dealers"] == 2
    assert data["selected_dealers"] == 2
    assert data["suspicious_test_dealers"] == 2
    assert len(data["sample"]) == 2
    assert data["sample"][0]["email"] == "west@example.com"
    assert "FROM dealer" in data["selection_sql"]
