from services.auth_service import AuthService


def test_create_and_verify_token():

    service = AuthService()

    token = service.create_token(10)

    user_id = service.verify_token(token)

    assert user_id == 10