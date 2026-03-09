@echo off
echo ============================================
echo   BlockGuard - Run All Services
echo ============================================
echo.

REM Check Docker containers
echo [*] Checking Docker containers...
docker-compose ps
echo.

REM Start Flask backend in background
echo [*] Starting Flask Backend API on port 5000...
start "BlockGuard-Backend" cmd /k "cd /d %~dp0 && python backend/app.py"
timeout /t 3 /nobreak >nul

REM Start React frontend
echo [*] Starting React Dashboard on port 3000...
start "BlockGuard-Frontend" cmd /k "cd /d %~dp0\frontend && npm start"
timeout /t 2 /nobreak >nul

REM Start Streamlit test suite
echo [*] Starting Streamlit Test Suite on port 8501...
start "BlockGuard-TestSuite" cmd /k "cd /d %~dp0 && streamlit run test_suite.py"

echo.
echo ============================================
echo   All services starting!
echo ============================================
echo.
echo   Backend API:     http://localhost:5000
echo   React Dashboard: http://localhost:3000
echo   Test Suite:      http://localhost:8501
echo.
echo Press any key to close this window (services will keep running)...
pause >nul
