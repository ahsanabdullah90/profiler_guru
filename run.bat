@echo off
title Profile Guru Launcher
echo ==================================================
echo  Profile Guru — Decoupled Architecture Launcher
echo ==================================================

:: ── PATH RESOLUTION ───────────────────────────────────────────────────────────
:: %~dp0 always expands to the absolute directory of THIS .bat file, regardless
:: of the shell's current working directory or how the script was launched.
:: All paths below are anchored to this absolute base, so cd / pushd / popd
:: never break anything.

set "ROOT=%~dp0"
:: Strip trailing backslash so concatenation is clean
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "FRONTEND_DIR=%ROOT%\frontend"
set "VENV_PYTHON=%ROOT%\..\\.venv\Scripts\python.exe"

:: Fallback: local .venv inside the project root
if not exist "%VENV_PYTHON%" (
    set "VENV_PYTHON=%ROOT%\.venv\Scripts\python.exe"
)

:: Final fallback: system python (warns user)
if not exist "%VENV_PYTHON%" (
    echo [WARN] Virtual environment not found. Using system Python.
    echo        Expected: %ROOT%\..\\.venv\Scripts\python.exe
    set "VENV_PYTHON=python"
)

echo [INFO] Project root : %ROOT%
echo [INFO] Python exe   : %VENV_PYTHON%
echo [INFO] Frontend dir : %FRONTEND_DIR%
echo.

:: ── CLEANUP EXISTING PROCESSES ────────────────────────────────────────────────
echo [STEP 1] Cleaning up any existing processes on ports 8000 and 3000...
for /f "tokens=5" %%P in ('netstat -aon ^| findstr ":8000 " ^| findstr LISTENING 2^>nul') do (
    echo          Killing PID %%P on port 8000...
    taskkill /F /PID %%P >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -aon ^| findstr ":3000 " ^| findstr LISTENING 2^>nul') do (
    echo          Killing PID %%P on port 3000...
    taskkill /F /PID %%P >nul 2>&1
)
echo          Done.
echo.

:: ── LAUNCH FASTAPI BACKEND ────────────────────────────────────────────────────
:: /D "%ROOT%" locks the new process's working directory to the project root,
:: completely independent of this shell's CWD.
echo [STEP 2] Starting FastAPI Backend (http://127.0.0.1:8000)...
start "Profile Guru — Backend" /D "%ROOT%" /min "%VENV_PYTHON%" main_api.py
echo          Backend process spawned.
echo.

:: ── HEALTH-CHECK POLLING LOOP ─────────────────────────────────────────────────
:: Poll GET /api/health every 1 second for up to 60 attempts (~1 minute).
:: curl.exe ships with Windows 10 1803+ and is always available.
:: The browser is NOT opened until the backend confirms it is alive.
echo [STEP 3] Waiting for backend to become ready...
echo          (polling http://127.0.0.1:8000/api/health — max 60s)
set /a TRIES=0
:WAIT_LOOP
set /a TRIES+=1
if %TRIES% GTR 60 (
    echo.
    echo [ERROR] Backend did not become ready within 60 seconds.
    echo         Check the "Profile Guru — Backend" terminal window for errors.
    echo         Common causes: missing packages, ChromaDB lock, or port conflict.
    pause
    exit /b 1
)
curl.exe -s -o nul -w "%%{http_code}" http://127.0.0.1:8000/api/health 2>nul | findstr /c:"200" >nul 2>&1
if %ERRORLEVEL%==0 goto BACKEND_READY
timeout /t 1 /nobreak >nul
goto WAIT_LOOP

:BACKEND_READY
echo          Backend is ready! (responded after %TRIES%s)
echo.

:: ── LAUNCH NEXT.JS FRONTEND ───────────────────────────────────────────────────
:: pushd uses the absolute FRONTEND_DIR path — unaffected by any prior cd.
:: popd restores the CWD cleanly afterward.
echo [STEP 4] Starting Next.js Frontend (http://localhost:3000)...
pushd "%FRONTEND_DIR%"
start "Profile Guru — Frontend" /min npm run dev
popd
echo          Frontend process spawned.
echo.

:: ── WAIT FOR NEXT.JS COMPILER ─────────────────────────────────────────────────
:: Next.js (Turbopack) typically compiles in 3-8 seconds.
:: Wait 8 seconds to give it a comfortable margin before opening the browser.
echo [STEP 5] Waiting 8 seconds for Next.js initial compilation...
timeout /t 8 /nobreak >nul

:: ── OPEN BROWSER ──────────────────────────────────────────────────────────────
echo [STEP 6] Opening Profile Guru Portal in default browser...
start "" http://localhost:3000
echo.
echo ==================================================
echo  Profile Guru is running!
echo  Backend  → http://localhost:8000
echo  Frontend → http://localhost:3000
echo ==================================================
echo.
echo  The application is active. 
echo  Press any key to SHUT DOWN the application and close all windows...
echo.
pause >nul

echo [SHUTDOWN] Stopping all Profile Guru processes...
for /f "tokens=5" %%P in ('netstat -aon ^| findstr ":8000 " ^| findstr LISTENING 2^>nul') do (
    echo            Stopping Backend (PID %%P)...
    taskkill /F /PID %%P >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -aon ^| findstr ":3000 " ^| findstr LISTENING 2^>nul') do (
    echo            Stopping Frontend (PID %%P)...
    taskkill /F /PID %%P >nul 2>&1
)
echo            Done.
echo.
echo ==================================================
echo  Profile Guru has been shut down successfully.
echo  All background terminal windows have been closed.
echo ==================================================
timeout /t 3 >nul
exit /b 0

