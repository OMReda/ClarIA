@echo off
:: test.bat — Run the backend test suite
cd /d "%~dp0"
echo.
echo  ===================================================================
echo    Plateforme de Restitution Intelligente  ^|  Test Suite
echo  ===================================================================
echo.
python -m pytest tests/backend/ -v --tb=short
echo.
pause
