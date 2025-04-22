# Test API endpoints
$baseUrl = "http://localhost:8003"
$token = $null

Write-Host "`n=== Testing Authentication ===" -ForegroundColor Green

# Test registration
Write-Host "`nTesting registration..." -ForegroundColor Yellow
$registerBody = @{
    username = "testuser"
    password = "testpass123"
    email = "test@example.com"
    full_name = "Test User"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/auth/register" -Method Post -Body $registerBody -ContentType "application/json"
    Write-Host "Registration successful!" -ForegroundColor Green
} catch {
    Write-Host "Registration failed: $_" -ForegroundColor Red
}

# Test login
Write-Host "`nTesting login..." -ForegroundColor Yellow
$loginBody = @{
    username = "testuser"
    password = "testpass123"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
    $token = $response.access_token
    Write-Host "Login successful! Token received." -ForegroundColor Green
} catch {
    Write-Host "Login failed: $_" -ForegroundColor Red
}

if ($token) {
    $headers = @{
        "Authorization" = "Bearer $token"
    }

    Write-Host "`n=== Testing User Endpoints ===" -ForegroundColor Green

    # Test get current user
    Write-Host "`nTesting get current user..." -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/users/me" -Method Get -Headers $headers
        Write-Host "Get current user successful!" -ForegroundColor Green
    } catch {
        Write-Host "Get current user failed: $_" -ForegroundColor Red
    }

    # Test get all users
    Write-Host "`nTesting get all users..." -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/users/" -Method Get -Headers $headers
        Write-Host "Get all users successful!" -ForegroundColor Green
    } catch {
        Write-Host "Get all users failed: $_" -ForegroundColor Red
    }

    Write-Host "`n=== Testing Role Endpoints ===" -ForegroundColor Green

    # Test create role
    Write-Host "`nTesting create role..." -ForegroundColor Yellow
    $roleBody = @{
        name = "test_role"
        description = "Test role description"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/roles/" -Method Post -Body $roleBody -Headers $headers -ContentType "application/json"
        Write-Host "Create role successful!" -ForegroundColor Green
        $roleId = $response.id
    } catch {
        Write-Host "Create role failed: $_" -ForegroundColor Red
    }

    # Test get all roles
    Write-Host "`nTesting get all roles..." -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/roles/" -Method Get -Headers $headers
        Write-Host "Get all roles successful!" -ForegroundColor Green
    } catch {
        Write-Host "Get all roles failed: $_" -ForegroundColor Red
    }

    # Test create permission
    Write-Host "`nTesting create permission..." -ForegroundColor Yellow
    $permissionBody = @{
        name = "test_permission"
        description = "Test permission description"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/roles/permissions" -Method Post -Body $permissionBody -Headers $headers -ContentType "application/json"
        Write-Host "Create permission successful!" -ForegroundColor Green
    } catch {
        Write-Host "Create permission failed: $_" -ForegroundColor Red
    }

    # Test get all permissions
    Write-Host "`nTesting get all permissions..." -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/roles/permissions" -Method Get -Headers $headers
        Write-Host "Get all permissions successful!" -ForegroundColor Green
    } catch {
        Write-Host "Get all permissions failed: $_" -ForegroundColor Red
    }
} 