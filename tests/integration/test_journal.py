from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from flask.testing import FlaskClient
from sqlalchemy import text

from gerdiary.extensions import db
from gerdiary.modules.identity.models import Category
from gerdiary.modules.journal.models import FoodEntry

pytestmark = pytest.mark.usefixtures("api_app")


def _login(api_client: FlaskClient, email: str = "ayu@example.com") -> None:
    from tests.integration.test_auth import _register
    
    _register(api_client)
    api_client.post(
        "/api/v1/onboarding/complete",
        json={"name": "Ayu", "sleep_time": "23:00", "timezone": "Asia/Jakarta"},
    )


def test_create_food_entry_success(api_client: FlaskClient) -> None:
    _login(api_client)
    
    user_response = api_client.get("/api/v1/auth/me")
    assert user_response.status_code == 200
    data = user_response.json["data"]
    user_id = data["id"]
    
    category = Category(id=str(uuid4()), user_id=user_id, name="Test Food", category_type="food")
    db.session.add(category)
    db.session.commit()
    
    response = api_client.post(
        "/api/v1/food-entries",
        json={
            "category_id": category.id,
            "meal_type": "lunch",
            "food_name": "Nasi goreng",
            "consumed_at": "2026-09-04T12:30:00+07:00",
            "portion": 250,
            "portion_unit": "g",
        }
    )
    
    assert response.status_code == 201
    data = response.json["data"]
    assert data["food_name"] == "Nasi goreng"
    assert data["meal_type"] == "lunch"
    assert data["late_night"] is False


def test_create_food_entry_with_symptoms_success(api_client: FlaskClient) -> None:
    _login(api_client)
    
    user_response = api_client.get("/api/v1/auth/me")
    data = user_response.json["data"]
    user_id = data["id"]
    
    category = Category(id=str(uuid4()), user_id=user_id, name="Snack Test", category_type="food")
    db.session.add(category)
    db.session.commit()
    
    response = api_client.post(
        "/api/v1/food-entries",
        json={
            "category_id": category.id,
            "meal_type": "snack",
            "food_name": "Pedas pedes",
            "consumed_at": "2026-09-04T15:00:00+07:00",
            "food_attributes": ["spicy"],
            "symptoms": [
                {
                    "symptom": "heartburn",
                    "severity": "moderate",
                    "occurred_at": "2026-09-04T15:45:00+07:00",
                },
            ]
        }
    )
    
    assert response.status_code == 201
    data = response.json["data"]
    assert len(data["symptoms"]) == 1
    assert data["symptoms"][0]["symptom"] == "heartburn"


def test_create_symptom_event_standalone(api_client: FlaskClient) -> None:
    _login(api_client)
    
    response = api_client.post(
        "/api/v1/symptom-events",
        json={
            "symptom": "bloating",
            "severity": "mild",
            "occurred_at": "2026-09-03T22:00:00+07:00",
            "source": "entry_form",
        }
    )
    
    assert response.status_code == 201
    data = response.json["data"]
    assert data["symptom"] == "bloating"


def test_get_timeline_empty(api_client: FlaskClient) -> None:
    _login(api_client)
    
    response = api_client.get("/api/v1/timeline?date=2026-09-04")
    assert response.status_code == 200
    assert response.json["data"]["items"] == []


def test_get_timeline_returns_entries_and_symptoms(api_client: FlaskClient) -> None:
    _login(api_client)
    
    user_response = api_client.get("/api/v1/auth/me")
    user_id = user_response.json["data"]["id"]
    
    temp_category_id = str(uuid4())
    from tests.integration.test_journal import db
    category = Category(id=temp_category_id, user_id=user_id, name="Temp Cat", category_type="food")
    db.session.add(category)
    db.session.commit()
    
    food = FoodEntry(
        id=str(uuid4()),
        user_id=user_id,
        category_id=temp_category_id,
        meal_type="dinner",
        food_name="Ceri test",
        consumed_at=datetime.fromisoformat("2026-09-04T18:00:00+07:00"),
    )
    db.session.add(food)
    db.session.commit()
    
    response = api_client.get("/api/v1/timeline?date=2026-09-04")
    assert response.status_code == 200
    items = response.json["data"]["items"]
    food_items = [item for item in items if item["kind"] == "food"]
    assert len(food_items) >= 1


def test_create_food_entry_missing_category(api_client: FlaskClient) -> None:
    _login(api_client)
    
    response = api_client.post(
        "/api/v1/food-entries",
        json={
            "meal_type": "lunch",
            "food_name": "No category food",
        }
    )
    
    assert response.status_code == 400
    assert response.json["error"]["code"] == "missing_field"


