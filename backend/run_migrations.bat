@echo off
cd %~dp0
set PYTHONPATH=%~dp0;%PYTHONPATH%
echo Running database migrations...
python -m alembic upgrade head
echo Migrations complete. 