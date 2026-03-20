import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException

from services.auth_service import ALGORITHM, SECRET_KEY, AuthService


class TestAuthService:
    def test_create_and_verify_roundtrip(self, auth_service):
        token = auth_service.create_token(42)
        account_id = auth_service.verify_token(token)
        assert account_id == 42

    def test_different_ids(self, auth_service):
        for uid in [1, 100, 999]:
            token = auth_service.create_token(uid)
            assert auth_service.verify_token(token) == uid

    def test_expired_token_raises_401(self, auth_service):
        payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_invalid_token_raises_401(self, auth_service):
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self, auth_service):
        token = auth_service.create_token(1)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException):
            auth_service.verify_token(tampered)
