import pytest
import requests
import uuid

BASE_URL = "https://petstore3.swagger.io/api/v3"

@pytest.fixture
def api_headers():
    return {"accept": "application/json", "Content-Type": "application/json"}

def test_add_new_valid_pet(api_headers):
    payload = {
        "id": 123456789,
        "name": "doggie",
        "photoUrls": ["string"],
        "status": "available"
    }
    response = requests.post(f"{BASE_URL}/pet", json=payload, headers=api_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "doggie"

def test_add_pet_missing_required_fields(api_headers):
    payload = {"status": "available"}
    response = requests.post(f"{BASE_URL}/pet", json=payload, headers=api_headers)
    assert response.status_code in [400, 422]

def test_get_pet_existing(api_headers):
    # Ensure pet exists first
    pet_id = 987654
    requests.post(f"{BASE_URL}/pet", json={"id": pet_id, "name": "tester", "photoUrls": ["url"]}, headers=api_headers)
    
    response = requests.get(f"{BASE_URL}/pet/{pet_id}", headers=api_headers)
    assert response.status_code == 200
    assert response.json()["id"] == pet_id

def test_get_pet_non_existent(api_headers):
    response = requests.get(f"{BASE_URL}/pet/99999999999", headers=api_headers)
    assert response.status_code == 404

def test_get_pet_invalid_id(api_headers):
    response = requests.get(f"{BASE_URL}/pet/invalid_id", headers=api_headers)
    assert response.status_code == 400

def test_find_pets_by_status_valid(api_headers):
    response = requests.get(f"{BASE_URL}/pet/findByStatus?status=available", headers=api_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_find_pets_by_status_invalid(api_headers):
    response = requests.get(f"{BASE_URL}/pet/findByStatus?status=unknown", headers=api_headers)
    assert response.status_code == 400

def test_upload_image_valid(api_headers):
    pet_id = 1
    files = {'file': ('test.jpg', b'fake_image_content', 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/pet/{pet_id}/uploadImage", files=files)
    assert response.status_code == 200

def test_upload_image_non_existent(api_headers):
    files = {'file': ('test.jpg', b'content', 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/pet/99999999/uploadImage", files=files)
    assert response.status_code == 404

def test_place_order_valid(api_headers):
    payload = {"petId": 1, "quantity": 1, "status": "placed", "complete": True}
    response = requests.post(f"{BASE_URL}/store/order", json=payload, headers=api_headers)
    assert response.status_code == 200

def test_place_order_invalid_quantity(api_headers):
    payload = {"petId": 1, "quantity": "invalid", "status": "placed"}
    response = requests.post(f"{BASE_URL}/store/order", json=payload, headers=api_headers)
    assert response.status_code in [400, 422]

def test_delete_order_valid(api_headers):
    order_id = 5
    response = requests.delete(f"{BASE_URL}/store/order/{order_id}", headers=api_headers)
    assert response.status_code in [200, 404]

def test_delete_order_non_existent(api_headers):
    response = requests.delete(f"{BASE_URL}/store/order/99999", headers=api_headers)
    assert response.status_code == 404

def test_create_user(api_headers):
    user = {"username": f"user_{uuid.uuid4().hex[:6]}", "firstName": "John"}
    response = requests.post(f"{BASE_URL}/user", json=user, headers=api_headers)
    assert response.status_code == 200

def test_user_login_valid(api_headers):
    response = requests.get(f"{BASE_URL}/user/login?username=user1&password=password")
    assert response.status_code == 200

def test_user_login_wrong_credentials(api_headers):
    response = requests.get(f"{BASE_URL}/user/login?username=nonexistent&password=wrong")
    assert response.status_code == 400

def test_get_non_existing_user(api_headers):
    response = requests.get(f"{BASE_URL}/user/ghost_user_123", headers=api_headers)
    assert response.status_code == 404

def test_get_user_empty_username(api_headers):
    response = requests.get(f"{BASE_URL}/user/%20", headers=api_headers)
    assert response.status_code in [400, 404]

def test_update_non_existent_pet(api_headers):
    payload = {"id": 888888, "name": "Ghost", "photoUrls": ["url"]}
    response = requests.put(f"{BASE_URL}/pet", json=payload, headers=api_headers)
    assert response.status_code == 404

def test_update_pet_malformed_json(api_headers):
    response = requests.put(f"{BASE_URL}/pet", data="not-a-json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400