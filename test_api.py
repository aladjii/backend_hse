import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import MagicMock, AsyncMock
import os

client = TestClient(app)

@pytest.fixture(autouse=True)
def ensure_model():
    with TestClient(app):
        yield

def test_predict_success_violation():
    payload = {
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 101,
        "name": "Kekek",
        "description": "kakaka",
        "category": 1,
        "images_qty": 0
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "probability" in data
    assert isinstance(data["is_violation"], bool)

def test_predict_success_clean():
    payload = {
        "seller_id": 2,
        "is_verified_seller": True,
        "item_id": 102,
        "name": "Cabacaba",
        "description": "Abacababab " * 50,
        "category": 10,
        "images_qty": 5
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200

def test_validation_error_types():
    payload = {
        "seller_id": "not_int",
        "is_verified_seller": True,
        "item_id": 103,
        "name": "Test",
        "description": "Test",
        "category": 1,
        "images_qty": 1
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

def test_validation_error_constraints():
    payload = {
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 104,
        "name": "Test",
        "description": "Test",
        "category": 1,
        "images_qty": -5
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

def test_model_unavailable():
    original_model = app.state.model

    try:
        app.state.model = None

        payload = {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 105,
            "name": "Test",
            "description": "Test",
            "category": 1,
            "images_qty": 1
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 503
        assert response.json()["detail"] == "Service Unavailable: model not loaded"

    finally:
        app.state.model = original_model

def test_internal_server_error():
    original_model = app.state.model

    try:
        mock_model = MagicMock()
        mock_model.predict_proba.side_effect = Exception("Sklearn unexpected error")
        app.state.model = mock_model

        payload = {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 106,
            "name": "Test",
            "description": "Test",
            "category": 1,
            "images_qty": 1
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 500
        assert "Internal Server Error" in response.json()["detail"]

    finally:
        app.state.model = original_model

def test_simple_predict_success(monkeypatch):
    from services import repositories

    async def fake_get_ad_by_item_id(pool, item_id):
        return {
            "id": 1,
            "item_id": item_id,
            "seller_id": 10,
            "name": "Some",
            "description": "Bad description",
            "category": 1,
            "images_qty": 0
        }

    async def fake_get_user_by_id(pool, user_id):
        return {
            "id": user_id,
            "username": "tester",
            "is_verified": False
        }

    monkeypatch.setattr(repositories, "get_ad_by_item_id", AsyncMock(side_effect=fake_get_ad_by_item_id))
    monkeypatch.setattr(repositories, "get_user_by_id", AsyncMock(side_effect=fake_get_user_by_id))

    response = client.post("/simple_predict", json={"item_id": 101})
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data and "probability" in data
    assert isinstance(data["is_violation"], bool)

def test_simple_predict_not_found(monkeypatch):
    from services import repositories
    monkeypatch.setattr(repositories, "get_ad_by_item_id", AsyncMock(return_value=None))

    response = client.post("/simple_predict", json={"item_id": 9999})
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_repositories_create_and_get():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL not set — skipping integration DB test")

    import asyncpg
    from services import repositories

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)

    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM ads")
        await conn.execute("DELETE FROM users")

    user_id = await repositories.create_user(pool, "test_user", is_verified=True)
    ad_id = await repositories.create_ad(pool, item_id=123456, seller_id=user_id, name="T", description="D", category=2, images_qty=3)

    ad = await repositories.get_ad_by_item_id(pool, 123456)
    assert ad is not None
    assert ad["item_id"] == 123456
    assert ad["seller_id"] == user_id

    user = await repositories.get_user_by_id(pool, user_id)
    assert user is not None
    assert user["username"] == "test_user"

    await pool.close()