def test_timeline_date_mandatory(api_client: FlaskClient) -> None:
    _login(api_client)
    
    response = api_client.get("/api/v1/timeline")
    assert response.status_code == 400
    assert response.json["error"]["code"] == "missing_field"


def test_timeline_invalid_date_format(api_client: FlaskClient) -> None:
    _login(api_client)
    
    response = api_client.get("/api/v1/timeline?date=invalid-date")
    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_query"


def test_update_food_entry(api_client: FlaskClient) -> None:
    _login(api_client)
    
    user_response = api_client.get("/api/v1/auth/me")
    user_id = user_response.json["data"]["id"]
    
    temp_cat_id = str(uuid4())
    category_obj = Category(
        id=temp_cat_id, user_id=user_id, name="Update Cat", category_type="food"
    )
    db.session.add(category_obj)
    db.session.commit()
    
    food = FoodEntry(
        id=str(uuid4()),
        user_id=user_id,
        category_id=temp_cat_id,
        meal_type="breakfast",
        food_name="Old name",
        consumed_at=datetime.now(),
    )
    db.session.add(food)
    db.session.commit()
    
    update_response = api_client.post(
        f"/api/v1/food-entries/{food.id}",
        json={"food_name": "New name"}
    )
    
    assert update_response.status_code == 200
    assert update_response.json["data"]["food_name"] == "New name"


def test_delete_food_entry(api_client: FlaskClient) -> None:
    _login(api_client)
    
    user_response = api_client.get("/api/v1/auth/me")
    user_id = user_response.json["data"]["id"]
    
    del_cat_id = str(uuid4())
    del_cat = Category(id=del_cat_id, user_id=user_id, name="Delete Cat", category_type="food")
    db.session.add(del_cat)
    db.session.commit()
    
    food = FoodEntry(
        id=str(uuid4()),
        user_id=user_id,
        category_id=del_cat_id,
        meal_type="lunch",
        food_name="To delete",
        consumed_at=datetime.now(),
    )
    db.session.add(food)
    db.session.commit()
    
    delete_response = api_client.delete(f"/api/v1/food-entries/{food.id}")
    assert delete_response.status_code == 204
    
    result = db.session.execute(
        text(f"SELECT deleted_at FROM food_entries WHERE id = '{food.id}'")
    ).scalar_one()
    assert result is not None


def test_cross_user_access_denied(api_client: FlaskClient) -> None:
    _login(api_client)

    user_response = api_client.get("/api/v1/auth/me")
    ayu_id = user_response.json["data"]["id"]

    cat_id = str(uuid4())
    db.session.add(Category(id=cat_id, user_id=ayu_id, name="Ayu Cat", category_type="food"))
    db.session.commit()

    food = FoodEntry(
        id=str(uuid4()),
        user_id=ayu_id,
        category_id=cat_id,
        meal_type="lunch",
        food_name="Ayu food",
        consumed_at=datetime.fromisoformat("2026-09-04T12:00:00+07:00"),
    )
    db.session.add(food)
    db.session.commit()

    register_response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "budi@example.com", "password": "portrait-of-you-1961", "name": "Budi"},
    )
    assert register_response.status_code == 201, register_response.json

    delete_response = api_client.delete(f"/api/v1/food-entries/{food.id}")
    assert delete_response.status_code == 404
    assert delete_response.json["error"]["code"] == "not_found"


def test_update_symptom_event(api_client: FlaskClient) -> None:
    _login(api_client)

    created = api_client.post(
        "/api/v1/symptom-events",
        json={
            "symptom": "bloating",
            "severity": "mild",
            "occurred_at": "2026-09-03T22:00:00+07:00",
            "source": "entry_form",
        },
    )
    assert created.status_code == 201
    event_id = created.json["data"]["id"]

    update_response = api_client.post(
        f"/api/v1/symptom-events/{event_id}",
        json={
            "symptom": "vomit_blood",
            "severity": "severe",
            "notes": "Makin parah",
            "occurred_at": "2026-09-04T06:30:00+07:00",
        },
    )

    assert update_response.status_code == 200
    data = update_response.json["data"]
    assert data["symptom"] == "vomit_blood"
    assert data["severity"] == "severe"
    assert data["notes"] == "Makin parah"
    assert datetime.fromisoformat(data["occurred_at"]) == datetime.fromisoformat(
        "2026-09-04T06:30:00+07:00"
    )
    assert data["red_flag"]["code"] == "RF_VOMIT_BLOOD"


