import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from metrics import DB_QUERY_DURATION


def _observe(query_type: str, start: float) -> None:
    DB_QUERY_DURATION.labels(query_type=query_type).observe(time.time() - start)


async def create_user(pool, username: str, is_verified: bool = False) -> int:
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO users (username, is_verified) VALUES ($1, $2) RETURNING id",
            username,
            is_verified,
        )
    _observe("insert", start)
    return row["id"]


async def get_user_by_id(pool, user_id: int) -> Optional[Dict[str, Any]]:
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, is_verified, created_at FROM users WHERE id = $1",
            user_id,
        )
    _observe("select", start)
    return dict(row) if row else None


async def create_ad(
    pool,
    item_id: int,
    seller_id: int,
    name: str,
    description: str,
    category: int,
    images_qty: int = 0,
) -> int:
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO ads (item_id, seller_id, name, description, category, images_qty)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            item_id,
            seller_id,
            name,
            description,
            category,
            images_qty,
        )
    _observe("insert", start)
    return row["id"]


async def get_ad_by_item_id(pool, item_id: int) -> Optional[Dict[str, Any]]:
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, item_id, seller_id, name, description, category, "
            "images_qty, created_at, is_closed FROM ads WHERE item_id = $1",
            item_id,
        )
    _observe("select", start)
    return dict(row) if row else None


async def get_ad_by_id(pool, ad_id: int) -> Optional[Dict[str, Any]]:
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, item_id, seller_id, name, description, category, "
            "images_qty, created_at, is_closed FROM ads WHERE id = $1",
            ad_id,
        )
    _observe("select", start)
    return dict(row) if row else None


async def delete_ad_by_item_id(pool, item_id: int) -> bool:
    start = time.time()
    async with pool.acquire() as conn:
        async with conn.transaction():
            res = await conn.execute(
                "DELETE FROM ads WHERE item_id = $1", item_id
            )
    _observe("delete", start)
    return res == "DELETE 1"


async def create_moderation_result(pool, item_id: int) -> int:
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO moderation_results (item_id, status) "
            "VALUES ($1, 'pending') RETURNING id",
            item_id,
        )
    _observe("insert", start)
    return row["id"]


async def get_moderation_result(pool, task_id: int) -> Optional[Dict[str, Any]]:
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, item_id, status, is_violation, probability, "
            "error_message, created_at, processed_at "
            "FROM moderation_results WHERE id = $1",
            task_id,
        )
    _observe("select", start)
    return dict(row) if row else None


async def get_latest_moderation_result_by_ad_id(
    pool, ad_id: int
) -> Optional[Dict[str, Any]]:
    start = time.time()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, status, is_violation, probability "
            "FROM moderation_results WHERE item_id = $1 "
            "ORDER BY created_at DESC LIMIT 1",
            ad_id,
        )
    _observe("select", start)
    return dict(row) if row else None


async def update_moderation_result_completed(
    pool, task_id: int, is_violation: bool, probability: float
) -> None:
    start = time.time()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE moderation_results "
            "SET status = 'completed', is_violation = $2, "
            "probability = $3, processed_at = $4 "
            "WHERE id = $1",
            task_id,
            is_violation,
            probability,
            datetime.now(timezone.utc),
        )
    _observe("update", start)


async def update_moderation_result_failed(
    pool, task_id: int, error_message: str
) -> None:
    start = time.time()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE moderation_results "
            "SET status = 'failed', error_message = $2, processed_at = $3 "
            "WHERE id = $1",
            task_id,
            error_message,
            datetime.now(timezone.utc),
        )
    _observe("update", start)
