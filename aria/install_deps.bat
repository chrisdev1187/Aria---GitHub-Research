@echo off
title ARIA v2 - Installing Dependencies
cd /d "%~dp0"

echo.
echo  +====================================================================+
echo  ^|                                                                    ^|
echo  ^|   Installing ARIA dependencies...                                  ^|
echo  ^|                                                                    ^|
echo  +====================================================================+
echo.

:: Check if Python is installed
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found! Please install Python 3.12+ from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/2] Installing required packages...
echo.

python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ⚠️  Some packages failed to install. Trying individually...
    python -m pip install groq openai typer rich httpx aiohttp python-dotenv pydantic jinja2 PyGithub google-generativeai
)

echo.
echo [2/2] Verifying installation...
echo.

python -c "
import typer, rich, httpx, openai, aiohttp, dotenv, pydantic, jinja2
print('  All core dependencies verified OK')
"

echo.
echo ────────────────────────────────────────────
echo.
echo  ✅ ARIA dependencies installed!
echo.
echo  ⚠️  NEXT STEP: Set up your API keys
echo     Copy .env.example to .env and open it in a text editor:
echo.
echo     copy .env.example .env
echo     notepad .env
echo.
echo     Add your API keys for the providers you want to use:
echo     - GROQ_API_KEY (required - fastest)
echo     - DEEPSEEK_API_KEY (required - deep dives)
echo     - NVIDIA_API_KEY (required - synthesis)
echo     - Others are optional (fallback providers)
echo.
echo  Quick start:
echo    run_aria.bat    - Interactive menu (double-click)
echo    run_ui.bat      - Launch UI dashboard
echo    aria.bat        - CLI: aria run "your idea"
echo.
pause
