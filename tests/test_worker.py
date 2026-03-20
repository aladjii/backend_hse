from unittest.mock import AsyncMock, MagicMock

import pytest

from model import train_model
from services.predictor import PredictionService
from workers.consumer import process_message


@pytest.fixture
def worker_deps():
    conn = AsyncMock()

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)

    tx_ctx = MagicMock()
    tx_ctx.__aenter__ = AsyncMock()
    tx_ctx.__aexit__ = AsyncMock(return_value=False)
    conn.transaction.return_value = tx_ctx

    pool = MagicMock()
    pool.acquire.return_value = ctx
    pool.close = AsyncMock()

    model = train_model()
    service = PredictionService(model)
    producer = AsyncMock()
    return pool, conn, service, producer


class TestWorkerProcessMessage:
    @pytest.mark.asyncio
    async def test_ad_not_found(self, worker_deps):
        pool, conn, service, producer = worker_deps
        conn.fetchrow = AsyncMock(return_value=None)
        await process_message(pool, service, producer, {"item_id": 999})
        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_moderation_task(self, worker_deps):
        pool, conn, service, producer = worker_deps
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": 1, "item_id": 10, "seller_id": 1, "name": "X",
             "description": "d", "category": 1, "images_qty": 0,
             "created_at": None, "is_closed": False},
            None,
        ])
        await process_message(pool, service, producer, {"item_id": 10})
        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_successful_processing(self, worker_deps):
        pool, conn, service, producer = worker_deps
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": 1, "item_id": 10, "seller_id": 1, "name": "X",
             "description": "desc", "category": 5, "images_qty": 2,
             "created_at": None, "is_closed": False},
            {"id": 77, "status": "pending", "is_violation": None, "probability": None},
            {"id": 1, "username": "seller", "is_verified": True, "created_at": None},
        ])
        await process_message(pool, service, producer, {"item_id": 10})
        conn.execute.assert_called_once()
        call_args = conn.execute.call_args
        assert "completed" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_failure_sends_to_dlq(self, worker_deps):
        pool, conn, service, producer = worker_deps
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": 1, "item_id": 10, "seller_id": 1, "name": "X",
             "description": "d", "category": 1, "images_qty": 0,
             "created_at": None, "is_closed": False},
            {"id": 77, "status": "pending", "is_violation": None, "probability": None},
            Exception("DB error"),
        ])
        await process_message(pool, service, producer, {"item_id": 10})
        producer.send_to_dlq.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_retries_marks_failed(self, worker_deps):
        pool, conn, service, producer = worker_deps
        conn.fetchrow = AsyncMock(side_effect=[
            {"id": 1, "item_id": 10, "seller_id": 1, "name": "X",
             "description": "d", "category": 1, "images_qty": 0,
             "created_at": None, "is_closed": False},
            {"id": 77, "status": "pending", "is_violation": None, "probability": None},
            Exception("DB error"),
        ])
        await process_message(
            pool, service, producer, {"item_id": 10, "retry_count": 3}
        )
        producer.send_to_dlq.assert_not_called()
        conn.execute.assert_called_once()
        assert "failed" in conn.execute.call_args[0][0]
