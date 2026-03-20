from fastapi import HTTPException, Request

from services.account_repository import get_account_by_id
from services.auth_service import AuthService

auth_service = AuthService()


async def get_current_account(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authorized")

    account_id = auth_service.verify_token(token)

    pool = request.app.state.db_pool
    account = await get_account_by_id(pool, account_id)
    if not account:
        raise HTTPException(status_code=401, detail="Account not found")
    if account["is_blocked"]:
        raise HTTPException(status_code=403, detail="Account blocked")

    return account
