@echo off
:: logs.bat — Stream logs from all Docker containers
cd /d "%~dp0"
echo  [LOGS] Streaming all container logs. Press Ctrl+C to stop.
echo.
docker compose -f docker/docker-compose.yml logs -f --tail=50
