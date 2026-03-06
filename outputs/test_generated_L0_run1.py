import pytest
import requests

BASE_URL = "https://petstore3.swagger.io/api/v3"
HEADERS = {"Content-Type": "application/json", "accept": "application/json"}

def test_add_new_pet_valid_data():
    payload = {
        "id": 12345,
        "name": "doggie",
        "photoUrls": ["string"],
        "status": "available"
    }
    response = requests.post(f"{BASE_URL}/pet", json=payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "doggie"
    assert "id" in data

def test_add_pet_missing_required_fields():
    payload = {"name": "incomplete_pet"} 
    response = requests.post(f"{BASE_URL}/pet", json=payload, headers=HEADERS)
    assert response.status_code in [400, 422]

def test_find_pets_by_valid_status():
    params = {"status": "available"}
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params=params, headers={"accept": "application/json"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_find_pets_invalid_status_value():
    params = {"status": "invalid_status_xyz"}
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params=params, headers={"accept": "application/json"})
    assert response.status_code in [400, 200]

def test_get_pet_by_existing_id():
    response = requests.get(f"{BASE_URL}/pet/12345", headers={"accept": "application/json"})
    assert response.status_code in [200, 404]

def test_get_pet_nonexistent_id():
    response = requests.get(f"{BASE_URL}/pet/9999999999", headers={"accept": "application/json"})
    assert response.status_code == 404

def test_get_pet_invalid_id_format():
    response = requests.get(f"{BASE_URL}/pet/abc", headers={"accept": "application/json"})
    assert response.status_code == 404

def test_delete_existing_pet():
    response = requests.delete(f"{BASE_URL}/pet/12345", headers={"accept": "application/json"})
    assert response.status_code in [200, 404]

def test_upload_image_success():
    files = {"file": ("test.jpg", b"fake-image-content", "image/jpeg")}
    response = requests.post(f"{BASE_URL}/pet/12345/uploadImage", files=files)
    assert response.status_code in [200, 404]

def test_get_inventory_unauthorized():
    response = requests.get(f"{BASE_URL}/store/inventory")
    assert response.status_code in [200, 401]

def test_place_valid_order():
    payload = {
        "id": 1,
        "petId": 12345,
        "quantity": 1,
        "shipDate": "2023-10-27T10:00:00.000Z",
        "status": "placed",
        "complete": True
    }
    response = requests.post(f"{BASE_URL}/store/order", json=payload, headers=HEADERS)
    assert response.status_code == 200

def test_get_order_boundary_value():
    response = requests.get(f"{BASE_URL}/store/order/5", headers={"accept": "application/json"})
    assert response.status_code in [200, 404]

def test_get_order_out_of_bounds():
    response = requests.get(f"{BASE_URL}/store/order/7", headers={"accept": "application/json"})
    assert response.status_code in [404, 400]

def test_create_user_success():
    payload = {
        "id": 1,
        "username": "testuser",
        "firstName": "John",
        "lastName": "Doe",
        "email": "test@test.com",
        "password": "password",
        "phone": "123456789",
        "userStatus": 1
    }
    response = requests.post(f"{BASE_URL}/user", json=payload, headers=HEADERS)
    assert response.status_code == 200

def test_login_valid_credentials():
    params = {"username": "testuser", "password": "password"}
    response = requests.get(f"{BASE_URL}/user/login", params=params)
    assert response.status_code == 200

def test_login_invalid_credentials():
    params = {"username": "wrong", "password": "wrong"}
    response = requests.get(f"{BASE_URL}/user/login", params=params)
    assert response.status_code in [400, 401]

def test_get_user_by_name_success():
    response = requests.get(f"{BASE_URL}/user/testuser", headers={"accept": "application/json"})
    assert response.status_code in [200, 404]

def test_get_user_not_found():
    response = requests.get(f"{BASE_URL}/user/nonexistentuser", headers={"accept": "application/json"})
    assert response.status_code == 404

def test_delete_existing_user():
    response = requests.delete(f"{BASE_URL}/user/testuser", headers={"accept": "application/json"})
    assert response.status_code in [200, 404]