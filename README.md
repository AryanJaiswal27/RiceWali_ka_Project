# AI Product Manual Troubleshooting Assistant
### TCS GenAI Lab Enterprise Diagnostic System - Appliance Service Engineering Standard

---

## 1. System Overview

The **AI Product Manual Troubleshooting Assistant** is an enterprise-grade field engineering diagnostics platform aligned with the **TCS GenAI Lab Model-as-a-Service (MaaS) gateway**. It provides automated, deterministic procedural troubleshooting for 4 target consumer/commercial appliance service platforms:
1. **Bosch 800 Series / Ascenta Dishwasher** (`BOSCH_SHEM78`: SHEM78****, SHPM78****)
2. **Whirlpool Front-Load Washer** (`WHIRLPOOL_WASHER_ALPHA`: Alpha / VMW Architecture)
3. **LG Smart French-Door Refrigerator** (`LG_REFRIG_LFXS`: LFXS / LRFCS Series - Inverter Linear Compressor)
4. **Breville Dual Boiler Espresso Machine** (`BREVILLE_BES920`: BES920XL / BES980XL Oracle Series)

The system enforces corporate IT standards: clear modular architecture, deterministic tool execution, strict safety boundary interlocks, dual-mode online/offline operation, and a high-contrast industrial operations console.

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
| - Component Check|           | - Compat Gate     |               | - manuals.md     |
| - Subsystems     |           | - Safe Planner    |               | - Vector Store   |
| (Drain, Optical, |           | - Evidence Audit  |               +------------------+
|  Hydraul, Invert,|           | - Resolution Rev  |
|  Thermal)        |           +---------+---------+
+------------------+                     |
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
| `verify_lab_connectivity.py` | Standalone pre-flight verification script testing environment, error codes across all 4 platforms (`E25`, `F06 E01`, `BLNK-5`, `Er01`), MaaS LLM / embedding pings, and compatibility gate enforcement with ASCII summary report. |
| `run_all.sh` | Shell launcher for Linux Fresco VM running pre-flight verification, background FastAPI (port 8000), and foreground Streamlit console (port 8501). |
| `run_all.bat` | Batch launcher for Windows environment service orchestration. |
| `data/error_codes.json` | Structured diagnostic database covering the 4 platforms: `E15`, `E24`, `E25`, `E27`, `F06 E01`, `F03 E01`, `F08 E01`, `BLNK-5`, `BLNK-6`, `DH-ERR`, `Er01`, `Er02`, `Er03`. |
| `data/industrial_manuals.md` | Formal multi-section equipment service manual covering specifications, board revisions, sequential procedures, and safety boundaries. |
| `src/config.py` | Configuration management reading `.env` and defaults matching the TCS GenAI Lab gateway. |
| `src/tools.py` | Deterministic diagnostic tools (`lookup_error_code`, `get_component_checklist`) supporting Drainage, Optical, Hydraulic, Inverter, and Thermal subsystems. |
| `src/agents.py` | Core multi-agent reasoning: Symptom Clarifier, LangChain Vector Retrieval (with remote `OpenAIEmbeddings` and local offline fallback), Compatibility Gate, Safe-Step Planner, Evidence Timeline, and Resolution Review Agent. |
| `src/api.py` | Production FastAPI application exposing `/api/diagnose`, `/api/timeline/{session_id}`, `/api/escalate/{session_id}`, `/health`, and `/api/models`. |
| `app.py` | High-density Streamlit console with active asset selector, diagnostic terminal, crimson safety banners, observation presets, confidence meter, and audit downloads. |

---

## 3. Supported Equipment Platforms & Safety Boundaries

### 1. Bosch 800 Series / Ascenta Dishwasher (`BOSCH_SHEM78`)
- **Board Revisions:** Rev C / Rev E (MCU 4.18.2)
- **Error Codes:** `E15` (Flood float triggered), `E24`/`E25` (Drain pump impeller blocked), `E27` (Voltage sag < 98V AC)
- **Safety Warning:** **240V Base Pan Electrical Hazard** (Power module, PTC heater contacts, BLDC heat pump).

