@echo off
title ANet Exit Ticket Studio
cd /d "%~dp0"
if not exist "venv" (
    echo Virtual environment not found. Please run setup.bat first.
    pause & exit /b 1
)
call venv\Scripts\activate.bat
echo Starting ANet Exit Ticket Studio -- your browser will open shortly...
streamlit run app.py
pause
