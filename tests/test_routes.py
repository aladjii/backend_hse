from unittest.mock import AsyncMock

import pytest


def _get_conn(client):
    """Get the shared mock connection from the fake pool."""
    pool = client._transport.app.state.db_pool
    return pool.acquire().__aenter__.return_value


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestPredict:
    @pytest.mark.asyncio
    async def test_predict_success(self, client):
        resp = await client.post("/api/v1/predict", json={
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 100,
            "name": "Phone",
            "description": "A good phone",
            "category": 10,
            "images_qty": 3,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "is_violation" in data
        assert "probability" in data
        assert isinstance(data["is_violation"], bool)
        assert 0.0 <= data["probability"] <= 1.0

    @pytest.mark.asyncio
    async def test_predict_cached(self, client):
        cache = client._transport.app.state.cache
        cache.get_prediction = AsyncMock(return_value={
            "is_violation": True, "probability": 0.99
        })
        resp = await client.post("/api/v1/predict", json={
            "seller_id": 1,
            "is_verified_seller": False,
            "item_id": 200,
            "name": "Spam",
            "description": "spam",
            "category": 1,
            "images_qty": 0,
        })
        assert resp.status_code == 200
        assert resp.json()["probability"] == 0.99

    @pytest.mark.asyncio
    async def test_predict_invalid_payload(self, client):
        resp = await client.post("/api/v1/predict", json={"bad": "data"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_negative_images(self, client):
        resp = await client.post("/api/v1/predict", json={
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 100,
            "name": "X",
            "description": "x",
            "category": 1,
            "images_qty": -1,
        })
        assert resp.status_code == 422


class TestSimplePredict:
    @pytest.mark.asyncio
    async def test_simple_predict_ad_not_found(self, client):
        conn = _get_conn(client)
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": 1, "login": "admin", "password": "admin", "is_blocked": False},
            None,
        ])
        resp = await client.post("/api/v1/simple_predict", json={"item_id": 999})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_simple_predict_success(self, client):
        conn = _get_conn(client)
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": 1, "login": "admin", "password": "admin", "is_blocked": False},
            {"id": 1, "item_id": 10, "seller_id": 1, "name": "X",
             "description": "test ad", "category": 5, "images_qty": 2,
             "created_at": None, "is_closed": False},
            {"id": 1, "username": "seller", "is_verified": True, "created_at": None},
        ])
        resp = await client.post("/api/v1/simple_predict", json={"item_id": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert "is_violation" in data
        assert "probability" in data


class TestAsyncPredict:
    @pytest.mark.asyncio
    async def test_async_predict_ad_not_found(self, client):
        conn = _get_conn(client)
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": 1, "login": "admin", "password": "admin", "is_blocked": False},
            None,
        ])
        resp = await client.post("/api/v1/async_predict", json={"item_id": 999})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_async_predict_success(self, client):
        conn = _get_conn(client)
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": 1, "login": "admin", "password": "admin", "is_blocked": False},
            {"id": 1, "item_id": 10, "seller_id": 1, "name": "X",
             "description": "test", "category": 1, "images_qty": 0,
             "created_at": None, "is_closed": False},
            {"id": 77},
        ])
        resp = await client.post("/api/v1/async_predict", json={"item_id": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["task_id"] == 77


class TestModerationResult:
    @pytest.mark.asyncio
    async def test_result_not_found(self, client):
        conn = _get_conn(client)
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": 1, "login": "admin", "password": "admin", "is_blocked": False},
            None,
        ])
        resp = await client.get("/api/v1/moderation_result/999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_result_completed(self, client):
        conn = _get_conn(client)
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": 1, "login": "admin", "password": "admin", "is_blocked": False},
            {"id": 5, "item_id": 1, "status": "completed", "is_violation": True,
             "probability": 0.85, "error_message": None,
             "created_at": None, "processed_at": None},
            {"id": 1, "item_id": 10, "seller_id": 1, "name": "X",
             "description": "d", "category": 1, "images_qty": 0,
             "created_at": None, "is_closed": False},
        ])
        resp = await client.get("/api/v1/moderation_result/5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["is_violation"] is True


class TestCloseAd:
    @pytest.mark.asyncio
    async def test_close_not_found(self, client):
        conn = _get_conn(client)
        conn.fetchrow = AsyncMock(return_value={
            "id": 1, "login": "admin", "password": "admin", "is_blocked": False
        })
        conn.execute = AsyncMock(return_value="DELETE 0")
        resp = await client.post("/api/v1/close", json={"item_id": 999})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_close_success(self, client):
        conn = _get_conn(client)
        conn.fetchrow = AsyncMock(return_value={
            "id": 1, "login": "admin", "password": "admin", "is_blocked": False
        })
        conn.execute = AsyncMock(return_value="DELETE 1")
        resp = await client.post("/api/v1/close", json={"item_id": 10})
        assert resp.status_code == 200
        assert "closed" in resp.json()["message"].lower()


class TestAuth:
    @pytest.mark.asyncio
    async def test_no_token_returns_401(self, client):
        client.cookies.clear()
        resp = await client.post("/api/v1/predict", json={
            "seller_id": 1, "is_verified_seller": True, "item_id": 1,
            "name": "X", "description": "x", "category": 1, "images_qty": 0,
        })
        assert resp.status_code == 401
