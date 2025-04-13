@echo off
echo Setting up development environment...

REM Create Python virtual environment
echo Creating Python virtual environment...
python -m venv venv
call venv\Scripts\activate

REM Install backend dependencies
echo Installing backend dependencies...
cd backend
pip install -r requirements.txt
cd ..

REM Setup configuration files
echo Creating configuration files...
if not exist .env (
    echo Creating .env file with default settings...
    echo POSTGRES_USER=postgres > .env
    echo POSTGRES_PASSWORD=postgres >> .env
    echo POSTGRES_DB=projectmanagement >> .env
    echo POSTGRES_SERVER=localhost >> .env
    echo POSTGRES_PORT=5432 >> .env
    echo JWT_SECRET=PLEASE_CHANGE_THIS_TO_A_SECURE_VALUE >> .env
    echo ENVIRONMENT=development >> .env
    echo LOG_LEVEL=DEBUG >> .env
)

REM Check for PostgreSQL
echo Checking for PostgreSQL...
where psql >nul 2>nul
if %errorlevel% equ 0 (
    echo PostgreSQL found! Make sure it's running and create a database named 'projectmanagement'
) else (
    echo PostgreSQL not found. Please install PostgreSQL from https://www.postgresql.org/download/windows/
    echo After installation, create a database named 'projectmanagement'
)

REM Setup complete message
echo.
echo Development environment setup complete!
echo.
echo Before running the application:
echo 1. Make sure PostgreSQL is running with a database named 'projectmanagement'
echo 2. Edit the .env file with your database credentials if needed
echo.
echo To start the backend server:
echo 1. Activate the virtual environment: venv\Scripts\activate
echo 2. Run the server: python backend\main.py
echo.
echo For the frontend (once implemented):
echo 1. Navigate to the frontend directory: cd frontend
echo 2. Install dependencies: npm install
echo 3. Start development server: npm run dev
echo.
echo Happy coding! 