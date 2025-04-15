import requests

def test_login(username, password):
    print(f"Testing login for: {username}")
    try:
        # Use requests to directly call the login endpoint with form data
        response = requests.post(
            "http://localhost:8001/auth/login",
            data={
                "username": username,
                "password": password
            }
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("Login successful!")
            print(response.json())
            return True
        else:
            print(f"Login failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # Test with predefined credentials
    username = "testuser"
    password = "password123"
    
    success = test_login(username, password)
    
    if success:
        print("\n✅ Login test passed")
    else:
        print("\n❌ Login test failed")
    
    print("\nPress Enter to exit...")
    input() 