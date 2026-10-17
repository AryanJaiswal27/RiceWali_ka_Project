# AI Product Manual Troubleshooting Assistant
### TCS GenAI Lab Enterprise Diagnostic System - Fresco Sandbox Standard

---

## 1. System Overview

The **AI Product Manual Troubleshooting Assistant** is an enterprise-grade field engineering diagnostics platform aligned with the **TCS GenAI Lab Model-as-a-Service (MaaS) gateway**. It provides automated, deterministic procedural troubleshooting for enterprise network infrastructure:
- **Apex Router Pro-X** (Carrier-grade edge router, Model ID: `ARPX-800`)
- **CoreSwitch 4000** (Modular Layer-3 core switch, Model ID: `CS4K-48T`)

The system enforces corporate IT standards: clear modular architecture, deterministic tool execution, strict safety boundary interlocks, and a high-density industrial operations console.

```
                     +---------------------------------------+
                     |    Streamlit Industrial Operations    |
                     |          Console (app.py)             |
                     +-------------------+-------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |      FastAPI Backend Engine           |
                     |           (src/api.py)                |
                     +-------------------+-------------------+
                                         |
     +-----------------------------------+-----------------------------------+
     |                                   |                                   |
     v                                   v                                   v
+------------------+           +-------------------+               +------------------+
| Diagnostic Tools |           | Multi-Agent Core  |               | Knowledge Base   |
| (src/tools.py)   |           | (src/agents.py)   |               | (data/)          |
|                  |           |                   |               |                  |
| - Error DB Query |           | - Clarifier Agent |               | - error_codes    |
| - Component Check|           | - Safe Planner    |               | - manuals.md     |
| - Deterministic  |           | - Evidence Audit  |               | - Vector Store   |
+------------------+           | - Resolution Rev  |               +------------------+
                               +---------+---------+
                                         |
                                         v
                               +-------------------+
                               | TCS GenAI Lab     |
                               | (MaaS OpenAI REST)|
                               +-------------------+
```

---

## 2. Architecture & File Manifest

| File / Path | Responsibility |
| :--- | :--- |
| `verify_lab_connectivity.py` | Standalone pre-flight verification script validating environment, MaaS LLM ping, embedding endpoint, and `OPT-001` error code query with an ASCII telemetry summary. |
| `run_all.sh` | Shell launcher for Linux Fresco VM running pre-flight verification, background FastAPI, and foreground Streamlit console. |
| `run_all.bat` | Batch launcher for Windows environment service orchestration. |
| `data/error_codes.json` | Structured diagnostic database containing error codes (including `OPT-001`, `ERR-ARPX-101`, `ERR-CS4K-215`), symptoms, severity, and technician authorization flags. |
| `data/industrial_manuals.md` | Formal multi-section equipment service manual covering specifications, sequential procedures, and safety boundaries. |
| `src/config.py` | Configuration management reading `.env` and defaults matching the TCS GenAI Lab gateway. |
| `src/tools.py` | Deterministic diagnostic tools (`lookup_error_code`, `get_component_checklist`) with structured schema returns and exception handling. |
| `src/agents.py` | Core multi-agent reasoning: Symptom Clarifier, Vector Retrieval (with remote `OpenAIEmbeddings` and local offline fallback), Compatibility Gate, Safe-Step Planner, Memory & Evidence Timeline, and Resolution Review Agent. |
| `src/api.py` | Production FastAPI application exposing `/api/diagnose`, `/api/timeline/{session_id}`, `/api/escalate/{session_id}`, and `/health`. |
| `app.py` | Streamlit operations console styled with industrial engineering CSS (slate backgrounds, `#334155` borders, monospace traces). |
| `requirements.txt` | Cleanly pinned production dependencies. |
| `.env.example` | Template for TCS GenAI Lab MaaS gateway parameters. |

---

## 3. TCS GenAI Lab Environment Alignment

The application is pre-configured with the following gateway specifications in [src/config.py](file:///c:/Users/Aryan/Desktop/Rice%20wali%20ka%20project/src/config.py) and [.env.example](file:///c:/Users/Aryan/Desktop/Rice%20wali%20ka%20project/.env.example):

```bash
# TCS GenAI Lab Model-as-a-Service (MaaS) OpenAI-Compatible REST Gateway
MAAS_API_BASE_URL="https://genailab.tcs.in/v1"
MAAS_API_KEY="your_tcs_genai_lab_api_key_here"
MODEL_NAME="azure/genailab-maas-gpt-4o-mini"
EMBEDDING_MODEL_NAME="azure/genailab-maas-text-embedding-3-large"

# Network Host & Port Configurations
API_HOST="0.0.0.0"
API_PORT=8000
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS="0.0.0.0"
```

> **Airgapped / Offline Sandbox Resiliency:**
> If `MAAS_API_KEY` is omitted or if the TCS GenAI Lab endpoint is unreachable from within an isolated Fresco sandbox, the system automatically falls back to its deterministic rule-based industrial diagnostic engine. This guarantees zero downtime and zero crash risk in isolated test networks.

---

## 4. Runbook & Startup Instructions

### Step 1: Pre-flight Verification (Fresco VM)
Run the standalone diagnostic verification script:
```bash
python verify_lab_connectivity.py
```
This runs a 5-point subsystem check:
1. Environment & Configuration Check
2. Diagnostic Error Code Database Query (`OPT-001`)
3. MaaS ChatOpenAI LLM Gateway Ping (`azure/genailab-maas-gpt-4o-mini`)
4. MaaS Text Embedding 3 Large Endpoint Ping (`azure/genailab-maas-text-embedding-3-large`)
5. Multi-Agent Knowledge Retrieval & Safe-Step Sequencer

### Step 2: One-Command Service Launcher
#### On Linux Fresco VM:
```bash
chmod +x run_all.sh
./run_all.sh
```
This script:
1. Runs `verify_lab_connectivity.py`.
2. Starts FastAPI in the background (`nohup uvicorn src.api:app --host 0.0.0.0 --port 8000 &`).
3. Launches Streamlit on `0.0.0.0:8501`.

#### On Windows:
```cmd
run_all.bat
```

---

## 5. API Reference

### `POST /api/diagnose`
Main diagnostic loop managing session state, symptom verification, safe-step sequencing, and observation auditing.

**Request Payload:**
```json
{
  "session_id": "SESS-ALPHA-01",
  "message": "Model: Apex Router Pro-X, Firmware: v4.2.0, Environment: Datacenter Cold Aisle, Code: OPT-001",
  "model_id": "Apex Router Pro-X",
  "firmware_version": "v4.2.0",
  "operating_environment": "Datacenter Cold Aisle",
  "error_code": "OPT-001"
}
```

### `GET /api/timeline/{session_id}`
Returns the immutable chronological evidence audit log for the session.

### `POST /api/escalate/{session_id}`
Forces immediate generation and compilation of the formal incident escalation record.

### `GET /health`
Standard health check verifying operational readiness and supported hardware models.
