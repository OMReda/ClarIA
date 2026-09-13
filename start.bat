@echo off
setlocal EnableDelayedExpansion
:: ─────────────────────────────────────────────────────────────────────────────
::  start.bat — Smart launcher (Flat control flow, crash-proof)
::
::  WITH Docker    → Full Docker Compose stack (postgres, redis, ollama, etc.)
::  WITHOUT Docker → Native async mode:
::                     Redis / Memurai  → message broker for Celery
::                     Backend (uvicorn) → FastAPI API server
::                     Celery Worker    → processes prompts asynchronously
::                     Frontend (vite)  → React UI
:: ─────────────────────────────────────────────────────────────────────────────
cd /d "%~dp0"

echo.
echo  ===================================================================
echo    Plateforme de Restitution Intelligente  ^|  Smart Launcher
echo  ===================================================================
echo.

:: ── Detect Docker ────────────────────────────────────────────────────────────
docker info >nul 2>&1
if errorlevel 1 goto :native_mode

echo  [OK] Docker is running — starting full Docker stack...
goto :docker_mode


:: ══════════════════════════════════════════════════════════════════════════════
:docker_mode
:: ══════════════════════════════════════════════════════════════════════════════
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo  [OK] .env created from .env.example
    )
)
echo.
echo  [BUILD] Building and starting all services...
echo  [INFO]  First run: Ollama will download the llama3 model (~4 GB). Be patient.
echo.
docker compose -f docker/docker-compose.yml up --build -d
if errorlevel 1 goto :docker_failed

echo.
echo  [WAIT] Waiting for services...
timeout /t 10 /nobreak >nul
echo.
echo  -------------------------------------------------------------------
echo   App      :  http://localhost
echo   API docs :  http://localhost/api/docs
echo  -------------------------------------------------------------------
echo   Run  stop.bat  to shut everything down.
echo  -------------------------------------------------------------------
echo.
start "" "http://localhost"
goto :end

:docker_failed
echo  [ERROR] Docker Compose failed.
pause
exit /b 1


:: ══════════════════════════════════════════════════════════════════════════════
:native_mode
:: ══════════════════════════════════════════════════════════════════════════════
echo.
echo  ===================================================================
echo    Native Async Mode  ^|  Redis + Celery + Backend + Frontend
echo  ===================================================================
echo.

:: ── 1. Ensure .env exists ────────────────────────────────────────────────────
if exist ".env" goto :env_ok
if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo  [OK] .env created from .env.example
    goto :env_done
)
echo  [WARN] No .env found — using defaults
goto :env_done

:env_ok
echo  [OK] .env already exists

:env_done
set CELERY_ALWAYS_EAGER=False

:: ── 2. Storage folder ─────────────────────────────────────────────────────────
if not exist "storage" mkdir storage
echo  [OK] storage\ ready

:: ── 3. Frontend deps ──────────────────────────────────────────────────────────
if exist "frontend\node_modules" goto :frontend_ok
echo.
echo  [INFO] Installing frontend dependencies (first run only)...
cd frontend && npm install
if errorlevel 1 goto :npm_failed
cd ..
echo  [OK] Frontend dependencies installed
goto :frontend_done

:npm_failed
echo  [ERROR] npm install failed.
cd ..
pause
exit /b 1

:frontend_ok
echo  [OK] Frontend node_modules present

:frontend_done

:: ── 4. Check .venv ───────────────────────────────────────────────────────────
if exist ".venv\Scripts\python.exe" goto :python_done
echo.
echo  [ERROR] Virtual environment not found at .venv\
echo  Run the following commands once to create it:
echo    py -3.11 -m venv .venv
echo    .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
echo    .venv\Scripts\python.exe -m pip install -r backend\requirements-ml.txt
echo.
pause
exit /b 1

:python_done
echo  [OK] .venv (Python 3.11) found

:: ── 5. Ensure Redis is running ────────────────────────────────────────────────
echo  [INFO] Checking Redis on port 6379...

:: Quick TCP check
set REDIS_OK=0
powershell -NoProfile -NonInteractive -Command "try { $t = New-Object System.Net.Sockets.TcpClient; $t.Connect('localhost',6379); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 set REDIS_OK=1

