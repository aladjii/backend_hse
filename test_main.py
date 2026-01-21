# pytest test_main.py

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# проверка положительного результата
def test_predict_verified_seller():
    payload = {
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 101,
        "name": "iPhone 15",
        "description": "New phone",
        "category": 1,
        "images_qty": 0
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is True

# проверка положительного 
def test_predict_unverified_with_images():
    payload = {
        "seller_id": 2,
        "is_verified_seller": False,
        "item_id": 102,
        "name": "Laptop",
        "description": "Used laptop",
        "category": 2,
        "images_qty": 3
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is True

# проверка отрицательного 
def test_predict_unverified_no_images():
    payload = {
        "seller_id": 3,
        "is_verified_seller": False,
        "item_id": 103,
        "name": "Table",
        "description": "Wooden table",
        "category": 3,
        "images_qty": 0
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() is False

# проверка валидации типов (передаем строку вместо числа в seller_id)
def test_predict_validation_error_type():
    payload = {
        "seller_id": "not_an_int", 
        "is_verified_seller": True,
        "item_id": 104,
        "name": "Test",
        "description": "Test",
        "category": 4,
        "images_qty": 1
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422 # Unprocessable Entity

# проверка обязательных аргументов (отсутствует item_id)
def test_predict_missing_fields():
    payload = {
        "seller_id": 1,
        "is_verified_seller": True,
        "name": "Test",
        "description": "Test",
        "category": 4,
        "images_qty": 1
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

# проверка валидации отрицательного количества фото
def test_predict_negative_images():
    payload = {
        "seller_id": 1,
        "is_verified_seller": False,
        "item_id": 105,
        "name": "Test",
        "description": "Test",
        "category": 4,
        "images_qty": -5
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 422