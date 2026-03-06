import pytest
import requests

BASE_URL = "https://petstore3.swagger.io/api/v3"

def test_add_valid_pet():
    url = f"{BASE_URL}/pet"
    data = {
        "id": 12345,
        "name": "doggie",
        "photoUrls": ["string"],
        "status": "available"
    }
    response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    assert response.json()["name"] == "doggie"

def test_add_pet_invalid_schema():
    url = f"{BASE_URL}/pet"
    data = {"invalid": "schema"}
    response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    assert response.status_code == 500

def test_get_pet_by_invalid_id_format():
    url = f"{BASE_URL}/pet/invalid_id"
    response = requests.get(url)
    assert response.status_code == 400

def test_get_nonexistent_pet():
    url = f"{BASE_URL}/pet/9999999999"
    response = requests.get(url)
    assert response.status_code == 500

def test_upload_image_unsupported_media():
    url = f"{BASE_URL}/pet/12345/uploadImage"
    response = requests.post(url, data="binary_data", headers={"Content-Type": "application/octet-stream"})
    assert response.status_code in [415, 500]

def test_find_by_valid_status():
    url = f"{BASE_URL}/pet/findByStatus"
    params = {"status": "available"}
    response = requests.get(url, params=params)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_inventory_without_api_key():
    url = f"{BASE_URL}/store/inventory"
    response = requests.get(url)
    assert response.status_code == 500

def test_place_order_extreme_quantity():
    url = f"{BASE_URL}/store/order"
    data = {"id": 1, "petId": 12345, "quantity": 999999999, "status": "placed"}
    response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    assert response.status_code == 200

def test_place_order_past_date():
    url = f"{BASE_URL}/store/order"
    data = {"id": 2, "petId": 12345, "shipDate": "2000-01-01T00:00:00.000Z", "status": "placed"}
    response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    assert response.status_code == 200

def test_delete_delivered_order():
    url = f"{BASE_URL}/store/order/1"
    response = requests.delete(url)
    assert response.status_code == 200

def test_create_user_invalid_data():
    url = f"{BASE_URL}/user"
    data = {"username": None}
    response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    assert response.status_code in [400, 500]

def test_login_with_wrong_credentials():
    url = f"{BASE_URL}/user/login"
    params = {"username": "nonexistent", "password": "wrongpassword"}
    response = requests.get(url, params=params)
    assert response.status_code == 200

def test_login_unlimited_requests():
    url = f"{BASE_URL}/user/login"
    params = {"username": "user1", "password": "password"}
    for _ in range(3):
        response = requests.get(url, params=params)
        assert response.status_code == 200

def test_get_nonexistent_user():
    url = f"{BASE_URL}/user/ghost_user_999"
    response = requests.get(url)
    assert response.status_code == 500

def test_delete_user_not_found():
    url = f"{BASE_URL}/user/ghost_user_999"
    response = requests.delete(url)
    assert response.status_code == 500

def test_find_by_tags_missing():
    url = f"{BASE_URL}/pet/findByTags"
    response = requests.get(url)
    assert response.status_code == 500

def test_create_users_with_list_malformed():
    url = f"{BASE_URL}/user/createWithList"
    data = "not a list"
    response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    assert response.status_code in [400, 500]

def test_logout_successful():
    url = f"{BASE_URL}/user/logout"
    response = requests.get(url)
    assert response.status_code == 200

def test_update_user_invalid_format():
    url = f"{BASE_URL}/user/testuser"
    data = {"phone": 123456789}
    response = requests.put(url, json=data, headers={"Content-Type": "application/json"})
    assert response.status_code == 500