def test_login_success(client, mocker):

    mock_repo = mocker.patch(
        "routes.auth.get_account_by_login_password"
    )

    mock_repo.return_value = {
        "id": 1,
        "login": "test",
        "password": "123",
        "is_blocked": False
    }

    res = client.post("/login", json={
        "login": "test",
        "password": "123"
    })

    assert res.status_code == 200
    assert "access_token" in res.cookies