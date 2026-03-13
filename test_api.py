import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from services.auth_dependency import get_current_account

app.dependency_overrides[get_current_account] = lambda: {"id": 1}

client = TestClient(app)

def test_predict_use_cache():
    mock_cache = AsyncMock()
    mock_cache.get_prediction.return_value = {"is_violation": True, "probability": 0.99}
    mock_model = MagicMock()
    
    with patch.object(app.state, "cache", mock_cache, create=True), \
         patch.object(app.state, "model", mock_model, create=True):
        payload = {
            "seller_id": 1, "is_verified_seller": False, "item_id": 100,
            "name": "T", "description": "D", "category": 1, "images_qty": 0
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        assert response.json()["is_violation"] is True
        mock_cache.get_prediction.assert_awaited_once_with(100)

def test_close_ad_logic():
    mock_repo = AsyncMock(return_value=True)
    mock_cache = AsyncMock()
    mock_pool = AsyncMock()
    
    with patch("services.repositories.delete_ad_by_item_id", mock_repo), \
         patch.object(app.state, "cache", mock_cache, create=True), \
         patch.object(app.state, "db_pool", mock_pool, create=True):
        response = client.post("/close", json={"item_id": 123})
        assert response.status_code == 200
        mock_repo.assert_awaited_once()
        mock_cache.delete_prediction.assert_awaited_once_with(123)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_integration():
    from services.cache import CacheStorage
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    cache = CacheStorage(redis_url)
    
    await cache.set_prediction(999, {"is_violation": False, "probability": 0.1})
    res = await cache.get_prediction(999)
    assert res["is_violation"] is False
    
    await cache.delete_prediction(999)
    res = await cache.get_prediction(999)
    assert res is None
    await cache.close()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_repositories():
    import asyncpg
    from services import repositories
    db_url = os.getenv("DATABASE_URL")
    if not db_url: pytest.skip("No DB URL")
    
    pool = await asyncpg.create_pool(db_url)
    
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM ads WHERE item_id = 888")
        await conn.execute("DELETE FROM users WHERE username = 'test_user'")

    user_id = await repositories.create_user(pool, "test_user")
    await repositories.create_ad(pool, 888, user_id, "N", "D", 1, 0)
    
    ad = await repositories.get_ad_by_item_id(pool, 888)
    assert ad is not None
    assert "is_closed" in ad
    
    await repositories.delete_ad_by_item_id(pool, 888)
    ad = await repositories.get_ad_by_item_id(pool, 888)
    assert ad is None
    
    await pool.close()