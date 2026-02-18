from typing import Optional, Dict, Any
from datetime import datetime, timezone


async def create_user(pool, username: str, is_verified: bool = False) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO users (username, is_verified) VALUES ($1, $2) RETURNING id",
            username, is_verified
        )
        return row["id"]

async def get_user_by_id(pool, user_id: int) -> Optional[Dict[str, Any]]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, username, is_verified, created_at FROM users WHERE id = $1", user_id)
        return dict(row) if row else None

async def create_ad(pool, item_id: int, seller_id: int, name: str, description: str, category: int, images_qty: int = 0) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO ads (item_id, seller_id, name, description, category, images_qty)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            item_id, seller_id, name, description, category, images_qty
        )
        return row["id"]

async def get_ad_by_item_id(pool, item_id: int) -> Optional[Dict[str, Any]]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, item_id, seller_id, name, description, category, images_qty, created_at FROM ads WHERE item_id = $1",
            item_id
        )
        return dict(row) if row else None


async def get_ad_by_id(pool, ad_id: int) -> Optional[Dict[str, Any]]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, item_id, seller_id, name, description, category, images_qty, created_at FROM ads WHERE id = $1",
            ad_id
        )
        return dict(row) if row else None


async def create_moderation_result(pool, item_id: int) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO moderation_results (item_id, status)
            VALUES ($1, 'pending')
            RETURNING id
            """,
            item_id
        )
        return row["id"]


async def get_moderation_result(pool, task_id: int) -> Optional[Dict[str, Any]]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, item_id, status, is_violation, probability, error_message, created_at, processed_at
            FROM moderation_results
            WHERE id = $1
            """,
            task_id
        )
        return dict(row) if row else None


async def update_moderation_result_completed(
    pool, task_id: int, is_violation: bool, probability: float
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE moderation_results
            SET status = 'completed',
                is_violation = $2,
                probability = $3,
                processed_at = $4
            WHERE id = $1
            """,
            task_id,
            is_violation,
            probability,
            datetime.now(timezone.utc),
        )


async def update_moderation_result_failed(pool, task_id: int, error_message: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE moderation_results
            SET status = 'failed',
                error_message = $2,
                processed_at = $3
            WHERE id = $1
            """,
            task_id,
            error_message,
            datetime.now(timezone.utc),
        )
