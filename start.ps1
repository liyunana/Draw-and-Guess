# PowerShell startup script for Draw and Guess
# This script supports Unicode (Chinese) properly

[System.Console]::OutputEncoding = [System.Text.UTF8Encoding]::UTF8

Write-Host "Draw & Guess Game Startup Script" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Virtual environment not found, creating..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "Virtual environment created successfully" -ForegroundColor Green
}

# Set paths
$PYTHON = "venv\Scripts\python.exe"
$PIP = "venv\Scripts\pip.exe"

# Check dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
& $PIP install -q -r requirements.txt

# Select startup mode
Write-Host ""
Write-Host "Choose startup mode:" -ForegroundColor Cyan
Write-Host "1. Start server only"
Write-Host "2. Start client only"
Write-Host "3. Start both server and client"
Write-Host "4. Run tests"
$choice = Read-Host "Enter option (1-4)"

# Function to free up port 5555
function Free-Port {
    $processes = netstat -ano | Select-String ":5555" | Select-String "LISTENING"
    if ($processes) {
        foreach ($line in $processes) {
            $parts = $line -split '\s+'
            $pid = $parts[-1]
            Write-Host "Killing process $pid on port 5555..." -ForegroundColor Yellow
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
}

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Starting server..." -ForegroundColor Green
        Free-Port
        & $PYTHON src\server\main.py
    }
    "2" {
        Write-Host ""
        Write-Host "Starting client..." -ForegroundColor Green
        & $PYTHON src\client\main.py
    }
    "3" {
        Write-Host ""
        Write-Host "Starting server and client..." -ForegroundColor Green
        Free-Port
        
        # Start server in background
        $serverJob = Start-Process -FilePath $PYTHON -ArgumentList "src\server\main.py" -PassThru -WindowStyle Normal
        Start-Sleep -Seconds 2
        
        # Start client
        & $PYTHON src\client\main.py
        
        # After client exits, kill server
        if ($null -ne $serverJob -and -not $serverJob.HasExited) {
            Write-Host "Stopping server..." -ForegroundColor Yellow
            Stop-Process -Id $serverJob.Id -Force -ErrorAction SilentlyContinue
        }
    }
    "4" {
        Write-Host ""
        Write-Host "Running tests..." -ForegroundColor Green
        if (Test-Path "venv\Scripts\pytest.exe") {
            & venv\Scripts\pytest.exe -v
        }
        else {
            & $PYTHON -m pytest -v
        }
    }
    default {
        Write-Host ""
        Write-Host "Invalid option" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}
