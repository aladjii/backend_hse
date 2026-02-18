import json
import logging
import os
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer

logger = logging.getLogger("kafka_producer")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
MODERATION_TOPIC = "moderation"
DLQ_TOPIC = "moderation_dlq"


class KafkaProducerClient:
    def __init__(self):
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()
        logger.info("Kafka producer started")

    async def stop(self):
        if self._producer is not None:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def send_moderation_request(self, item_id: int) -> None:
        message = {
            "item_id": item_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._producer.send_and_wait(MODERATION_TOPIC, message)
        logger.info(f"Sent moderation request for item_id={item_id}")

    async def send_to_dlq(self, original_message: dict, error: str, retry_count: int = 1) -> None:
        dlq_message = {
            "original_message": original_message,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": retry_count,
        }
        await self._producer.send_and_wait(DLQ_TOPIC, dlq_message)
        logger.info(f"Sent message to DLQ: item_id={original_message.get('item_id')}, error={error}")


kafka_producer = KafkaProducerClient()