### 2. Whirlpool Front-Load Washer (`WHIRLPOOL_WASHER_ALPHA`)
- **Platform Architecture:** Alpha / Vertical Modular Washer (VMW) Front-Load (W11663204 Rev B)
- **Board Revisions:** Rev B3 / Rev C1 (ACU Part # W11419171)
- **Error Codes:** `F06 E01` (Tachometer failure), `F03 E01` (Pressure sensor fault), `F08 E01` (Wash heater drive failure)
- **Safety Warning:** **Direct-Drive Capacitor Discharge (400V DC) & 1200 RPM Spin-Basket Kinetic Interlock**.

### 3. LG Smart French-Door Refrigerator (`LG_REFRIG_LFXS`)
- **Compressor Architecture:** Linear Inverter Compressor (FLB075LANA / FLA108LANA)
- **Board Revisions:** Rev 4.2 / Rev 5.0 (EBR822304*)
- **Error Codes:** `BLNK-5` (Inverter locked rotor), `BLNK-6` (Drive overcurrent trip), `DH-ERR` (Defrost cycle timeout)
- **Safety Warning:** **Flammable R600a Isobutane Refrigerant Isolation (EPA Universal certification required; flameless Lokring fittings) & 3-Minute PCB Bleed-Down Delay**.

### 4. Breville Dual Boiler Espresso Machine (`BREVILLE_BES920`)
- **Boiler Architecture:** Dual Independent Stainless Steel Boilers (Brew: 0.3L, Steam: 0.9L)
- **Board Revisions:** Rev 3.4 / Rev 4.1 (Main Power Board + Digital Logic PCB)
- **Error Codes:** `Er01` (Steam boiler fill timeout), `Er02` (Grouphead thermal runaway > 105C), `Er03` (NTC steam boiler open circuit)
- **Safety Warning:** **15-Bar Pressurized Steam Boiler Scalding & Brass Solenoid Teardown Boundary (45-minute cool-down & manual petcock depressurization required)**.

---

## 4. Multi-Agent Reasoning Pipeline

1. **Symptom Clarifier Agent:** Ensures model and symptom/code are established. Prompts for clarification if inputs are vague.
2. **Compatibility Gate:** Filters manual vector chunks strictly by the verified `model_id`. Prevents cross-model confusion.
3. **Safe-Step Planner:** Ranks diagnostic steps from least disruptive (clean filters, panel resets) to advanced. Halts with deterministic safety interlock if a step requires an Authorized Field Technician.
4. **Evidence Timeline:** Appends every action, timestamp, operator observation, and status (`VERIFIED_NORMAL`, `VERIFIED_ABNORMAL`, `BLOCKED`).
5. **Resolution Review Agent:** Recalculates Resolution Confidence (0-100%). Emits next step, `FAULT RESOLVED` (98%), or formal Escalation Package.

---

## 5. API Reference (`src/api.py`)

- `GET /health`: Operational readiness ping.
- `GET /api/models`: Returns list of the 4 supported appliance platforms.
- `POST /api/diagnose`: Main diagnostic conversational turn.
- `GET /api/timeline/{session_id}`: Retrieves chronological evidence history.
- `POST /api/escalate/{session_id}`: Compiles formal escalation JSON payload.
- `GET /api/codes`: Returns list of error codes.
- `GET /api/codes/{code}`: Returns metadata for a specific error code.

---

## 6. Execution & Verification

### Running the Subsystem Verification Script
```bash
python verify_lab_connectivity.py
```

### Starting All Services (Windows)
```cmd
run_all.bat
```

### Starting All Services (Linux VM)
```bash
chmod +x run_all.sh
./run_all.sh
```
- FastAPI Backend: `http://localhost:8000` (Docs: `http://localhost:8000/docs`)
- Streamlit Console: `http://localhost:8501`
