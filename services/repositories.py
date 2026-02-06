from typing import Optional, Dict, Any

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
