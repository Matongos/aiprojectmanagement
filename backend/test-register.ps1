$registrationData = @{
    username = "testuser123"
    password = "testpassword123"
    email = "test123@example.com"
    full_name = "Test User 123"
}

$jsonData = $registrationData | ConvertTo-Json

$headers = @{
    "Content-Type" = "application/json"
}

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8002/auth/register" -Method Post -Body $jsonData -Headers $headers
    Write-Host "Registration successful!"
    Write-Host "User ID: $($response.user_id)"
    Write-Host "Username: $($response.username)"
    Write-Host "Email: $($response.email)"
    Write-Host "Token Type: $($response.token_type)"
    Write-Host "Access Token: $($response.access_token.Substring(0, 15))..."
} catch {
    Write-Host "Error: $_"
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "Error Details: $($_.ErrorDetails.Message)"
} 