import requests

print("Testing login endpoint...")
try:
    url = "http://localhost:8001/auth/login"
    data = {
        "username": "testuser", 
        "password": "password123"
    }
    
    response = requests.post(
        url, 
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("Login successful!")
        print(response.json())
    else:
        print("Login failed.")
        
except Exception as e:
    print(f"Error: {e}")
    
print("Press Enter to exit...")
input() 