import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as redis

logger = logging.getLogger("cache")

PREDICTION_TTL = 86400


class CacheStorage:
    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.ttl = PREDICTION_TTL

    async def get_prediction(self, item_id: int) -> Optional[Dict[str, Any]]:
        data = await self.client.get(f"prediction:{item_id}")
        return json.loads(data) if data else None

    async def set_prediction(self, item_id: int, result: Dict[str, Any]) -> None:
        await self.client.set(
            f"prediction:{item_id}", json.dumps(result), ex=self.ttl
        )

    async def delete_prediction(self, item_id: int) -> None:
        await self.client.delete(f"prediction:{item_id}")

    async def close(self) -> None:
        await self.client.aclose()
