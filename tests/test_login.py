from unittest.mock import AsyncMock

import pytest


class TestLoginRoute:
    @pytest.mark.asyncio
    async def test_login_success(self, client):
        pool = client._transport.app.state.db_pool
        conn = pool.acquire().__aenter__.return_value
        conn.fetchrow = AsyncMock(return_value={
            "id": 1, "login": "admin", "password": "admin", "is_blocked": False
        })
        resp = await client.post("/api/v1/login", json={
            "login": "admin", "password": "admin"
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "ok"
        assert "access_token" in resp.cookies

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        pool = client._transport.app.state.db_pool
        conn = pool.acquire().__aenter__.return_value
        conn.fetchrow = AsyncMock(return_value=None)
        resp = await client.post("/api/v1/login", json={
            "login": "wrong", "password": "wrong"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_blocked_account(self, client):
        pool = client._transport.app.state.db_pool
        conn = pool.acquire().__aenter__.return_value
        conn.fetchrow = AsyncMock(return_value={
            "id": 2, "login": "blocked", "password": "pass", "is_blocked": True
        })
        resp = await client.post("/api/v1/login", json={
            "login": "blocked", "password": "pass"
        })
        assert resp.status_code == 403
