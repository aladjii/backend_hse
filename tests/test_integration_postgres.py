"""Integration tests for PostgreSQL repositories.

Requires a running PostgreSQL instance.
Run: pytest -m integration
"""
import os

import asyncpg
import pytest
import pytest_asyncio

from services import repositories
from services.account_repository import (
    block_account,
    create_account,
    delete_account,
    get_account_by_id,
    get_account_by_login_password,
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/moderation",
)

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def pool():
    p = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)
    yield p
    await p.close()


@pytest_asyncio.fixture(autouse=True)
async def cleanup(pool):
    yield
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM moderation_results")
        await conn.execute("DELETE FROM ads")
        await conn.execute("DELETE FROM users WHERE username != 'test_seller'")
        await conn.execute("DELETE FROM account WHERE login != 'admin'")


class TestUserRepository:
    @pytest.mark.asyncio
    async def test_create_and_get_user(self, pool):
        uid = await repositories.create_user(pool, "integ_user", True)
        user = await repositories.get_user_by_id(pool, uid)
        assert user is not None
        assert user["username"] == "integ_user"
        assert user["is_verified"] is True


class TestAdRepository:
    @pytest.mark.asyncio
    async def test_create_and_get_ad(self, pool):
        uid = await repositories.create_user(pool, "ad_seller", False)
        ad_id = await repositories.create_ad(pool, 9999, uid, "Test Ad", "desc", 5, 3)
        ad = await repositories.get_ad_by_item_id(pool, 9999)
        assert ad is not None
        assert ad["name"] == "Test Ad"
        assert ad["seller_id"] == uid

    @pytest.mark.asyncio
    async def test_delete_ad(self, pool):
        uid = await repositories.create_user(pool, "del_seller", False)
        await repositories.create_ad(pool, 8888, uid, "Del Ad", "", 1, 0)
        deleted = await repositories.delete_ad_by_item_id(pool, 8888)
        assert deleted is True
        assert await repositories.get_ad_by_item_id(pool, 8888) is None


class TestModerationRepository:
    @pytest.mark.asyncio
    async def test_create_and_complete_moderation(self, pool):
        uid = await repositories.create_user(pool, "mod_seller", True)
        ad_id = await repositories.create_ad(pool, 7777, uid, "Mod Ad", "d", 2, 1)
        task_id = await repositories.create_moderation_result(pool, ad_id)

        result = await repositories.get_moderation_result(pool, task_id)
        assert result["status"] == "pending"

        await repositories.update_moderation_result_completed(pool, task_id, False, 0.15)
        result = await repositories.get_moderation_result(pool, task_id)
        assert result["status"] == "completed"
        assert result["is_violation"] is False
        assert abs(result["probability"] - 0.15) < 1e-6

    @pytest.mark.asyncio
    async def test_mark_failed(self, pool):
        uid = await repositories.create_user(pool, "fail_seller", True)
        ad_id = await repositories.create_ad(pool, 6666, uid, "Fail Ad", "d", 1, 0)
        task_id = await repositories.create_moderation_result(pool, ad_id)

        await repositories.update_moderation_result_failed(pool, task_id, "timeout")
        result = await repositories.get_moderation_result(pool, task_id)
        assert result["status"] == "failed"
        assert result["error_message"] == "timeout"


class TestAccountRepository:
    @pytest.mark.asyncio
    async def test_create_and_auth(self, pool):
        aid = await create_account(pool, "testlogin", "testpass")
        acc = await get_account_by_login_password(pool, "testlogin", "testpass")
        assert acc is not None
        assert acc["id"] == aid

    @pytest.mark.asyncio
    async def test_block_account(self, pool):
        aid = await create_account(pool, "blockme", "pass")
        await block_account(pool, aid)
        acc = await get_account_by_id(pool, aid)
        assert acc["is_blocked"] is True

    @pytest.mark.asyncio
    async def test_delete_account(self, pool):
        aid = await create_account(pool, "deleteme", "pass")
        assert await delete_account(pool, aid) is True
        assert await get_account_by_id(pool, aid) is None