def test_update_symptom_event_invalid(api_client: FlaskClient) -> None:
    _login(api_client)

    created = api_client.post(
        "/api/v1/symptom-events",
        json={
            "symptom": "gas",
            "severity": "mild",
            "occurred_at": "2026-09-03T21:00:00+07:00",
        },
    )
    assert created.status_code == 201
    event_id = created.json["data"]["id"]

    update_response = api_client.post(
        f"/api/v1/symptom-events/{event_id}",
        json={"symptom": "not-a-symptom", "severity": "extreme"},
    )

    assert update_response.status_code == 400
    assert update_response.json["error"]["code"] == "validation_failed"
    fields = update_response.json["error"]["fields"]
    assert "symptom" in fields
    assert "severity" in fields


def test_update_symptom_event_cross_user_denied(api_client: FlaskClient) -> None:
    _login(api_client)

    created = api_client.post(
        "/api/v1/symptom-events",
        json={
            "symptom": "heartburn",
            "severity": "mild",
            "occurred_at": "2026-09-03T20:00:00+07:00",
        },
    )
    assert created.status_code == 201
    event_id = created.json["data"]["id"]

    register_response = api_client.post(
        "/api/v1/auth/register",
        json={"email": "budi@example.com", "password": "portrait-of-you-1961", "name": "Budi"},
    )
    assert register_response.status_code == 201, register_response.json

    update_response = api_client.post(
        f"/api/v1/symptom-events/{event_id}",
        json={"severity": "severe"},
    )
    assert update_response.status_code == 404
    assert update_response.json["error"]["code"] == "not_found"


def test_update_symptom_event_not_found(api_client: FlaskClient) -> None:
    _login(api_client)

    update_response = api_client.post(
        f"/api/v1/symptom-events/{uuid4()}",
        json={"severity": "mild"},
    )
    assert update_response.status_code == 404
    assert update_response.json["error"]["code"] == "not_found"


def test_search_food_entries(api_client: FlaskClient) -> None:
    _login(api_client)

    user_response = api_client.get("/api/v1/auth/me")
    user_id = user_response.json["data"]["id"]

    category = Category(id=str(uuid4()), user_id=user_id, name="Search Cat", category_type="food")
    db.session.add(category)
    db.session.commit()

    for name, consumed_at in (
        ("Nasi goreng", "2026-09-01T12:00:00+07:00"),
        ("Bakso", "2026-09-02T19:00:00+07:00"),
        ("Nasi uduk", "2026-09-03T07:00:00+07:00"),
    ):
        created = api_client.post(
            "/api/v1/food-entries",
            json={
                "category_id": category.id,
                "meal_type": "lunch",
                "food_name": name,
                "consumed_at": consumed_at,
            },
        )
        assert created.status_code == 201, created.json

    by_name = api_client.get("/api/v1/food-entries/search", query_string={"q": "nasi"})
    assert by_name.status_code == 200
    names = {entry["food_name"] for entry in by_name.json["data"]["entries"]}
    assert names == {"Nasi goreng", "Nasi uduk"}

    by_range = api_client.get(
        "/api/v1/food-entries/search",
        query_string={"start": "2026-09-02", "end": "2026-09-03"},
    )
    assert by_range.status_code == 200
    range_names = {entry["food_name"] for entry in by_range.json["data"]["entries"]}
    assert range_names == {"Bakso", "Nasi uduk"}

    invalid_date = api_client.get(
        "/api/v1/food-entries/search", query_string={"start": "bukan-tanggal"}
    )
    assert invalid_date.status_code == 400


def test_search_food_entries_filters(api_client: FlaskClient) -> None:
    _login(api_client)

    user_id = api_client.get("/api/v1/auth/me").json["data"]["id"]
    category = Category(id=str(uuid4()), user_id=user_id, name="Search Cat", category_type="food")
    db.session.add(category)
    db.session.commit()

    for name, consumed_at in (
        ("Nasi goreng", "2026-09-01T12:30:00+07:00"),
        ("Nasi uduk", "2026-09-02T08:00:00+07:00"),
        ("Bakso", "2026-09-03T19:00:00+07:00"),
    ):
        created = api_client.post(
            "/api/v1/food-entries",
            json={
                "category_id": category.id,
                "meal_type": "lunch",
                "food_name": name,
                "consumed_at": consumed_at,
            },
        )
        assert created.status_code == 201, created.json

    by_name = api_client.get("/api/v1/food-entries/search", query_string={"q": "nasi"})
    assert by_name.status_code == 200
    names = {entry["food_name"] for entry in by_name.json["data"]["entries"]}
    assert names == {"Nasi goreng", "Nasi uduk"}
    assert by_name.json["meta"]["total"] == 2

    by_range = api_client.get(
        "/api/v1/food-entries/search",
        query_string={"start": "2026-09-02", "end": "2026-09-03"},
    )
    assert by_range.status_code == 200
    range_names = {entry["food_name"] for entry in by_range.json["data"]["entries"]}
    assert range_names == {"Nasi uduk", "Bakso"}

    invalid = api_client.get("/api/v1/food-entries/search", query_string={"start": "01-09"})
    assert invalid.status_code == 400


