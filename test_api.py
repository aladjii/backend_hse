import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import MagicMock

client = TestClient(app)

@pytest.fixture(autouse=True)
def ensure_model():
    with TestClient(app):
        yield

def test_predict_success_violation():
    payload = {
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 101,
        "name": "Kekek",
        "description": "kakaka",
        "category": 1,
        "images_qty": 0
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "probability" in data
    assert isinstance(data["is_violation"], bool)

def test_predict_success_clean():
    payload = {
        "seller_id": 2,
        "is_verified_seller": True,
        "item_id": 102,
        "name": "Cabacaba",
        "description": "Abacababab " * 50,
        "category": 10,
        "images_qty": 5
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200

def test_validation_error_types():
    payload = {
        "seller_id": "not_int",
        "is_verified_seller": True,
        "item_id": 103,
        "name": "Test",
        "description": "Test",
        "category": 1,
        "images_qty": 1
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

def test_validation_error_constraints():
    payload = {
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 104,
        "name": "Test",
        "description": "Test",
        "category": 1,
        "images_qty": -5
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

def test_model_unavailable():
    original_model = app.state.model

    try:
        app.state.model = None

        payload = {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 105,
            "name": "Test",
            "description": "Test",
            "category": 1,
            "images_qty": 1
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 503
        assert response.json()["detail"] == "Service Unavailable: model not loaded"

    finally:
        app.state.model = original_model

def test_internal_server_error():
    original_model = app.state.model

    try:
        mock_model = MagicMock()
        mock_model.predict_proba.side_effect = Exception("Sklearn unexpected error")
        app.state.model = mock_model

        payload = {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 106,
            "name": "Test",
            "description": "Test",
            "category": 1,
            "images_qty": 1
        }
        response = client.post("/predict", json=payload)
        assert response.status_code == 500
        assert "Internal Server Error" in response.json()["detail"]

    finally:
        app.state.model = original_model
