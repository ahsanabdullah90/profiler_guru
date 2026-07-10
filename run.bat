@echo off
title Profile Guru Launcher
echo ==================================================
echo  Profile Guru — Decoupled Architecture Launcher
echo ==================================================

:: ── PATH RESOLUTION ───────────────────────────────────────────────────────────
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "FRONTEND_DIR=%ROOT%\frontend"
set "VENV_PYTHON=%ROOT%\..\\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    set "VENV_PYTHON=%ROOT%\.venv\Scripts\python.exe"
)

if not exist "%VENV_PYTHON%" (
    echo [WARN] Virtual environment not found. Using system Python.
    set "VENV_PYTHON=python"
) else (
    "%VENV_PYTHON%" -c "import fastapi" >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Venv missing dependencies. Using system Python.
        set "VENV_PYTHON=python"
    )
)

echo [INFO] Project root : %ROOT%
echo [INFO] Python exe   : %VENV_PYTHON%
echo [INFO] Frontend dir : %FRONTEND_DIR%
echo.

:: ── CLEANUP EXISTING PROCESSES ────────────────────────────────────────────────
echo [STEP 1] Cleaning up any existing processes on ports 8000 and 3000...
call :cleanup_ports
echo          Done.
echo.

:: ── ENSURE MEMURAI (REDIS) IS RUNNING ─────────────────────────────────────────
echo [STEP 2] Checking Memurai (Redis cache)...
sc query Memurai 2>nul | findstr /c:"RUNNING" >nul 2>&1
if %ERRORLEVEL%==0 (
    echo          Memurai is already running.
) else (
    echo          Starting Memurai service...
    net start Memurai >nul 2>&1
    if %ERRORLEVEL%==0 (
        echo          Memurai started successfully.
    ) else (
        echo [WARN]  Could not start Memurai service. Caching will be disabled.
        echo         To install: winget install Memurai.MemuraiDeveloper
    )
)
echo.

:: ── LAUNCH FASTAPI BACKEND ────────────────────────────────────────────────────
echo [STEP 3] Starting FastAPI Backend (http://127.0.0.1:8000)...
start "ProfileGuru-Backend" /D "%ROOT%" /min "%VENV_PYTHON%" main_api.py
echo          Backend process spawned.
echo.

:: ── HEALTH-CHECK POLLING LOOP ─────────────────────────────────────────────────
echo [STEP 4] Waiting for backend to become ready...
echo          (polling http://127.0.0.1:8000/api/health — max 60s)
set /a TRIES=0
:WAIT_LOOP
set /a TRIES+=1
if %TRIES% GTR 60 (
    echo.
    echo [ERROR] Backend did not become ready within 60 seconds.
    echo         Check the "ProfileGuru-Backend" terminal window for errors.
    call :shutdown
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
echo [STEP 5] Starting Next.js Frontend (http://localhost:3000)...
start "ProfileGuru-Frontend" /D "%FRONTEND_DIR%" /min cmd /c "npm run dev"
echo          Frontend process spawned.
echo.

:: ── WAIT FOR NEXT.JS COMPILER ─────────────────────────────────────────────────
echo [STEP 6] Waiting 8 seconds for Next.js initial compilation...
timeout /t 8 /nobreak >nul

:: ── PRINT STATUS ──────────────────────────────────────────────────────────────
echo.
echo ==================================================
echo  Profile Guru is running!
echo.
echo  Backend  : http://localhost:8000
echo  Frontend : http://localhost:3000
echo.
echo  Open http://localhost:3000 in your browser.
echo ==================================================
echo.
echo  Press X to SHUT DOWN...
echo.

:: ── WAIT FOR X KEY ────────────────────────────────────────────────────────────
:WAIT_X
choice /c X /n /m ""
if %ERRORLEVEL%==1 goto SHUTDOWN
goto WAIT_X

:SHUTDOWN
echo.
echo [SHUTDOWN] Stopping all Profile Guru processes...
call :cleanup_ports
call :cleanup_windows
echo.
echo ==================================================
echo  Profile Guru has been shut down.
echo ==================================================
timeout /t 2 >nul
exit /b 0

:: ── FUNCTIONS ─────────────────────────────────────────────────────────────────

:cleanup_ports
for /f "tokens=5" %%P in ('netstat -aon ^| findstr ":8000 " ^| findstr LISTENING 2^>nul') do (
    echo          Killing PID %%P on port 8000...
    taskkill /F /PID %%P >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -aon ^| findstr ":3000 " ^| findstr LISTENING 2^>nul') do (
    echo          Killing PID %%P on port 3000...
    taskkill /F /PID %%P >nul 2>&1
)
exit /b 0

:cleanup_windows
taskkill /FI "WINDOWTITLE eq ProfileGuru-Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ProfileGuru-Frontend*" /F >nul 2>&1
exit /b 0
