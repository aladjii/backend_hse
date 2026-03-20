import asyncio
import json
import logging
import os

import asyncpg
from aiokafka import AIOKafkaConsumer

from clients.kafka import KafkaProducerClient
from model import get_or_create_model
from services import repositories
from services.predictor import PredictionService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("worker")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/moderation")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
MODERATION_TOPIC = "moderation"
MAX_RETRIES = 3


async def process_message(
    pool: asyncpg.Pool,
    prediction_service: PredictionService,
    producer: KafkaProducerClient,
    data: dict,
) -> None:
    item_id = data["item_id"]
    ad = await repositories.get_ad_by_item_id(pool, item_id)
    if not ad:
        logger.warning("Ad not found for item_id=%d", item_id)
        return

    moderation = await repositories.get_latest_moderation_result_by_ad_id(pool, ad["id"])
    if not moderation:
        logger.warning("No moderation task for ad_id=%d", ad["id"])
        return

    task_id = moderation["id"]

    try:
        seller = await repositories.get_user_by_id(pool, ad["seller_id"])
        is_violation, probability = prediction_service.predict(
            is_verified=bool(seller.get("is_verified", False)) if seller else False,
            images_qty=int(ad.get("images_qty", 0)),
            description=str(ad.get("description", "")),
            category=int(ad.get("category", 0)),
        )
        await repositories.update_moderation_result_completed(pool, task_id, is_violation, probability)
        logger.info("Completed task_id=%d item_id=%d violation=%s", task_id, item_id, is_violation)
    except Exception as e:
        logger.error("Failed task_id=%d: %s", task_id, e)
        retry_count = data.get("retry_count", 0) + 1
        if retry_count < MAX_RETRIES:
            data["retry_count"] = retry_count
            await producer.send_to_dlq(data, str(e), retry_count)
        else:
            await repositories.update_moderation_result_failed(pool, task_id, str(e))


async def main() -> None:
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5)
    model = get_or_create_model()
    prediction_service = PredictionService(model)

    producer = KafkaProducerClient()
    await producer.start()

    consumer = AIOKafkaConsumer(
        MODERATION_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="moderation-workers",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
    )
    await consumer.start()
    logger.info("Worker started, consuming from '%s'", MODERATION_TOPIC)

    try:
        async for msg in consumer:
            await process_message(pool, prediction_service, producer, msg.value)
    finally:
        await consumer.stop()
        await producer.stop()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
