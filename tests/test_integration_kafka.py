"""Integration tests for Kafka producer/consumer.

Requires a running Kafka instance.
Run: pytest -m integration
"""
import asyncio
import json
import os

import pytest
import pytest_asyncio
from aiokafka import AIOKafkaConsumer

from clients.kafka import KafkaProducerClient

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TEST_TOPIC = "moderation_test"

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def producer():
    p = KafkaProducerClient()
    p._producer = None
    from aiokafka import AIOKafkaProducer

    p._producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await p._producer.start()
    yield p
    await p._producer.stop()


@pytest_asyncio.fixture
async def consumer():
    c = AIOKafkaConsumer(
        "moderation",
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="test-group",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        consumer_timeout_ms=5000,
    )
    await c.start()
    # let consumer join group
    await asyncio.sleep(1)
    yield c
    await c.stop()


class TestKafkaProducer:
    @pytest.mark.asyncio
    async def test_send_moderation_request(self, producer, consumer):
        await producer.send_moderation_request(42)
        # consume the message
        msg = None
        async for m in consumer:
            msg = m.value
            break
        assert msg is not None
        assert msg["item_id"] == 42
        assert "timestamp" in msg

    @pytest.mark.asyncio
    async def test_send_to_dlq(self, producer):
        await producer.send_to_dlq({"item_id": 99}, "test error", retry_count=2)
        # just verify no exception — DLQ topic is auto-created
