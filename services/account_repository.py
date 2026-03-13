from typing import Optional, Dict, Any


async def create_account(pool, login: str, password: str) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO account (login, password)
            VALUES ($1, $2)
            RETURNING id
            """,
            login,
            password,
        )
    return row["id"]


async def get_account_by_id(pool, account_id: int) -> Optional[Dict[str, Any]]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, login, password, is_blocked
            FROM account
            WHERE id = $1
            """,
            account_id,
        )
    return dict(row) if row else None


async def get_account_by_login_password(pool, login: str, password: str):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, login, password, is_blocked
            FROM account
            WHERE login = $1 AND password = $2
            """,
            login,
            password,
        )
    return dict(row) if row else None


async def block_account(pool, account_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE account
            SET is_blocked = TRUE
            WHERE id = $1
            """,
            account_id,
        )


async def delete_account(pool, account_id: int):
    async with pool.acquire() as conn:
        res = await conn.execute(
            "DELETE FROM account WHERE id=$1",
            account_id
        )
    return res == "DELETE 1"