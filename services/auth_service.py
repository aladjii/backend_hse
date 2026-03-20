from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

SECRET_KEY = "secret"
ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 24


class AuthService:
    def create_token(self, account_id: int) -> str:
        payload = {
            "sub": str(account_id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def verify_token(self, token: str) -> int:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return int(payload["sub"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
