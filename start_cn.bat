@echo off
REM 设置代码页为 UTF-8
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 注意: 该批处理文件已转换为英文，以避免编码问题
REM Note: This batch file uses English to avoid encoding issues on Windows

echo Draw and Guess Game Startup Script
echo ===================================

REM 检查虚拟环境 (Check virtual environment)
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)

REM 设置路径 (Set paths)
set "PYTHON=venv\Scripts\python.exe"
set "PIP=venv\Scripts\pip.exe"

REM 检查依赖 (Check dependencies)
echo Checking dependencies...
"%PIP%" install -q -r requirements.txt

REM 选择启动模式 (Select startup mode)
echo.
echo Menu:
echo 1 - Start server only
echo 2 - Start client only
echo 3 - Start both server and client
echo 4 - Run tests
set /p choice="Choose option (1-4): "

REM 释放占用端口的函数 (Free port function)
set "FREE_PORT=for /f %%p in ('netstat -ano ^| findstr :5555 ^| findstr LISTENING') do @for /f "tokens=5" %%a in ("%%p") do @taskkill /F /PID %%a >nul 2>&1"

if "%choice%"=="1" (
    echo.
    echo Starting server...
    REM 释放端口 (Free port)
    %FREE_PORT%
    "%PYTHON%" src\server\main.py
) else if "%choice%"=="2" (
    echo.
    echo Starting client...
    "%PYTHON%" src\client\main.py
) else if "%choice%"=="3" (
    echo.
    echo Starting server and client...
    REM 释放端口 (Free port)
    %FREE_PORT%
    start "Draw-and-Guess Server" "%PYTHON%" src\server\main.py
    timeout /t 2 /nobreak >nul
    "%PYTHON%" src\client\main.py
    REM 客户端退出后，清理后台服务器 (Clean up server after client exits)
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
