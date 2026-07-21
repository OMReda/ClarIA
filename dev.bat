@echo off
setlocal EnableDelayedExpansion
title Plateforme de Restitution — Dev Server

:: ─────────────────────────────────────────────────────────────────────────────
::  dev.bat — Start backend + frontend in local dev mode (no Docker needed)
::
::  Requirements already on this machine:
::    python  (3.8+)   — for FastAPI / uvicorn
::    node    (18+)    — for Vite / npm
::
::  Optional:
::    redis-server     — rate limiting (disabled gracefully if absent)
::    ollama           — local LLM (run: ollama serve && ollama pull llama3)
:: ─────────────────────────────────────────────────────────────────────────────

cd /d "%~dp0"

echo.
echo  ===================================================================
echo    Plateforme de Restitution Intelligente  ^|  Dev Mode
echo  ===================================================================
echo.

:: ── 1. Copy dev env if no .env exists ────────────────────────────────────────
if not exist ".env" (
    if exist ".env.dev" (
        copy ".env.dev" ".env" >nul
        echo  [OK] .env created from .env.dev
    ) else (
        echo  [WARN] No .env found — backend will use built-in defaults
    )
) else (
    echo  [OK] .env already exists
)

:: ── 2. Create storage directory ───────────────────────────────────────────────
if not exist "storage" mkdir storage
echo  [OK] storage\ ready

:: ── 3. Install frontend deps if needed ───────────────────────────────────────
if not exist "frontend\node_modules" (
    echo.
    echo  [INFO] Installing frontend dependencies ^(first run only^)...
    cd frontend
    npm install
    if errorlevel 1 (
        echo  [ERROR] npm install failed. Is Node.js installed?
        pause
        exit /b 1
    )
    cd ..
    echo  [OK] Frontend dependencies installed
) else (
    echo  [OK] Frontend node_modules present
)

:: ── 4. Check Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.8+ and add to PATH.
    pause
    exit /b 1
)
echo  [OK] Python found

:: ── 5. Check Redis Broker ───────────────────────────────────────────────────────
echo  [INFO] Checking Redis Broker on port 6379...
powershell -Command "Test-NetConnection localhost -Port 6379 -WarningAction SilentlyContinue" | findstr "TcpTestSucceeded : True" >nul
if errorlevel 1 (
    echo  [WARN] Redis is NOT running on localhost:6379.
    echo         Celery worker requires a running Redis server.
    echo         Please start Redis locally or configure it!
    echo.
) else (
    echo  [OK] Redis broker detected on port 6379
)

:: ── 6. Launch backend in new terminal window ──────────────────────────────────
echo.
echo  [START] Launching backend  ^(http://localhost:8000^)...
start "Backend API" cmd /k "cd /d %~dp0 && color 0A && python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 --env-file .env"

timeout /t 3 /nobreak >nul

:: ── 7. Launch Celery Worker in new terminal window ──────────────────────────────
echo  [START] Launching Celery Worker...
start "Celery Worker" cmd /k "cd /d %~dp0 && color 0D && celery -A backend.workers.celery_app worker --loglevel=info -Q celery"

timeout /t 3 /nobreak >nul

:: ── 8. Launch frontend in new terminal window ─────────────────────────────────
echo  [START] Launching frontend ^(http://localhost:5173^)...
start "Frontend Vite" cmd /k "cd /d %~dp0\frontend && color 0B && npm run dev"

timeout /t 4 /nobreak >nul

:: ── 9. Open browser ───────────────────────────────────────────────────────────
echo  [OK] Opening browser at http://localhost:5173
start "" "http://localhost:5173"

echo.
echo  -------------------------------------------------------------------
echo   Frontend  :  http://localhost:5173
echo   Backend   :  http://localhost:8000
echo   API docs  :  http://localhost:8000/api/docs
echo  -------------------------------------------------------------------
echo   Frontend, Backend, and Celery are running in separate windows.
echo   Press any key here to STOP everything and exit.
echo  -------------------------------------------------------------------
echo.
pause >nul

:: ── 10. Kill servers on keypress ───────────────────────────────────────────────
echo  [STOP] Shutting down...
taskkill /fi "WindowTitle eq Backend API" /f >nul 2>&1
taskkill /fi "WindowTitle eq Celery Worker" /f >nul 2>&1
taskkill /fi "WindowTitle eq Frontend Vite" /f >nul 2>&1
echo  [DONE] All servers stopped.
timeout /t 2 /nobreak >nul

