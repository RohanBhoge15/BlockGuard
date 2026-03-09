@echo off
echo ============================================
echo   BlockGuard - Setup Script (Windows)
echo ============================================
echo.

REM Step 1: Start Docker containers
echo [1/5] Starting Docker containers (MongoDB + Ganache)...
docker-compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo [!] Docker failed. Make sure Docker Desktop is running.
    pause
    exit /b 1
)
echo [+] Docker containers started!
echo.

REM Step 2: Wait for services to be ready
echo [2/5] Waiting for services to start...
timeout /t 5 /nobreak >nul
echo [+] Services should be ready.
echo.

REM Step 3: Install Python dependencies
echo [3/5] Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [!] pip install failed. Check Python installation.
    pause
    exit /b 1
)
echo [+] Python dependencies installed!
echo.

REM Step 4: Generate dataset and train model
echo [4/5] Generating synthetic dataset...
python backend/data/generate_dataset.py
echo.
echo [4/5] Training ML models...
python backend/ml_model/train_model.py
echo [+] Models trained!
echo.

REM Step 5: Deploy smart contract
echo [5/5] Deploying smart contract to Ganache...
python backend/blockchain/deploy_contract.py
echo.

echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo To run the system:
echo   1. Backend API:    python backend/app.py
echo   2. React Dashboard: cd frontend ^&^& npm install ^&^& npm start
echo   3. Test Suite:     streamlit run test_suite.py
echo.
pause
