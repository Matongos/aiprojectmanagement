import requests
import json

# Test configuration
BASE_URL = "http://localhost:8001"
TEST_USER = {
    "username": "testuser",
    "password": "testpassword123",
    "email": "test@example.com",
    "full_name": "Test User"
}

def test_profile_update():
    print("\n=== Testing Profile Update ===")
    
    # Step 1: Login to get token
    print("\n1. Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": TEST_USER["username"], "password": TEST_USER["password"]}
    )
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        print(login_response.text)
        return
    
    token = login_response.json()["access_token"]
    print("Login successful!")
    
    # Step 2: Update profile
    print("\n2. Updating profile...")
    update_data = {
        "full_name": "Updated Test User",
        "email": "updated@example.com",
        "current_password": TEST_USER["password"],
        "new_password": "newpassword123"
    }
    
    update_response = requests.patch(
        f"{BASE_URL}/users/me/profile",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if update_response.status_code != 200:
        print(f"Profile update failed: {update_response.status_code}")
        print(update_response.text)
        return
    
    print("Profile update successful!")
    print("Updated data:", json.dumps(update_response.json(), indent=2))
    
    # Step 3: Verify changes
    print("\n3. Verifying changes...")
    profile_response = requests.get(
        f"{BASE_URL}/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if profile_response.status_code != 200:
        print(f"Profile fetch failed: {profile_response.status_code}")
        print(profile_response.text)
        return
    
    profile_data = profile_response.json()
    print("Current profile:", json.dumps(profile_data, indent=2))
    
    # Step 4: Test login with new password
    print("\n4. Testing login with new password...")
    new_login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": TEST_USER["username"], "password": "newpassword123"}
    )
    
    if new_login_response.status_code != 200:
        print(f"Login with new password failed: {new_login_response.status_code}")
        print(new_login_response.text)
        return
    
    print("Login with new password successful!")
    
    print("\n=== Profile Update Test Complete ===")

if __name__ == "__main__":
    test_profile_update() 