if "!REDIS_OK!"=="1" goto :redis_ready

:: Try to start Memurai Windows service
echo  [INFO] Redis not running. Checking Memurai service...
sc query Memurai >nul 2>&1
if errorlevel 1 goto :no_memurai
sc start Memurai >nul 2>&1
timeout /t 3 /nobreak >nul
powershell -NoProfile -NonInteractive -Command "try { $t = New-Object System.Net.Sockets.TcpClient; $t.Connect('localhost',6379); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto :redis_started

:no_memurai
sc query memurai-developer >nul 2>&1
if errorlevel 1 goto :no_redis
sc start memurai-developer >nul 2>&1
timeout /t 3 /nobreak >nul
powershell -NoProfile -NonInteractive -Command "try { $t = New-Object System.Net.Sockets.TcpClient; $t.Connect('localhost',6379); $t.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto :redis_started

:no_redis
echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  Redis is required for async Celery processing.             ║
echo  ║                                                              ║
echo  ║  Install Memurai (free Redis for Windows, no Docker):       ║
echo  ║  https://www.memurai.com/get-memurai                        ║
echo  ║                                                              ║
echo  ║  After install, run start.bat again — it will               ║
echo  ║  start Memurai automatically.                               ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
pause
exit /b 1

:redis_started
echo  [OK] Redis started successfully via service
goto :redis_ready


:redis_ready
:: ── 6. Launch Backend ─────────────────────────────────────────────────────────
echo  [OK] Redis broker detected on port 6379
echo.
echo  [START] Backend API (http://localhost:8000)...
start "Backend API" cmd /k "cd /d %~dp0 && color 0A && title Backend API && set CELERY_ALWAYS_EAGER=False&& .venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 --env-file .env"
timeout /t 3 /nobreak >nul

:: ── 7. Launch Celery Worker ───────────────────────────────────────────────────
echo  [START] Celery Worker (async prompt processing)...
start "Celery Worker" cmd /k "cd /d %~dp0 && color 0D && title Celery Worker && set CELERY_ALWAYS_EAGER=False&& .venv\Scripts\python.exe -m celery -A backend.workers.celery_app worker --loglevel=info -Q celery --pool=solo -n worker-%%RANDOM%%@%%h"
timeout /t 3 /nobreak >nul

:: ── 7.5 Launch Keycloak ───────────────────────────────────────────────────────
echo  [START] Keycloak (http://localhost:8080)...
start "Keycloak Auth" cmd /k "cd /d %~dp0 && color 0E && title Keycloak Auth && call start-keycloak.bat --import-realm"
timeout /t 5 /nobreak >nul

:: ── 8. Launch Frontend ────────────────────────────────────────────────────────
echo  [START] Launching frontend (http://localhost:5173)...
start "Frontend Vite" cmd /k "cd /d %~dp0\frontend && color 0B && title Frontend Vite && npm run dev"
timeout /t 4 /nobreak >nul

:: ── 9. Open browser ───────────────────────────────────────────────────────────
echo  [OK] Opening browser...
start "" "https://localhost:5173"

echo.
echo  -------------------------------------------------------------------
echo   Frontend  :  https://localhost:5173
echo   Backend   :  http://localhost:8000
echo   API docs  :  http://localhost:8000/api/docs
echo   Keycloak  :  http://localhost:8080
echo  -------------------------------------------------------------------
echo   Mode: Native ASYNC — Redis + Celery Worker + Backend + Frontend
echo   Press any key here to STOP everything and exit.
echo  -------------------------------------------------------------------
echo.
pause >nul

:: ── 10. Cleanup ──────────────────────────────────────────────────────────────
echo  [STOP] Shutting down...
taskkill /fi "WindowTitle eq Backend API" /f >nul 2>&1
taskkill /fi "WindowTitle eq Celery Worker" /f >nul 2>&1
taskkill /fi "WindowTitle eq Frontend Vite" /f >nul 2>&1
taskkill /fi "WindowTitle eq Keycloak Auth" /f >nul 2>&1
echo  [DONE] All servers stopped.
timeout /t 2 /nobreak >nul

:end
