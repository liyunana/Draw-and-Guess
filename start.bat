@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 快速启动脚本 (Windows)

echo  Draw ^& Guess 游戏启动脚本
echo ================================

REM 检查虚拟环境
if not exist "venv" (
    echo  虚拟环境不存在，正在创建...
    python -m venv venv
    if errorlevel 1 (
        echo  虚拟环境创建失败
        pause
        exit /b 1
    )
    echo  虚拟环境创建完成
)

REM 设置路径
set "PYTHON=venv\Scripts\python.exe"
set "PIP=venv\Scripts\pip.exe"

REM 检查依赖
echo  检查依赖...
"%PIP%" install -q -r requirements.txt

REM 选择启动模式
echo.
echo 请选择启动模式:
echo 1. 启动服务器
echo 2. 启动客户端
echo 3. 同时启动服务器和客户端
echo 4. 运行测试
set /p choice="输入选项 (1-4): "

REM 释放占用端口的函数
set "FREE_PORT=for /f %%p in ('netstat -ano ^| findstr :5555 ^| findstr LISTENING') do @for /f "tokens=5" %%a in ("%%p") do @taskkill /F /PID %%a >nul 2>&1"

if "%choice%"=="1" (
    echo.
    echo  启动服务器...
    REM 释放端口
    %FREE_PORT%
    "%PYTHON%" src\server\main.py
) else if "%choice%"=="2" (
    echo.
    echo  启动客户端...
    "%PYTHON%" src\client\main.py
) else if "%choice%"=="3" (
    echo.
    echo  启动服务器和客户端...
    REM 释放端口
    %FREE_PORT%
    start "Draw-and-Guess Server" "%PYTHON%" src\server\main.py
    timeout /t 2 /nobreak >nul
    "%PYTHON%" src\client\main.py
    REM 客户端退出后，清理后台服务器
    for /f "tokens=2" %%i in ('tasklist /fi "WINDOWTITLE eq Draw-and-Guess Server" /fo list ^| findstr "PID:"') do taskkill /PID %%i /F >nul 2>&1
) else if "%choice%"=="4" (
    echo.
    echo  运行测试...
    if exist "venv\Scripts\pytest.exe" (
        venv\Scripts\pytest.exe -v
    ) else (
        "%PYTHON%" -m pytest -v
    )
) else (
    echo.
    echo  无效选项
    pause
    exit /b 1
)

endlocal
