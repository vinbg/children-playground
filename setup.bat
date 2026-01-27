@echo off
setlocal enabledelayedexpansion

:: IB Portfolio MCP Server - Windows Setup Script
:: Double-click this file to run setup

echo.
echo ================================================================
echo         IB Portfolio Tracker - MCP Server Setup
echo ================================================================
echo.

:: Get the directory where the script is located
cd /d "%~dp0"
set "SCRIPT_DIR=%CD%"

:: Step 1: Check Python
echo [Step 1] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10 or higher.
    echo         Download from: https://www.python.org/downloads/
    echo         Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Found Python %PYTHON_VERSION%

:: Step 2: Create virtual environment
echo.
echo [Step 2] Creating virtual environment...
if exist ".venv" (
    echo [INFO] Virtual environment already exists, skipping...
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

:: Step 3: Install dependencies
echo.
echo [Step 3] Installing dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -e . -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

:: Step 4: Configuration
echo.
echo [Step 4] Configuring environment...

if exist ".env" (
    echo [INFO] .env file already exists
    set /p "OVERWRITE=Overwrite? (y/N): "
    if /i "!OVERWRITE!"=="y" (
        del .env
    ) else (
        echo [INFO] Keeping existing .env file
        goto :test_finnhub
    )
)

echo.
echo Let's configure your API keys:
echo.

:: Finnhub API Key
echo Finnhub API Key (get free at https://finnhub.io/register):
set /p "FINNHUB_KEY=  Enter your Finnhub API key: "

:: IB Port
echo.
echo IB Gateway/TWS Port:
echo   4001 = IB Gateway Paper Trading (recommended)
echo   4002 = IB Gateway Live Trading
echo   7497 = TWS Paper Trading
echo   7496 = TWS Live Trading
set /p "IB_PORT=  Enter port [4001]: "
if "!IB_PORT!"=="" set "IB_PORT=4001"

:: Create .env file
(
echo # Interactive Brokers Connection
echo IB_HOST=127.0.0.1
echo IB_PORT=!IB_PORT!
echo IB_CLIENT_ID=1
echo.
echo # News API
echo FINNHUB_API_KEY=!FINNHUB_KEY!
echo.
echo # Sentiment Model: "vader" (fast^) or "finbert" (accurate, 500MB download^)
echo SENTIMENT_MODEL=vader
echo.
echo # Cache TTL in seconds
echo NEWS_CACHE_TTL=300
echo SENTIMENT_CACHE_TTL=3600
echo.
echo # Logging
echo LOG_LEVEL=INFO
) > .env

echo [OK] Configuration saved to .env

:test_finnhub
:: Step 5: Test Finnhub API
echo.
echo [Step 5] Testing Finnhub API...
call .venv\Scripts\activate.bat
python -c "import os; from dotenv import load_dotenv; load_dotenv(); key = os.getenv('FINNHUB_API_KEY', ''); print('[WARN] No Finnhub API key configured' if not key or key == 'your_finnhub_api_key_here' else '[OK] Finnhub API key configured')" 2>nul || echo [WARN] Could not test Finnhub API

:: Step 6: Test IB Connection
echo.
echo [Step 6] Testing IB Gateway connection...
python -c "import asyncio; import os; from dotenv import load_dotenv; load_dotenv(); port = int(os.getenv('IB_PORT', 4001)); print(f'[INFO] IB Gateway configured on port {port}'); print('[INFO] Make sure IB Gateway is running before using portfolio features')" 2>nul || echo [WARN] Could not verify IB settings

:: Done!
echo.
echo ================================================================
echo                     Setup Complete!
echo ================================================================
echo.
echo Next steps:
echo.
echo 1. Make sure IB Gateway is running
echo    Download: https://www.interactivebrokers.com/en/trading/ibgateway-stable.php
echo.
echo 2. Add to Claude Desktop config:
echo    File: %%APPDATA%%\Claude\claude_desktop_config.json
echo.
echo    {
echo      "mcpServers": {
echo        "ib-portfolio": {
echo          "command": "%SCRIPT_DIR%\.venv\Scripts\python.exe",
echo          "args": ["-m", "ib_mcp.server"],
echo          "cwd": "%SCRIPT_DIR%"
echo        }
echo      }
echo    }
echo.
echo 3. Restart Claude Desktop (close and reopen)
echo.
echo 4. Ask Claude: "What's my portfolio value?"
echo.
echo For troubleshooting, see README.md
echo.
pause
