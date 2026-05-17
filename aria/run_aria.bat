@echo off
title ARIA v2 - Research Agent
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

:: Check .env exists (needs API keys)
if not exist ".env" (
    echo.
    echo  ⚠️  API keys not configured!
    echo.
    echo  Copy .env.example to .env and add your API keys:
    echo    copy .env.example .env
    echo    notepad .env
    echo.
    echo  At minimum, you need:
    echo    GROQ_API_KEY=your_groq_key_here
    echo    DEEPSEEK_API_KEY=your_deepseek_key_here
    echo    NVIDIA_API_KEY=your_nvidia_key_here
    echo.
    echo  Press any key to continue anyway (will show CLOSED providers)...
    pause >nul
)

echo.
echo  +====================================================================+
echo  ^|                                                                    ^|
echo  ^|   ARIA v2 - Agentic Research Intelligence Architecture             ^|
echo  ^|   Deep Code Research System                                        ^|
echo  ^|                                                                    ^|
echo  ^|   Double-click ready! Type your idea below.                        ^|
echo  ^|                                                                    ^|
echo  +====================================================================+
echo.

:ask
set /p "idea=Enter your research idea (or type 'exit' to quit): "

if /i "%idea%"=="exit" goto :eof
if /i "%idea%"=="" (
    echo Please enter an idea or type 'exit' to quit.
    goto ask
)

echo.
echo [1] Research mode (default) - produces knowledge package
echo [2] Build mode - research + ready-to-build scaffold
echo [3] Dry-run - estimate costs without running
echo.
set /p "mode_choice=Choose mode (1-3): "

if "%mode_choice%"=="1" goto research
if "%mode_choice%"=="2" goto build
if "%mode_choice%"=="3" goto dryrun
goto research

:research
echo.
echo Starting research pipeline...
echo.
python main.py run "%idea%"
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  Run finished with errors. Check the output above.
)
goto done

:build
echo.
echo Starting build mode (research + scaffold)...
echo.
python main.py run "%idea%" --mode build
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  Run finished with errors. Check the output above.
)
goto done

:dryrun
echo.
echo Estimating API usage...
echo.
python main.py run "%idea%" --dry-run
goto done

:done
echo.
echo.
echo ────────────────────────────────────────────
echo.
echo  [1] Run another idea
echo  [2] Launch UI dashboard
echo  [3] Quit
echo.
set /p "next=Choose (1-3): "

if "%next%"=="1" goto ask
if "%next%"=="2" (
    start "ARIA UI" "%~dp0run_ui.bat"
    echo.
    echo UI dashboard launching in a new window.
    goto done
)
pause
goto :eof