def test_late_night_detection(api_client: FlaskClient) -> None:
    _login(api_client)

    user_response = api_client.get("/api/v1/auth/me")
    user_id = user_response.json["data"]["id"]

    category = Category(id=str(uuid4()), user_id=user_id, name="Night Cat", category_type="food")
    db.session.add(category)
    db.session.commit()

    response = api_client.post(
        "/api/v1/food-entries",
        json={
            "category_id": category.id,
            "meal_type": "snack",
            "food_name": "Midnight snack",
            "consumed_at": "2026-09-03T22:00:00+07:00",
        },
    )

    assert response.status_code == 201, response.json


def test_repeat_food_entry(api_client: FlaskClient) -> None:
    _login(api_client)
    
    # Create an original food entry
    user_response = api_client.get("/api/v1/auth/me")
    user_id = user_response.json["data"]["id"]
    
    category = Category(id=str(uuid4()), user_id=user_id, name="Apple", category_type="food")
    db.session.add(category)
    db.session.commit()
    
    from datetime import UTC, datetime, timedelta, timezone
    
    wib = timezone(timedelta(hours=7))
    
    def _wib_iso(minutes_from_now: int) -> str:
        local = datetime.now(UTC).astimezone(wib) + timedelta(minutes=minutes_from_now)
        return local.strftime("%Y-%m-%dT%H:%M:%S+07:00")
    
    # Waktu siang tetap supaya late_night deterministik (jauh dari bedtime 23:00),
    # tapi digeser ke masa lalu bila siang WIB belum terjadi hari ini.
    now_wib = datetime.now(UTC).astimezone(wib)
    local_noon = now_wib.replace(hour=12, minute=0, second=0, microsecond=0)
    if local_noon > now_wib:
        local_noon -= timedelta(days=1)
    consumed_at_raw = local_noon.strftime("%Y-%m-%dT%H:%M:%S+07:00")
    
    create_response = api_client.post(
        "/api/v1/food-entries",
        json={
            "category_id": category.id,
            "meal_type": "breakfast",
            "food_name": "Red apple",
            "consumed_at": consumed_at_raw,
            "emoji": "\U0001f34e",
            "portion": 1,
            "portion_unit": "pcs",
            "tags": ["healthy"],
            "notes": "Fresh from market",
        },
    )
    assert create_response.status_code == 201, f"Create failed: {create_response.json}"
    
    original_id = create_response.json["data"]["id"]
    original_entry = create_response.json["data"]
    original_consumed_at = original_entry["consumed_at"]
    
    # Repeat the food entry with new consumed_at (30 minutes later)
    repeat_time = (local_noon + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S+07:00")
    repeat_response = api_client.post(
        f"/api/v1/food-entries/{original_id}/repeat",
        json={"consumed_at": repeat_time},
    )
    
    assert repeat_response.status_code == 201, repeat_response.json
    new_entry = repeat_response.json["data"]
    
    # New entry should have same food data but different timestamp
    assert new_entry["food_name"] == original_entry["food_name"]
    assert new_entry["meal_type"] == original_entry["meal_type"]
    assert new_entry["emoji"] == original_entry["emoji"]
    assert new_entry["portion"] == original_entry["portion"]
    assert new_entry["portion_unit"] == original_entry["portion_unit"]
    assert new_entry["tags"] == original_entry["tags"]
    assert new_entry["notes"] == original_entry["notes"]
    assert datetime.fromisoformat(new_entry["consumed_at"]) == datetime.fromisoformat(repeat_time)
    
    # Original entry should still exist unchanged
    get_response = api_client.get(f"/api/v1/food-entries/{original_id}")
    assert get_response.status_code == 200
    assert get_response.json["data"]["consumed_at"] == original_consumed_at
    assert get_response.json["data"]["late_night"] is False
