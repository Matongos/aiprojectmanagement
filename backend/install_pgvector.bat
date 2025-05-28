@echo off
REM Set Visual Studio environment
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

REM Set PostgreSQL root directory and include paths
set "PGROOT=C:\Program Files\PostgreSQL\12"
set "INCLUDE=%PGROOT%\include;%PGROOT%\include\server;%PGROOT%\include\server\port\win32_msvc;%PGROOT%\include\server\port\win32;%INCLUDE%"
set "LIB=%PGROOT%\lib;%LIB%"

REM Create temp directory and clone pgvector
cd %TEMP%
rmdir /s /q pgvector 2>nul
git clone --branch v0.4.4 https://github.com/pgvector/pgvector.git
cd pgvector

REM Build and install
nmake /F Makefile.win clean
nmake /F Makefile.win
nmake /F Makefile.win install

echo "pgvector installation completed!"

REM Create extension in database
"%PGROOT%\bin\psql" -U postgres -d aiprojectmanagement -c "CREATE EXTENSION IF NOT EXISTS vector;" 