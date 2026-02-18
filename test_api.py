import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import MagicMock, AsyncMock, patch
import os

client = TestClient(app)

@pytest.fixture(autouse=True)
def ensure_model():
    # pool.close() вызывается через await, поэтому нужен AsyncMock
    fake_pool = AsyncMock()
    fake_pool.close = AsyncMock()

    with patch("main.asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool, \
         patch("main.kafka_producer.start", new_callable=AsyncMock), \
         patch("main.kafka_producer.stop", new_callable=AsyncMock):
        mock_create_pool.return_value = fake_pool
        with TestClient(app) as c:
            # Гарантируем не-None пул после старта lifespan
            app.state.db_pool = fake_pool
            yield c

# ---------------------------------------------------------------------------
# Existing /predict tests
# ---------------------------------------------------------------------------

def test_predict_success_violation():
    payload = {
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 101,
        "name": "Kekek",
        "description": "kakaka",
        "category": 1,
        "images_qty": 0
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "probability" in data
    assert isinstance(data["is_violation"], bool)

def test_predict_success_clean():
    payload = {
        "seller_id": 2,
        "is_verified_seller": True,
        "item_id": 102,
        "name": "Cabacaba",
        "description": "Abacababab " * 50,
        "category": 10,
        "images_qty": 5
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200

def test_validation_error_types():
    payload = {
        "seller_id": "not_int",
        "is_verified_seller": True,
        "item_id": 103,
        "name": "Test",
        "description": "Test",
        "category": 1,
        "images_qty": 1
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

def test_validation_error_constraints():
    payload = {
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 104,
        "name": "Test",
        "description": "Test",
        "category": 1,
        "images_qty": -5
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

def test_model_unavailable():
    original_model = app.state.model

    try:
        app.state.model = None

        payload = {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 105,
            "name": "Test",
            "description": "Test",
            "category": 1,
            "images_qty": 1
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 503
        assert response.json()["detail"] == "Service Unavailable: model not loaded"

    finally:
        app.state.model = original_model

def test_internal_server_error():
    original_model = app.state.model

    try:
        mock_model = MagicMock()
        mock_model.predict_proba.side_effect = Exception("Sklearn unexpected error")
        app.state.model = mock_model

        payload = {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 106,
            "name": "Test",
            "description": "Test",
            "category": 1,
            "images_qty": 1
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 500
        assert "Internal Server Error" in response.json()["detail"]

    finally:
        app.state.model = original_model

def test_simple_predict_success(monkeypatch):
    from services import repositories

    async def fake_get_ad_by_item_id(pool, item_id):
        return {
            "id": 1,
            "item_id": item_id,
            "seller_id": 10,
            "name": "Some",
            "description": "Bad description",
            "category": 1,
            "images_qty": 0
        }

    async def fake_get_user_by_id(pool, user_id):
        return {
            "id": user_id,
            "username": "tester",
            "is_verified": False
        }

    monkeypatch.setattr(repositories, "get_ad_by_item_id", AsyncMock(side_effect=fake_get_ad_by_item_id))
    monkeypatch.setattr(repositories, "get_user_by_id", AsyncMock(side_effect=fake_get_user_by_id))

    response = client.post("/simple_predict", json={"item_id": 101})
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data and "probability" in data
    assert isinstance(data["is_violation"], bool)

def test_simple_predict_not_found(monkeypatch):
    from services import repositories
    monkeypatch.setattr(repositories, "get_ad_by_item_id", AsyncMock(return_value=None))

    response = client.post("/simple_predict", json={"item_id": 9999})
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# /async_predict tests
# ---------------------------------------------------------------------------

def test_async_predict_success(monkeypatch):
    from services import repositories
    from clients import kafka

    monkeypatch.setattr(
        repositories,
        "get_ad_by_item_id",
        AsyncMock(return_value={"id": 5, "item_id": 200, "seller_id": 1}),
    )
    monkeypatch.setattr(
        repositories,
        "create_moderation_result",
        AsyncMock(return_value=42),
    )
    monkeypatch.setattr(
        kafka.kafka_producer,
        "send_moderation_request",
        AsyncMock(return_value=None),
    )

    response = client.post("/async_predict", json={"item_id": 200})
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == 42
    assert data["status"] == "pending"
    assert "message" in data

def test_async_predict_ad_not_found(monkeypatch):
    from services import repositories

    monkeypatch.setattr(
        repositories,
        "get_ad_by_item_id",
        AsyncMock(return_value=None),
    )

    response = client.post("/async_predict", json={"item_id": 9999})
    assert response.status_code == 404

def test_async_predict_invalid_item_id():
    response = client.post("/async_predict", json={"item_id": 0})
    assert response.status_code == 422

# ---------------------------------------------------------------------------
# /moderation_result/{task_id} tests
# ---------------------------------------------------------------------------

def test_moderation_result_pending(monkeypatch):
    from services import repositories

    monkeypatch.setattr(
        repositories,
        "get_moderation_result",
        AsyncMock(return_value={
            "id": 1,
            "item_id": 5,
            "status": "pending",
            "is_violation": None,
            "probability": None,
            "error_message": None,
            "created_at": None,
            "processed_at": None,
        }),
    )

    response = client.get("/moderation_result/1")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == 1
    assert data["status"] == "pending"
    assert data["is_violation"] is None
    assert data["probability"] is None

def test_moderation_result_completed(monkeypatch):
    from services import repositories

    monkeypatch.setattr(
        repositories,
        "get_moderation_result",
        AsyncMock(return_value={
            "id": 2,
            "item_id": 5,
            "status": "completed",
            "is_violation": True,
            "probability": 0.87,
            "error_message": None,
            "created_at": None,
            "processed_at": None,
        }),
    )

    response = client.get("/moderation_result/2")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == 2
    assert data["status"] == "completed"
    assert data["is_violation"] is True
    assert abs(data["probability"] - 0.87) < 1e-6

def test_moderation_result_not_found(monkeypatch):
    from services import repositories

    monkeypatch.setattr(
        repositories,
        "get_moderation_result",
        AsyncMock(return_value=None),
    )

    response = client.get("/moderation_result/9999")
    assert response.status_code == 404

# ---------------------------------------------------------------------------
# Worker unit tests (with mocked Kafka and DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_worker_process_message_success():
    from workers.moderation_worker import process_message
    from services import repositories

    ad = {"id": 10, "item_id": 300, "seller_id": 1, "images_qty": 3, "description": "OK", "category": 5}
    seller = {"id": 1, "username": "seller", "is_verified": True}
    task_row = {"id": 7}

    raw_message = {"item_id": 300, "timestamp": "2025-01-01T00:00:00Z"}

    mock_pool = MagicMock()
    mock_dlq_producer = AsyncMock()

    with (
        patch.object(repositories, "get_ad_by_item_id", AsyncMock(return_value=ad)),
        patch("workers.moderation_worker._get_pending_task", AsyncMock(return_value=task_row)),
        patch.object(repositories, "get_user_by_id", AsyncMock(return_value=seller)),
        patch.object(repositories, "update_moderation_result_completed", AsyncMock()),
    ):
        from model import get_or_create_model
        from services.predictor import PredictionService
        model = get_or_create_model()
        svc = PredictionService(model)

        await process_message(raw_message, mock_pool, svc, mock_dlq_producer)
        repositories.update_moderation_result_completed.assert_awaited_once()

@pytest.mark.asyncio
async def test_worker_process_message_ad_not_found():
    from workers.moderation_worker import process_message
    from services import repositories

    raw_message = {"item_id": 9999, "timestamp": "2025-01-01T00:00:00Z"}
    mock_pool = MagicMock()
    mock_dlq_producer = AsyncMock()

    with patch.object(repositories, "get_ad_by_item_id", AsyncMock(return_value=None)):
        from model import get_or_create_model
        from services.predictor import PredictionService
        model = get_or_create_model()
        svc = PredictionService(model)

        with pytest.raises(ValueError, match="not found in DB"):
            await process_message(raw_message, mock_pool, svc, mock_dlq_producer)

@pytest.mark.asyncio
async def test_worker_dlq_on_error():
    from workers.moderation_worker import handle_error
    from services import repositories

    raw_message = {"item_id": 300, "timestamp": "2025-01-01T00:00:00Z"}
    mock_pool = MagicMock()
    mock_dlq_producer = AsyncMock()
    mock_dlq_producer.send_and_wait = AsyncMock()

    with (
        patch.object(repositories, "get_ad_by_item_id", AsyncMock(return_value={"id": 10, "item_id": 300})),
        patch("workers.moderation_worker._get_pending_task", AsyncMock(return_value={"id": 7})),
        patch.object(repositories, "update_moderation_result_failed", AsyncMock()),
    ):
        await handle_error(raw_message, Exception("ML model down"), mock_pool, mock_dlq_producer, retry_count=3)

    mock_dlq_producer.send_and_wait.assert_awaited_once()
    call_args = mock_dlq_producer.send_and_wait.call_args
    import json
    dlq_msg = json.loads(call_args[0][1].decode("utf-8"))
    assert dlq_msg["retry_count"] == 3
    assert "ML model down" in dlq_msg["error"]
    assert dlq_msg["original_message"] == raw_message

# ---------------------------------------------------------------------------
# Integration tests (require DATABASE_URL)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_repositories_create_and_get():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL not set — skipping integration DB test")

    import asyncpg
    from services import repositories

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)

    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM moderation_results")
        await conn.execute("DELETE FROM ads")
        await conn.execute("DELETE FROM users")

    user_id = await repositories.create_user(pool, "test_user", is_verified=True)
    ad_id = await repositories.create_ad(pool, item_id=123456, seller_id=user_id, name="T", description="D", category=2, images_qty=3)

    ad = await repositories.get_ad_by_item_id(pool, 123456)
    assert ad is not None
    assert ad["item_id"] == 123456
    assert ad["seller_id"] == user_id

    user = await repositories.get_user_by_id(pool, user_id)
    assert user is not None
    assert user["username"] == "test_user"

    task_id = await repositories.create_moderation_result(pool, ad["id"])
    assert task_id is not None

    result = await repositories.get_moderation_result(pool, task_id)
    assert result is not None
    assert result["status"] == "pending"
    assert result["is_violation"] is None

    await repositories.update_moderation_result_completed(pool, task_id, True, 0.9)
    result = await repositories.get_moderation_result(pool, task_id)
    assert result["status"] == "completed"
    assert result["is_violation"] is True

    await pool.close()
