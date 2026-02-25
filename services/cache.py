import json
import logging
from typing import Optional, Dict, Any
import redis.asyncio as redis

logger = logging.getLogger("cache")

class CacheStorage:
    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.ttl = 86400

    async def get_prediction(self, item_id: int) -> Optional[Dict[str, Any]]:
        key = f"prediction:{item_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_prediction(self, item_id: int, result: Dict[str, Any]):
        key = f"prediction:{item_id}"
        await self.client.set(key, json.dumps(result), ex=self.ttl)

    async def delete_prediction(self, item_id: int):
        key = f"prediction:{item_id}"
        await self.client.delete(key)

    async def close(self):
        # Используем aclose вместо close для предотвращения DeprecationWarning
        await self.client.aclose()