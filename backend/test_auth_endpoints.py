import requests
import json

# API base URL
API_URL = "http://localhost:8001"

def test_register():
    """Test the user registration endpoint."""
    print("\n--- Testing User Registration ---")
    
    # Registration data
    register_data = {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "testpassword"
    }
    
    # Make request
    try:
        response = requests.post(
            f"{API_URL}/auth/register",
            json=register_data
        )
        
        # Print response details
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Registration successful:")
            print(f"User ID: {data.get('user_id')}")
            print(f"Username: {data.get('username')}")
            print(f"Email: {data.get('email')}")
            print(f"Token Type: {data.get('token_type')}")
            print(f"Access Token: {data.get('access_token')[:15]}...") # Show just the start of the token
            
            # Save token for login test
            return data.get('access_token')
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None

def test_login(username="testuser", password="testpassword"):
    """Test the login endpoint."""
    print("\n--- Testing Login ---")
    
    # Create login form data
    login_data = {
        "username": username,
        "password": password
    }
    
    # Make request
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            data=login_data
        )
        
        # Print response details
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Login successful:")
            print(f"User ID: {data.get('user_id')}")
            print(f"Username: {data.get('username')}")
            print(f"Email: {data.get('email')}")
            print(f"Token Type: {data.get('token_type')}")
            print(f"Access Token: {data.get('access_token')[:15]}...") # Show just the start of the token
            
            return data.get('access_token')
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None

def test_me_endpoint(token):
    """Test the /me endpoint with an authentication token."""
    print("\n--- Testing /me Endpoint ---")
    
    if not token:
        print("No token available, skipping /me endpoint test")
        return
    
    # Set authorization header
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Make request
    try:
        response = requests.get(
            f"{API_URL}/auth/me",
            headers=headers
        )
        
        # Print response details
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("User data retrieved successfully:")
            print(json.dumps(data, indent=2))
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception occurred: {str(e)}")

if __name__ == "__main__":
    # Test registration
    token = test_register()
    
    # Test login
    if not token:
        token = test_login()
    
    # Test /me endpoint
    test_me_endpoint(token) 