@echo off
title S1 IPTV Helper
cd /d "%~dp0"

:: Create venv and install dependencies on first run only
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment.
        echo Make sure Python 3.10+ is installed and in PATH.
        pause
        exit /b 1
    )
    echo Installing dependencies...
    venv\Scripts\pip.exe install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install dependencies.
        echo Check your internet connection and try again.
        pause
        exit /b 1
    )
    echo.
)

if not exist "config.json" (
    echo No config.json found — copying config.example.json.
    echo Edit config.json and fill in your IPTV username/password before continuing.
    copy config.example.json config.json >nul
    pause
    exit /b 1
)

:: Launch without a console window.
start "" venv\Scripts\pythonw.exe -m s1iptv.main
