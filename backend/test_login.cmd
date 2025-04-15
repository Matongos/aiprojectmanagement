@echo off
echo Testing login endpoint...
curl -X POST http://localhost:8001/auth/login -H "Content-Type: application/x-www-form-urlencoded" -d "username=testuser&password=password123"
pause 