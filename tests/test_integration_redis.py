"""Integration tests for Redis cache.

Requires a running Redis instance.
Run: pytest -m integration
"""
import os

import pytest
import pytest_asyncio

from services.cache import CacheStorage

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def cache():
    storage = CacheStorage(REDIS_URL)
    yield storage
    await storage.client.flushdb()
    await storage.close()


class TestRedisCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        data = {"is_violation": True, "probability": 0.87}
        await cache.set_prediction(111, data)
        result = await cache.get_prediction(111)
        assert result == data

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        result = await cache.get_prediction(999999)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        await cache.set_prediction(222, {"is_violation": False, "probability": 0.1})
        await cache.delete_prediction(222)
        assert await cache.get_prediction(222) is None

    @pytest.mark.asyncio
    async def test_ttl_is_set(self, cache):
        await cache.set_prediction(333, {"is_violation": False, "probability": 0.05})
        ttl = await cache.client.ttl("prediction:333")
        assert 0 < ttl <= 86400
