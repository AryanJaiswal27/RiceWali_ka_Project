@echo off
REM ==============================================================================
REM TCS GenAI Lab - Windows Service Orchestration Script
REM Starts Connectivity Verification, FastAPI Backend, and Streamlit Operations Console
REM ==============================================================================

echo ================================================================================
echo TCS GENAI LAB // ENTERPRISE SERVICE LAUNCHER (WINDOWS)
echo ================================================================================

echo [*] Step 1/4: Executing pre-flight subsystem connectivity verification...
python verify_lab_connectivity.py
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Verification flagged warnings or offline mode. Continuing startup...
)

echo.
echo [*] Step 2/4: Executing automated 4-dimension regression benchmark (100%% Target)...
python -m src.evaluation
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Benchmark tests encountered warnings. Continuing startup...
)

echo.
echo [*] Step 3/4: Launching FastAPI backend service on 0.0.0.0:8000 in background...
start "FastAPI Diagnostics Backend" cmd /c "uvicorn src.api:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo.
echo [*] Step 4/4: Launching Streamlit industrial console on 0.0.0.0:8501...
echo ================================================================================
echo OPERATIONS CONSOLE ACCESSIBLE AT: http://localhost:8501
echo ================================================================================

streamlit run app.py --server.port 8501 --server.address 0.0.0.0
