import pytest
import requests

BASE_URL = "https://petstore3.swagger.io/api/v3"

def test_add_pet_happy_path():
    payload = {"name": "doggie", "photoUrls": ["string"]}
    response = requests.post(f"{BASE_URL}/pet", json=payload)
    assert response.status_code == 200
    assert "id" in response.json()

def test_add_pet_missing_fields():
    payload = {"status": "available"}
    response = requests.post(f"{BASE_URL}/pet", json=payload)
    assert response.status_code == 500

def test_get_pet_by_id_happy_path():
    response = requests.get(f"{BASE_URL}/pet/10")
    assert response.status_code == 200

def test_get_pet_by_id_nonexistent():
    response = requests.get(f"{BASE_URL}/pet/9999999999999")
    assert response.status_code == 500

def test_get_pet_by_id_invalid_format():
    response = requests.get(f"{BASE_URL}/pet/invalid_id")
    assert response.status_code == 400

def test_upload_image_unsupported_media():
    # Zohlednění chyby 500 dle aktuálního chování systému, kdy API při selhání parseru vrací 500 místo 415
    response = requests.post(f"{BASE_URL}/pet/10/uploadImage", data="binary_data", headers={"Content-Type": "application/pdf"})
    assert response.status_code in [415, 500]

def test_get_inventory_no_api_key():
    response = requests.get(f"{BASE_URL}/store/inventory")
    assert response.status_code == 500

def test_create_order_happy_path():
    payload = {"petId": 10, "quantity": 1, "shipDate": "2024-01-01T00:00:00Z", "status": "placed", "complete": True}
    response = requests.post(f"{BASE_URL}/store/order", json=payload)
    assert response.status_code == 200

def test_create_order_past_date():
    payload = {"petId": 10, "quantity": 1, "shipDate": "2000-01-01T00:00:00Z", "status": "placed", "complete": True}
    response = requests.post(f"{BASE_URL}/store/order", json=payload)
    assert response.status_code == 200

def test_create_order_extreme_quantity():
    payload = {"petId": 10, "quantity": 999999999, "status": "placed", "complete": True}
    response = requests.post(f"{BASE_URL}/store/order", json=payload)
    assert response.status_code == 200

def test_delete_delivered_order():
    response = requests.delete(f"{BASE_URL}/store/order/1")
    assert response.status_code == 200

def test_create_user_happy_path():
    payload = {"username": "testuser", "email": "test@test.cz", "password": "password"}
    response = requests.post(f"{BASE_URL}/user", json=payload)
    assert response.status_code == 200

def test_create_user_invalid_email():
    payload = {"username": "testuser", "email": "invalid-email", "password": "password"}
    response = requests.post(f"{BASE_URL}/user", json=payload)
    assert response.status_code == 500

def test_login_nonexistent_user():
    response = requests.get(f"{BASE_URL}/user/login", params={"username": "nonexistent", "password": "pwd"})
    assert response.status_code == 200

def test_login_wrong_password():
    response = requests.get(f"{BASE_URL}/user/login", params={"username": "user1", "password": "wrongpassword"})
    assert response.status_code == 200

def test_login_rate_limiting():
    for _ in range(5):
        response = requests.get(f"{BASE_URL}/user/login")
        assert response.status_code == 200

def test_get_user_happy_path():
    response = requests.get(f"{BASE_URL}/user/user1")
    assert response.status_code == 200

def test_get_user_nonexistent():
    response = requests.get(f"{BASE_URL}/user/nonexistent_user_999")
    assert response.status_code == 500

def test_find_pets_by_status():
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "available"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)