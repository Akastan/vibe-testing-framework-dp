import pytest
import requests

BASE_URL = "https://petstore3.swagger.io/api/v3"

def test_add_new_pet_successfully():
    payload = {
        "id": 99999,
        "name": "doggie",
        "photoUrls": ["https://example.com/photo.jpg"],
        "status": "available"
    }
    response = requests.post(f"{BASE_URL}/pet", json=payload)
    # Status 200 je očekávaný dle specifikace, pokud API vrací 500, znamená to, že vyžaduje 
    # kompletnější objekt nebo specifické formátování dle interních pravidel serveru.
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["name"] == "doggie"

def test_add_pet_missing_required_fields():
    payload = {"name": "incomplete"} # Chybí photoUrls
    response = requests.post(f"{BASE_URL}/pet", json=payload)
    assert response.status_code == 422

def test_get_existing_pet_by_id():
    # Nejprve vytvoříme, abychom měli co číst
    pet_id = 12345
    requests.post(f"{BASE_URL}/pet", json={"id": pet_id, "name": "test", "photoUrls": ["url"]})
    response = requests.get(f"{BASE_URL}/pet/{pet_id}")
    assert response.status_code == 200
    assert response.json()["id"] == pet_id

def test_get_non_existent_pet():
    response = requests.get(f"{BASE_URL}/pet/9999999999")
    assert response.status_code == 404

def test_get_pet_invalid_id_format():
    response = requests.get(f"{BASE_URL}/pet/abc")
    assert response.status_code == 404 # V Swagger Petstore v3 vrací cesta /pet/abc 404 místo 400

def test_find_pets_by_valid_status():
    # Status musí být v query parametru, nikoliv prázdný
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "available"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_find_pets_invalid_status():
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": "invalid_val"})
    assert response.status_code == 400

def test_upload_image_for_valid_pet():
    pet_id = 1
    files = {'file': ('test.jpg', b'fake_image_content', 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/pet/{pet_id}/uploadImage", files=files)
    assert response.status_code == 200

def test_create_valid_order():
    payload = {"petId": 1, "quantity": 1, "status": "placed", "complete": True}
    response = requests.post(f"{BASE_URL}/store/order", json=payload)
    assert response.status_code == 200

def test_create_order_invalid_data():
    response = requests.post(f"{BASE_URL}/store/order", json="not_a_json")
    assert response.status_code in [400, 422]

def test_delete_order_boundary():
    # Dle specifikace > 1000 generuje chybu, zkusíme 9999
    response = requests.delete(f"{BASE_URL}/store/order/9999")
    # API vrací 400 pro neplatná ID
    assert response.status_code == 400

def test_create_valid_user():
    payload = {"username": "testuser", "firstName": "John", "lastName": "Doe"}
    response = requests.post(f"{BASE_URL}/user", json=payload)
    assert response.status_code == 200

def test_login_valid_credentials():
    response = requests.get(f"{BASE_URL}/user/login", params={"username": "user1", "password": "123"})
    assert response.status_code == 200
    assert "X-Expires-After" in response.headers

def test_login_missing_credentials():
    response = requests.get(f"{BASE_URL}/user/login")
    assert response.status_code == 400

def test_get_existing_user():
    response = requests.get(f"{BASE_URL}/user/user1")
    assert response.status_code == 200

def test_get_non_existent_user():
    response = requests.get(f"{BASE_URL}/user/nonexistentuser123")
    assert response.status_code == 404

def test_bulk_create_users():
    payload = [{"username": "u1"}, {"username": "u2"}]
    response = requests.post(f"{BASE_URL}/user/createWithList", json=payload)
    assert response.status_code == 200

def test_update_pet_status():
    payload = {"id": 1, "name": "doggie", "photoUrls": ["url"], "status": "sold"}
    response = requests.put(f"{BASE_URL}/pet", json=payload)
    assert response.status_code == 200

def test_update_non_existent_pet():
    payload = {"id": 99999999, "name": "ghost", "photoUrls": ["url"]}
    response = requests.put(f"{BASE_URL}/pet", json=payload)
    assert response.status_code == 404

def test_get_inventory_without_api_key():
    response = requests.get(f"{BASE_URL}/store/inventory")
    # Pokud není přítomen api_key, server by měl vrátit 401
    assert response.status_code == 401