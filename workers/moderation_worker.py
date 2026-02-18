"""
Kafka consumer worker for moderation requests.

Run:
    python -m workers.moderation_worker
"""
import asyncio
import json
import logging
import os
import sys

import asyncpg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from datetime import datetime, timezone

# Allow importing project modules when executed as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model import get_or_create_model
from services.predictor import PredictionService
from services import repositories

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("moderation_worker")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
DATABASE_URL = os.getenv("DATABASE_URL")
MODERATION_TOPIC = "moderation"
DLQ_TOPIC = "moderation_dlq"
GROUP_ID = "moderation-workers"

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5


async def process_message(
    raw_message: dict,
    pool,
    prediction_service: PredictionService,
    dlq_producer: AIOKafkaProducer,
    retry_count: int = 0,
) -> None:
    item_id: int = raw_message["item_id"]

    # Find the ad record
    ad = await repositories.get_ad_by_item_id(pool, item_id)
    if ad is None:
        raise ValueError(f"Ad with item_id={item_id} not found in DB")

    # Find the pending moderation task for this ad
    task_row = await _get_pending_task(pool, ad["id"])
    if task_row is None:
        raise ValueError(f"No pending moderation task for ad id={ad['id']}")

    task_id = task_row["id"]

    # Get seller data
    seller = await repositories.get_user_by_id(pool, ad["seller_id"])
    if seller is None:
        raise ValueError(f"Seller with id={ad['seller_id']} not found")

    is_violation, probability = prediction_service.predict(
        is_verified=bool(seller.get("is_verified", False)),
        images_qty=int(ad.get("images_qty", 0)),
        description=str(ad.get("description", "")),
        category=int(ad.get("category", 0)),
    )

    await repositories.update_moderation_result_completed(pool, task_id, is_violation, probability)
    logger.info(
        f"Moderation complete: task_id={task_id}, item_id={item_id}, "
        f"is_violation={is_violation}, probability={probability:.4f}"
    )


async def _get_pending_task(pool, ad_db_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT id FROM moderation_results WHERE item_id = $1 AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
            ad_db_id,
        )


async def handle_error(
    raw_message: dict,
    error: Exception,
    pool,
    dlq_producer: AIOKafkaProducer,
    retry_count: int,
) -> None:
    error_str = str(error)
    item_id = raw_message.get("item_id")
    logger.error(f"Error processing item_id={item_id} (attempt {retry_count}): {error_str}")

    # Try to mark pending task as failed in DB
    try:
        ad = await repositories.get_ad_by_item_id(pool, item_id)
        if ad is not None:
            task_row = await _get_pending_task(pool, ad["id"])
            if task_row is not None:
                await repositories.update_moderation_result_failed(pool, task_row["id"], error_str)
    except Exception as db_err:
        logger.error(f"Failed to update DB status for item_id={item_id}: {db_err}")

    dlq_message = {
        "original_message": raw_message,
        "error": error_str,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retry_count": retry_count,
    }
    await dlq_producer.send_and_wait(
        DLQ_TOPIC, json.dumps(dlq_message).encode("utf-8")
    )
    logger.info(f"Sent to DLQ: item_id={item_id}")


async def run_worker():
    logger.info("Loading ML model...")
    model = get_or_create_model()
    prediction_service = PredictionService(model)

    logger.info("Connecting to DB...")
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)

    logger.info("Starting Kafka consumer and DLQ producer...")
    consumer = AIOKafkaConsumer(
        MODERATION_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
    )
    dlq_producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

    await consumer.start()
    await dlq_producer.start()
    logger.info(f"Worker started, listening on topic '{MODERATION_TOPIC}'")

    try:
        async for msg in consumer:
            raw_message = msg.value
            item_id = raw_message.get("item_id")
            logger.info(f"Received message: item_id={item_id}")

            success = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    await process_message(raw_message, pool, prediction_service, dlq_producer, attempt)
                    success = True
                    break
                except Exception as e:
                    logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed for item_id={item_id}: {e}")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY_SECONDS)

            if not success:
                await handle_error(raw_message, Exception(f"Failed after {MAX_RETRIES} attempts"), pool, dlq_producer, MAX_RETRIES)

    finally:
        await consumer.stop()
        await dlq_producer.stop()
        await pool.close()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(run_worker())
