# Download pgvector
$url = "https://github.com/pgvector/pgvector/releases/download/v0.4.4/pgvector-v0.4.4-pg12-windows-x64.zip"
$output = "$env:TEMP\pgvector.zip"
$pgvectorDir = "$env:TEMP\pgvector"

# Create temp directory
New-Item -ItemType Directory -Force -Path $pgvectorDir

# Download the file
Invoke-WebRequest -Uri $url -OutFile $output

# Extract the zip file
Expand-Archive -Path $output -DestinationPath $pgvectorDir -Force

# Copy files to PostgreSQL directory
$pgDir = "C:\Program Files\PostgreSQL\12"
Copy-Item "$pgvectorDir\bin\*" "$pgDir\bin" -Force
Copy-Item "$pgvectorDir\lib\*" "$pgDir\lib" -Force
Copy-Item "$pgvectorDir\share\extension\*" "$pgDir\share\extension" -Force

# Clean up
Remove-Item $output -Force
Remove-Item $pgvectorDir -Recurse -Force

Write-Host "pgvector installation completed!" 