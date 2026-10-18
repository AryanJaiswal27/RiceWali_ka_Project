#!/usr/bin/env bash
# ==============================================================================
# TCS GenAI Lab - Service Orchestration Script (Fresco Linux VM)
# Starts Connectivity Verification, FastAPI Backend, and Streamlit Operations Console
# ==============================================================================

set -e

echo "================================================================================"
echo "TCS GENAI LAB // ENTERPRISE SERVICE LAUNCHER"
echo "Target Platform: Fresco Linux VM / CentOS / Ubuntu"
echo "================================================================================"

# 1. Execute Subsystem Verification
echo -e "\n[*] Step 1/4: Executing pre-flight subsystem verification..."
python3 verify_lab_connectivity.py || python verify_lab_connectivity.py

# 2. Execute Automated Quality Benchmark Suite (100% Target)
echo -e "\n[*] Step 2/4: Executing automated 4-dimension regression benchmark..."
python3 -m src.evaluation || python -m src.evaluation

# 3. Launch FastAPI REST Service in Background
echo -e "\n[*] Step 3/4: Launching FastAPI backend service on 0.0.0.0:8000..."
nohup uvicorn src.api:app --host 0.0.0.0 --port 8000 > fastapi_service.log 2>&1 &
API_PID=$!
echo "    FastAPI running in background with PID: ${API_PID} (Logs: fastapi_service.log)"

# Brief pause for socket binding
sleep 2

# Verify API health
echo "    Verifying API health endpoint..."
if command -v curl &> /dev/null; then
    curl -s http://127.0.0.1:8000/health || echo "    [WARNING] Health check probe delayed, continuing."
fi

# 4. Launch Streamlit Operations Console in Foreground
echo -e "\n[*] Step 4/4: Launching Streamlit industrial console on 0.0.0.0:8501..."
echo "================================================================================"
echo "OPERATIONS CONSOLE ACCESSIBLE AT: http://<VM_IP_OR_LOCALHOST>:8501"
echo "================================================================================"

trap "echo '[*] Shutting down background API PID ${API_PID}...'; kill ${API_PID} 2>/dev/null || true; exit 0" INT TERM EXIT

streamlit run app.py --server.port 8501 --server.address 0.0.0.0
