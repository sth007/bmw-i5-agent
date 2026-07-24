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
