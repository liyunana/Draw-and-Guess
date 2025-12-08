@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo Draw and Guess Game Launcher
echo ================================
echo.

REM Check virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    py -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Set paths
set "PYTHON=venv\Scripts\python.exe"
set "PIP=venv\Scripts\pip.exe"

REM Check if Python exists in venv
if not exist "%PYTHON%" (
    echo [ERROR] Python not found in virtual environment
    pause
    exit /b 1
)

REM Install dependencies
echo.
echo [INFO] Installing dependencies...
"%PIP%" install -q -r requirements.txt
if errorlevel 1 (
    echo [WARNING] Some dependencies may not be installed correctly
)

REM Menu
echo.
echo Select mode:
echo [1] Start Server
echo [2] Start Client
echo [3] Start Server and Client
echo [4] Run Tests
echo.
set /p choice="Enter option (1-4): "

if "%choice%"=="1" (
    echo.
    echo [INFO] Starting server...
    "%PYTHON%" src\server\main.py
) else if "%choice%"=="2" (
    echo.
    echo [INFO] Starting client...
    "%PYTHON%" src\client\main.py
) else if "%choice%"=="3" (
    echo.
    echo [INFO] Starting server and client...
    start "Draw-and-Guess Server" "%PYTHON%" src\server\main.py
    timeout /t 2 /nobreak >nul
    "%PYTHON%" src\client\main.py
) else if "%choice%"=="4" (
    echo.
    echo [INFO] Running tests...
    if exist "venv\Scripts\pytest.exe" (
        venv\Scripts\pytest.exe -v
    ) else (
        "%PYTHON%" -m pytest -v
    )
) else (
    echo.
    echo [ERROR] Invalid option
    pause
    exit /b 1
)

endlocal
