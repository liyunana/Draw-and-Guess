@echo off
REM Set code page to UTF-8
chcp 65001 >nul
setlocal enabledelayedexpansion

REM Quick startup script for Windows

echo Draw ^& Guess Game Startup Script
echo ================================

REM Check virtual environment
if not exist "venv" (
    echo Virtual environment not found, creating...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)

REM Set paths
set "PYTHON=venv\Scripts\python.exe"
set "PIP=venv\Scripts\pip.exe"

REM Check dependencies
echo Checking dependencies...
"%PIP%" install -q -r requirements.txt

REM Select startup mode
echo.
echo Choose startup mode:
echo 1. Start server only
echo 2. Start client only
echo 3. Start server and client
echo 4. Run tests
set /p choice="Enter option (1-4): "

REM Function to free up port
set "FREE_PORT=for /f %%p in ('netstat -ano ^| findstr :5555 ^| findstr LISTENING') do @for /f "tokens=5" %%a in ("%%p") do @taskkill /F /PID %%a >nul 2>&1"

if "%choice%"=="1" (
    echo.
    echo Starting server...
    REM Free port
    %FREE_PORT%
    "%PYTHON%" src\server\main.py
) else if "%choice%"=="2" (
    echo.
    echo Starting client...
    "%PYTHON%" src\client\main.py
) else if "%choice%"=="3" (
    echo.
    echo Starting server and client...
    REM Free port
    %FREE_PORT%
    start "Draw-and-Guess Server" "%PYTHON%" src\server\main.py
    timeout /t 2 /nobreak >nul
    "%PYTHON%" src\client\main.py
    REM After client exits, clean up background server
    for /f "tokens=2" %%i in ('tasklist /fi "WINDOWTITLE eq Draw-and-Guess Server" /fo list ^| findstr "PID:"') do taskkill /PID %%i /F >nul 2>&1
) else if "%choice%"=="4" (
    echo.
    echo Running tests...
    if exist "venv\Scripts\pytest.exe" (
        venv\Scripts\pytest.exe -v
    ) else (
        "%PYTHON%" -m pytest -v
    )
) else (
    echo.
    echo Invalid option
    pause
    exit /b 1
)

endlocal
