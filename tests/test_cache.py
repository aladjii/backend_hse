import json
from unittest.mock import AsyncMock

import pytest

from services.cache import CacheStorage


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def cache_storage(mock_redis):
    storage = CacheStorage.__new__(CacheStorage)
    storage.client = mock_redis
    storage.ttl = 86400
    return storage


class TestCacheStorage:
    @pytest.mark.asyncio
    async def test_get_prediction_miss(self, cache_storage, mock_redis):
        mock_redis.get.return_value = None
        result = await cache_storage.get_prediction(1)
        assert result is None
        mock_redis.get.assert_called_once_with("prediction:1")

    @pytest.mark.asyncio
    async def test_get_prediction_hit(self, cache_storage, mock_redis):
        data = {"is_violation": True, "probability": 0.95}
        mock_redis.get.return_value = json.dumps(data)
        result = await cache_storage.get_prediction(42)
        assert result == data

    @pytest.mark.asyncio
    async def test_set_prediction(self, cache_storage, mock_redis):
        data = {"is_violation": False, "probability": 0.1}
        await cache_storage.set_prediction(10, data)
        mock_redis.set.assert_called_once_with(
            "prediction:10", json.dumps(data), ex=86400
        )

    @pytest.mark.asyncio
    async def test_delete_prediction(self, cache_storage, mock_redis):
        await cache_storage.delete_prediction(5)
        mock_redis.delete.assert_called_once_with("prediction:5")

    @pytest.mark.asyncio
    async def test_close(self, cache_storage, mock_redis):
        await cache_storage.close()
        mock_redis.aclose.assert_called_once()
