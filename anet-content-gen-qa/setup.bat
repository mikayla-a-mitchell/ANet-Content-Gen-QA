@echo off
setlocal enabledelayedexpansion
title ANet Exit Ticket Studio - Setup

echo.
echo ==================================================
echo   ANet Exit Ticket Studio -- Setup (Windows)
echo ==================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo Download from https://python.org
    echo IMPORTANT: Check "Add Python to PATH" during install.
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VERSION=%%v
echo Found Python %PY_VERSION%

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 ( echo ERROR: Could not create venv. & pause & exit /b 1 )
)

echo Installing packages (may take a minute)...
call venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 ( echo ERROR: Package install failed. & pause & exit /b 1 )
echo Packages installed.

echo.
python -c "import cairosvg" >nul 2>&1
if errorlevel 1 (
    echo NOTE: PNG export unavailable on this machine -- visuals still work as SVG.
    echo       cairosvg's Windows wheels usually bundle what they need; if this
    echo       persists, PNG export just won't be offered. Nothing else to do.
) else (
    echo PNG export available.
)

if not exist "output" ( mkdir output & echo Created output\ -- generated lessons will be saved here )

echo.
echo API Key Setup
set /p ANT_KEY="  Anthropic API key (claude.ai - Settings - API Keys): "
(echo ANTHROPIC_API_KEY=%ANT_KEY%) > "%SCRIPT_DIR%.env"
echo Key saved to .env

echo.
echo ==================================================
echo   Setup complete!
echo   -- Double-click launch.bat to start the app
echo ==================================================
echo.
pause
