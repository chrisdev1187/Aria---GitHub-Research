@echo off
title ARIA v2 - UI Dashboard
cd /d "%~dp0"

:: Check Python is available
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python not found! Please install Python 3.12+ from:
    echo  https://www.python.org/downloads/
    echo.
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    echo  Then run install_deps.bat to install all dependencies.
    echo.
    pause
    exit /b 1
)

echo.
echo  +====================================================================+
echo  ^|                                                                    ^|
echo  ^|   ARIA v2 - Research Dashboard                                    ^|
echo  ^|   Launching UI in your browser...                                  ^|
echo  ^|                                                                    ^|
echo  +====================================================================+
echo.

python main.py serve --port 8080

echo.
echo Server stopped.
pause
