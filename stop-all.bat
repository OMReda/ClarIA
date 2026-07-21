@echo off
setlocal
:: ─────────────────────────────────────────────────────────────────────────────
::  stop-all.bat — Stop all native-mode servers launched by start.bat
::
::  Strategy: start.bat sets a distinct window title for every process it opens:
::    "Backend API"   → uvicorn
::    "Celery Worker" → celery
::    "Frontend Vite" → vite / npm run dev
::
::  We kill by window title, which is scoped to THIS project's cmd windows only.
::  This will NOT affect another checkout of this repo or any other project.
::
::  NOTE: If you started with Docker (start.bat detected Docker), use:
::    docker compose -f docker/docker-compose.yml down
:: ─────────────────────────────────────────────────────────────────────────────

echo.
echo  ===================================================================
echo    Plateforme de Restitution Intelligente  ^|  Stop All Servers
echo  ===================================================================
echo.

set STOPPED=0

:: ── Backend API ───────────────────────────────────────────────────────────────
taskkill /fi "WindowTitle eq Backend API" /f >nul 2>&1
if not errorlevel 1 (
    echo  [STOP] Backend API stopped.
    set STOPPED=1
) else (
    echo  [SKIP] Backend API: not running.
)

:: ── Celery Worker ─────────────────────────────────────────────────────────────
taskkill /fi "WindowTitle eq Celery Worker" /f >nul 2>&1
if not errorlevel 1 (
    echo  [STOP] Celery Worker stopped.
    set STOPPED=1
) else (
    echo  [SKIP] Celery Worker: not running.
)

:: ── Frontend Vite ─────────────────────────────────────────────────────────────
taskkill /fi "WindowTitle eq Frontend Vite" /f >nul 2>&1
if not errorlevel 1 (
    echo  [STOP] Frontend Vite stopped.
    set STOPPED=1
) else (
    echo  [SKIP] Frontend Vite: not running.
)

echo.
if "%STOPPED%"=="1" (
    echo  [DONE] All running servers have been stopped.
) else (
    echo  [INFO] No servers were running. Nothing to stop.
    echo  [INFO] If you used Docker, run:
    echo           docker compose -f docker/docker-compose.yml down
)
echo.
endlocal
