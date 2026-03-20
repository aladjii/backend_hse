import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, ".")

from model import train_model
from services.auth_service import AuthService
from services.predictor import PredictionService


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def ml_model():
    return train_model()


@pytest.fixture
def prediction_service(ml_model):
    return PredictionService(ml_model)


@pytest.fixture
def auth_service():
    return AuthService()


def _make_fake_pool():
    """Create a mock that behaves like asyncpg.Pool.

    asyncpg pattern: ``async with pool.acquire() as conn``
    pool.acquire() returns an async context manager (not a coroutine),
    so we need MagicMock with __aenter__/__aexit__.
    """
    conn = AsyncMock()

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)

    tx_ctx = MagicMock()
    tx_ctx.__aenter__ = AsyncMock()
    tx_ctx.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=tx_ctx)

    pool = MagicMock()
    pool.acquire.return_value = ctx
    pool.close = AsyncMock()

    return pool, conn


def _make_fake_cache():
    cache = AsyncMock()
    cache.get_prediction = AsyncMock(return_value=None)
    cache.set_prediction = AsyncMock()
    cache.delete_prediction = AsyncMock()
    return cache


@pytest.fixture
def fake_pool():
    return _make_fake_pool()


@pytest.fixture
def fake_cache():
    return _make_fake_cache()


@pytest_asyncio.fixture
async def client(ml_model):
    from main import app
    from clients.kafka import kafka_producer

    pool, conn = _make_fake_pool()

    account_row = {"id": 1, "login": "admin", "password": "admin", "is_blocked": False}
    conn.fetchrow = AsyncMock(return_value=account_row)

    app.state.db_pool = pool
    app.state.cache = _make_fake_cache()
    app.state.model = ml_model
    app.state.kafka_started = False

    kafka_producer._producer = AsyncMock()
    kafka_producer._producer.send_and_wait = AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        auth = AuthService()
        token = auth.create_token(1)
        ac.cookies.set("access_token", token)
        yield ac
