import asyncio
import json
import logging
import os
import sys
import asyncpg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import get_or_create_model
from services.predictor import PredictionService
from services import repositories
from services.cache import CacheStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("moderation_worker")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MODERATION_TOPIC = "moderation"
DLQ_TOPIC = "moderation_dlq"
GROUP_ID = "moderation-workers"

async def process_message(raw_message, pool, service, cache, dlq_producer):
    item_id = raw_message["item_id"]
    ad = await repositories.get_ad_by_item_id(pool, item_id)
    if not ad: return

    task_row = await _get_pending_task(pool, ad["id"])
    if not task_row: return

    seller = await repositories.get_user_by_id(pool, ad["seller_id"])
    is_violation, prob = service.predict(
        is_verified=bool(seller["is_verified"]),
        images_qty=ad["images_qty"],
        description=ad["description"],
        category=ad["category"]
    )

    await repositories.update_moderation_result_completed(pool, task_row["id"], is_violation, prob)
    await cache.set_prediction(item_id, {"is_violation": is_violation, "probability": prob})

async def _get_pending_task(pool, ad_db_id):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT id FROM moderation_results WHERE item_id = $1 AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
            ad_db_id,
        )

async def run_worker():
    model = get_or_create_model()
    service = PredictionService(model)
    pool = await asyncpg.create_pool(DATABASE_URL)
    cache = CacheStorage(REDIS_URL)

    consumer = AIOKafkaConsumer(
        MODERATION_TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=GROUP_ID, value_deserializer=lambda v: json.loads(v.decode("utf-8"))
    )
    dlq_producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

    await consumer.start()
    await dlq_producer.start()

    try:
        async for msg in consumer:
            await process_message(msg.value, pool, service, cache, dlq_producer)
    finally:
        await consumer.stop()
        await dlq_producer.stop()
        await pool.close()
        await cache.close()

if __name__ == "__main__":
    asyncio.run(run_worker())