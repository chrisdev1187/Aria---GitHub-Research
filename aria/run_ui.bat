@echo off
title ARIA v2 - UI Dashboard
cd /d "%~dp0"

echo.
echo  +====================================================================+
echo  ^|   ARIA v2 - Research Dashboard                                    ^|
echo  +====================================================================+
echo.

:: Kill any existing Python process holding port 8080
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8080 "') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH.
    pause
    exit /b 1
)

echo  Starting server on http://127.0.0.1:8080
echo  Press Ctrl+C to stop.
echo.

python main.py serve --port 8080

echo.
echo  Server stopped. Press any key to close.
pause >nul
