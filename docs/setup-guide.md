# Development Environment Setup Guide

This document provides detailed instructions for setting up the development environment for the AI-Enhanced Project Management System.

## Backend Setup

### Installing Python
1. Download Python 3.10+ from [python.org](https://www.python.org/downloads/)
2. Ensure Python and pip are added to your PATH during installation

### Setting Up the Python Environment
1. Open Command Prompt
2. Navigate to the project root directory
3. Create a virtual environment:
   ```
   python -m venv venv
   ```
4. Activate the virtual environment:
   ```
   venv\Scripts\activate
   ```
5. Install dependencies:
   ```
   cd backend
   pip install -r requirements.txt
   ```

### Installing and Configuring PostgreSQL
1. Download PostgreSQL from [postgresql.org](https://www.postgresql.org/download/)
2. Install PostgreSQL with default options (remember your password for the postgres user)
3. After installation, open pgAdmin (comes with PostgreSQL)
4. Create a new database named `projectmanagement`
5. Create a .env file in the project root with the following content (adjust as needed):
   ```
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password_here
   POSTGRES_DB=projectmanagement
   POSTGRES_SERVER=localhost
   POSTGRES_PORT=5432
   JWT_SECRET=your_secure_secret_here
   ENVIRONMENT=development
   LOG_LEVEL=DEBUG
   ```

### Running the Backend
1. With the virtual environment activated, run:
   ```
   python backend/main.py
   ```
2. The server will start on http://localhost:8001

## Frontend Setup (when implemented)

### Installing Node.js
1. Download Node.js LTS version from [nodejs.org](https://nodejs.org/)
2. Install with default options

### Setting Up the Frontend
1. Open Command Prompt
2. Navigate to the frontend directory in the project
3. Install dependencies:
   ```
   npm install
   ```
4. Start the development server:
   ```
   npm run dev
   ```
5. Access the frontend at the URL shown in the command output (typically http://localhost:3000)

## Production Deployment

### Backend Deployment
1. Prepare a server with Python 3.10+ installed
2. Set up PostgreSQL on the server
3. Create a system user for the application:
   ```
   sudo adduser --system --group appuser
   ```
4. Clone the repository to `/opt/projectmanagement`
5. Install dependencies in a virtual environment
6. Create a systemd service file at `/etc/systemd/system/projectmanagement.service`:
   ```ini
   [Unit]
   Description=Project Management API
   After=network.target postgresql.service

   [Service]
   User=appuser
   Group=appuser
   WorkingDirectory=/opt/projectmanagement
   Environment="PATH=/opt/projectmanagement/venv/bin"
   EnvironmentFile=/opt/projectmanagement/.env
   ExecStart=/opt/projectmanagement/venv/bin/python /opt/projectmanagement/backend/main.py

   [Install]
   WantedBy=multi-user.target
   ```
7. Create a production .env file with secure values
8. Enable and start the service:
   ```
   sudo systemctl enable projectmanagement
   sudo systemctl start projectmanagement
   ```

### Nginx Configuration
1. Install Nginx:
   ```
   sudo apt install nginx
   ```
2. Create a configuration file at `/etc/nginx/sites-available/projectmanagement`:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
3. Enable the site:
   ```
   sudo ln -s /etc/nginx/sites-available/projectmanagement /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```
4. Set up SSL with Let's Encrypt:
   ```
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

## Troubleshooting

### Common Issues

#### "uvicorn" is not defined
- Make sure you've installed all dependencies from requirements.txt
- Verify that the import statement `import uvicorn` is at the top of main.py

#### PostgreSQL connection issues
- Check if PostgreSQL service is running
- Verify the credentials in your .env file
- Ensure the database exists and is accessible

#### Port already in use
- If port 8001 is already in use, you can change the port in main.py

#### Package installation failures
- If you encounter any issues installing packages, try updating pip:
  ```
  pip install --upgrade pip
  ```
- For Windows-specific issues, you might need to install Visual C++ Build Tools

## Development Workflow

1. Activate the virtual environment before starting work
2. Run tests before committing changes:
   ```
   cd backend
   pytest
   ```
3. Follow the project coding standards (PEP 8 for Python) 