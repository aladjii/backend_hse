from fastapi import APIRouter, Request, Response, HTTPException
from pydantic import BaseModel

from services.auth_service import AuthService
from services.account_repository import get_account_by_login_password

router = APIRouter()

auth_service = AuthService()


class LoginRequest(BaseModel):
    login: str
    password: str


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response):

    pool = request.app.state.db_pool

    account = await get_account_by_login_password(
        pool,
        payload.login,
        payload.password
    )

    if not account:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if account["is_blocked"]:
        raise HTTPException(status_code=403, detail="Account blocked")

    token = auth_service.create_token(account["id"])

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True
    )

    return {"message": "ok"}