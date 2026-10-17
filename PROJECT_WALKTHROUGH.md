# AI Product Manual Troubleshooting Assistant
## Comprehensive Project Architecture & End-to-End Walkthrough

---

## 1. Executive Problem & Solution Summary

### 1.1 The Real-World Industrial Challenge
In enterprise mission-critical environments (datacenters, telecommunications points-of-presence, and industrial substations), high-availability networking hardware—such as enterprise gateways, optical routers, and modular core switches—must maintain near 100% uptime. When a hardware fault occurs, organizations face three severe operational liabilities:

1. **Astronomical Dispatch Costs & High MTTR (Mean Time to Repair):**
   Dispatching a certified Tier-3 Field Engineer equipped with optical power meters, replacement FRUs (Field Replaceable Units), and torque tools costs between $500 and $2,000 per on-site visit. Up to 40% of physical dispatches result in "No Trouble Found" (NTF) because the issue was merely a dirty fiber connector, unlatched cable, or transient buffer overflow that an L1 site operator could have isolated non-invasively.
2. **Trial-and-Error Troubleshooting & Hardware Degradation:**
   Untrained site operators often perform arbitrary reboots, unseat energized line cards, or power-cycle equipment during flash writes. This trial-and-error approach leads to bootloader corruptions, backplane differential pin bending, and cascading downtime across adjacent network segments.
3. **Severe Physical & Electrical Safety Hazards:**
   Enterprise network equipment contains Class 1M / Class 3R invisible optical laser transmitters (1310nm/1550nm) capable of causing irreversible retinal damage, as well as high-voltage redundant power supply units (maintaining 400V internal DC bus charge for up to 300 seconds post-disconnection). Generative AI systems that freely suggest "open the chassis and check the wiring" pose unacceptable enterprise liability risks.

### 1.2 The Solution: Deterministic AI Troubleshooting Assistant
This project delivers a mission-critical, enterprise-grade diagnostic engine for two specific network gateways:
- **Apex Router Pro-X** (Carrier-grade edge router, Model ID: `ARPX-800`)
- **CoreSwitch 4000** (Modular Layer-3 core switch, Model ID: `CS4K-48T`)

Rather than treating diagnostic guidance as an unconstrained conversational chat, the system orchestrates a **Deterministic Multi-Agent Diagnostic Pipeline**. It enforces strict parameter gating, metadata-filtered compatibility, ordered safe-step sequencing, an immutable chronological evidence audit trail, and deterministic Python-enforced safety interlocks.

### 1.3 High-Level Architecture Journey: Tracing a Request End-to-End
The lifecycle of a diagnostic turn proceeds through six clear stages:

```
[Operator UI] Streamlit Operations Console (app.py)
      |
      | HTTP POST /api/diagnose { session_id, message, model_id, firmware, error_code }
      v
[REST Layer] FastAPI Production Backend (src/api.py)
      |
      | Dispatches payload to DiagnosticCoordinator
      v
[Agent Core] Multi-Agent Diagnostic Orchestrator (src/agents.py)
      |
      +---> Stage 1: Symptom Clarifier Agent
      |        Verifies Model ID, Firmware Revision, and Operating Environment.
      |        If any parameter is missing, execution halts and returns a parameter deficit notice.
      |
      +---> Stage 2: Knowledge Retrieval & Compatibility Gate
      |        Queries ChromaDB / SentenceTransformer vector store and data/error_codes.json.
      |        Strict metadata filtering strips out chunks from non-matching models.
      |
      +---> Stage 3: Safe-Step Planner Agent
      |        Orders approved diagnostic routines from least disruptive to invasive.
      |        If a step requires an "Authorized Field Technician", execution is immediately halted.
      |
      +---> Stage 4: Evidence Timeline State Manager
      |        Appends an immutable chronological record: Step Index, Action, Citation, Observation, Status.
      |
      +---> Stage 5: Resolution Review Agent
      |        Calculates quantitative Resolution Confidence (0-100%).
      |        Yields NEXT_STEP, RESOLUTION_SUMMARY, or INCIDENT_ESCALATION_PACKAGE.
      |
      v
[MaaS Layer] TCS GenAI Lab Gateway (azure/genailab-maas-gpt-4o-mini)
      |
      | Enhances final output phrasing in formal engineering prose (or triggers local fallback if offline).
      v
[Response] Returns structured JSON to app.py -> Updates Telemetry Meter & Audit Log in real time.
```

---

## 2. Comprehensive File-by-File Operational Breakdown

### File 1: `.env.example` and `src/config.py`
- **WHAT:** Configuration boundary defining Model-as-a-Service (MaaS) endpoints, model identifiers, network bind addresses, and persistent file paths.
- **HOW:** `src/config.py` instantiates a Pydantic `SystemSettings` object. It automatically loads key-value pairs from `.env` using `dotenv.load_dotenv()` with a built-in fallback parser for airgapped environments. It defines default configurations:
  * `MAAS_API_BASE_URL="https://genailab.tcs.in/v1"`
  * `MODEL_NAME="azure/genailab-maas-gpt-4o-mini"`
  * `EMBEDDING_MODEL_NAME="azure/genailab-maas-text-embedding-3-large"`
  * `API_HOST="0.0.0.0"`, `API_PORT=8000`
  * `STREAMLIT_SERVER_PORT=8501`, `STREAMLIT_SERVER_ADDRESS="0.0.0.0"`
- **WHY:** Enterprise environments require centralized, 12-factor application configuration. Hardcoding API endpoints or keys inside agent scripts violates corporate security standards and prevents seamless transitions between cloud endpoints and offline Fresco sandboxes.

### File 2: `data/error_codes.json`
- **WHAT:** The authoritative, structured ground-truth database of diagnostic fault codes.
- **HOW:** Formatted as a JSON dictionary indexed by error codes (e.g., `OPT-001`, `ERR-ARPX-101`, `ERR-CS4K-215`). Each entry specifies:
  * `code`: Unique fault identifier.
  * `model`: Targeted network hardware.
  * `subsystem`: Functional domain (`WAN Optical Interface`, `Thermal & Chassis Cooling`, etc.).
  * `severity`: Categorized as `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`.
  * `requires_authorized_technician`: Boolean flag (`true` or `false`).
  * `technician_authorization_boundary`: Plain-language perimeter defining what site operators may touch versus what requires certified engineers.
  * `initial_isolation_checks`: Array of sequential inspection commands.
- **WHY:** Relying solely on unstructured text or LLM memory to recall error codes produces hallucinations. By maintaining an external, deterministic JSON database, error code lookups operate in $O(1)$ time with 100% factual accuracy.

### File 3: `data/industrial_manuals.md`
- **WHAT:** Comprehensive, multi-section OEM service manuals covering hardware specifications, safety directives, and sequential diagnostic procedures for both gateways.
- **HOW:** Structured with markdown headings (`## 1. Safety Directives`, `## 2. Apex Router Pro-X`, `## 3. CoreSwitch 4000`). It establishes physical clearance thresholds, Class 1M laser radiation warnings, 400V bus discharge windows (300 seconds), hot-swap fan tray extraction limits (180 seconds), and SerDes lane backplane bit-error-rate thresholds ($10^{-5}$).
- **WHY:** Industrial manuals represent the authoritative source of truth for field operations. They provide the grounding corpus from which vector embeddings are generated and against which all diagnostic directives are cited.

### File 4: `src/tools.py`
- **WHAT:** Deterministic Python execution tools providing structured diagnostic querying and checklist generation.
- **HOW:** Contains two core public functions:
  * `lookup_error_code(code: str) -> dict`: Queries `data/error_codes.json` using exact and normalized uppercase matching. Returns structured metadata with status `SUCCESS`, `NOT_FOUND`, or `SYSTEM_FAULT`.
  * `get_component_checklist(component: str, model: str) -> list[dict]`: Evaluates component keywords (`optical`, `thermal`, `power`, `routing`, `backplane`, `poe`, `crypto`) and returns structured inspection steps ordered by disruption level (`NON_DISRUPTIVE`, `LOW_DISRUPTION`, `CRITICAL_INVASIVE`).
  * All functions are wrapped in `try/except` blocks to guarantee zero unhandled runtime crashes.
- **WHY:** Tools isolate deterministic data retrieval from LLM reasoning. Rather than having an LLM invent inspection routines, tools query audited corporate datasets and return verified schemas.

### File 5: `src/agents.py`
- **WHAT:** The cognitive core of the system. Hosts the vector retrieval engine, the five collaborative diagnostic agents, and the session state manager.
- **HOW:** 
  * `VectorRetrievalEngine`: Parses `data/industrial_manuals.md` into tagged chunks. Attempts remote embeddings via `OpenAIEmbeddings` using `EMBEDDING_MODEL_NAME`. If remote calls fail or no API key exists, it seamlessly activates the local semantic cosine-similarity engine.
  * `SymptomClarifierAgent`: Evaluates user inputs for missing hardware parameters.
  * `SafeStepPlannerAgent`: Generates and sequences diagnostic checks; implements deterministic halts on technician-flagged steps.
  * `ResolutionReviewAgent`: Evaluates technician observations, updates verification statuses, calculates confidence, and drafts escalation records.
  * `DiagnosticCoordinator`: Orchestrates the pipeline for every conversational turn.
- **WHY:** Monolithic prompts fail when managing multi-turn diagnostic sessions with strict safety requirements. Decomposing the system into specialized, single-responsibility agents ensures complete determinism, auditability, and safety.

### File 6: `src/api.py`
- **WHAT:** Production-grade FastAPI REST application exposing backend services to external dashboards, CLI tools, and automated testing suites.
- **HOW:** Exposes four primary endpoints:
  * `POST /api/diagnose`: Main conversational loop managing session state and returning next steps or resolution packages.
  * `GET /api/timeline/{session_id}`: Returns the complete immutable chronological evidence audit trail.
  * `POST /api/escalate/{session_id}`: Forces incident escalation package generation.
  * `GET /health`: Returns operational readiness, system version, and supported hardware.
  * `GET /api/codes`: Lists all error codes in the corporate database.
- **WHY:** Decoupling the backend from the UI adheres to corporate microservice standards. It allows the core diagnostic engine to be integrated into ticketing systems (e.g., ServiceNow, Jira Service Management) without depending on Streamlit.

### File 7: `app.py`
- **WHAT:** Streamlit operations console styled as a high-density industrial terminal.
- **HOW:** Applies custom CSS (`#0B0F19` canvas, `#111827` panels, `#1F2937` borders, strict monospace typography). Divides the screen into a two-column layout:
  * Left Column: Active Check Card (directive, citation, disruption badge), Safety Interlock Banner, Dialogue Stream, and Operator Observation Input with one-click presets.
  * Right Column: Quantitative Resolution Confidence digital meter, Compatibility Gate Lock table, Chronological Evidence Timeline, and JSON/Markdown export controls.
  * Queries FastAPI via HTTP, with automatic internal fallback to `DiagnosticCoordinator` if the REST server is starting up.
- **WHY:** Enterprise operators in NOCs and SOCs require high-density, distraction-free interfaces. Eliminating playful animations, pastel cards, and conversational pleasantries focuses the operator on safety directives and empirical telemetry.

### File 8: `verify_lab_connectivity.py`
- **WHAT:** Standalone pre-flight verification script for the Fresco VM.
- **HOW:** Executes a 5-subsystem audit:
  1. Validates `.env` and runtime settings.
  2. Executes `lookup_error_code("OPT-001")` and validates ground-truth resolution.
  3. Tests MaaS ChatOpenAI LLM ping via REST/LangChain.
  4. Tests MaaS embedding endpoint with a sample phrase.
  5. Tests the multi-agent vector search and safe planner pipeline.
  Outputs a high-contrast industrial ASCII report with `[PASS]` or `[FAIL]` status for each component.
- **WHY:** Evaluators and operators need immediate confirmation that all system paths are functional before launching web servers. It pinpoints network or credential faults before runtime.

### File 9: `run_all.sh` / `run_all.bat`
- **WHAT:** Single-command service orchestration scripts for Linux and Windows environments.
- **HOW:** In `run_all.sh`:
  1. Runs `python3 verify_lab_connectivity.py`.
  2. Spawns FastAPI in the background: `nohup uvicorn src.api:app --host 0.0.0.0 --port 8000 > fastapi_service.log 2>&1 &`.
  3. Launches Streamlit in the foreground: `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`.
  4. Traps exit signals to terminate background processes cleanly upon shutdown.
- **WHY:** Eliminates manual multi-terminal startup steps and ensures both services bind to all network interfaces (`0.0.0.0`) inside enterprise VMs.

---

## 3. The 5 Core Pillars in Depth

### Pillar 1: Symptom Clarifier (Parameter Gating)
- **The Problem:** Users frequently enter incomplete prompts (e.g., *"My router is flashing amber and dropping packets"*). If an AI begins troubleshooting immediately, it may recommend procedures intended for a CoreSwitch 4000 on an Apex Router Pro-X, causing hardware damage.
- **How It Works:** The `SymptomClarifierAgent` analyzes the input using regular expressions and keyword extractors for three mandatory parameters:
  1. `Model ID` (Must resolve to `Apex Router Pro-X` or `CoreSwitch 4000`)
  2. `Firmware Revision` (Must match semantic versioning, e.g., `v4.2.0`)
  3. `Operating Environment` (Must establish context, e.g., `Datacenter Rack 4 Cold Aisle`)
- **The Gate:** If any parameter is absent, the agent sets status to `PARAM_CLARIFICATION`, halts the pipeline, and issues a structured `[PARAMETER DEFICIT - DIAGNOSTIC GATE HALT]` notice listing the exact missing variables. No procedural checks are retrieved until all three parameters are verified.

### Pillar 2: Compatibility Gate (Preventing Cross-Model Hallucination)
- **The Problem:** In standard RAG systems, a semantic search for *"How to replace fan tray"* retrieves chunks from all manuals in the database. If a technician servicing an Apex Router Pro-X receives fan extraction instructions for a CoreSwitch 4000, they will pull the wrong module and trigger thermal runaway.
- **How It Works:** Every manual chunk in `VectorRetrievalEngine` is permanently tagged with a `model_target` metadata field (`Apex Router Pro-X`, `CoreSwitch 4000`, or `COMMON`). When vector similarity search runs:
  ```python
  if model_filter and model_filter != "COMMON":
      if chunk.model_target != "COMMON" and chunk.model_target.lower() != model_filter.lower():
          continue  # Strip chunk from candidate list
  ```
- **The Result:** Cross-model chunks are mathematically excluded from the prompt context, achieving 0% model-confusion hallucination.

### Pillar 3: Safe-Step Planner (Ordered Checks & Safety Interlocks)
- **The Problem:** Unstructured AI models often suggest invasive actions first (e.g., *"Reboot the switch and swap the motherboard"*). In production, non-disruptive software queries must always precede physical touches. Furthermore, if a step is dangerous, execution must halt unconditionally.
- **How It Works:**
  1. **Disruption Sequencing:** Checks are grouped into three progressive tiers:
     - Tier 1: `NON_DISRUPTIVE` (CLI read-only show commands, optical DOM telemetry).
     - Tier 2: `LOW_DISRUPTION` (Physical patch cord verification, ferrule cleaning, soft BGP refreshes).
     - Tier 3: `CRITICAL_INVASIVE` (Transceiver extraction, line card reseating, fan tray extraction, flash replacement).
  2. **Deterministic Python Safety Interlock:** When candidate steps are evaluated, `SafeStepPlannerAgent` inspects the `requires_authorized_technician` boolean flag. If `True`, the pipeline triggers an immediate status change:
     ```python
     session.diagnostic_status = "MANDATORY_HALT_TECHNICIAN_REQUIRED"
     ```
     Execution halts deterministically in Python code. The prompt instructing the user to disassemble hardware is never sent to the UI. Instead, the UI renders a prominent crimson safety interlock alert and compiles a Tier-3 dispatch package.

### Pillar 4: Memory & Evidence Timeline (Preventing Redundant Loops)
- **The Problem:** In multi-turn chat sessions, LLMs frequently lose track of previous steps and re-suggest actions already performed (e.g., *"Try cleaning the fiber connector again"*).
- **How It Works:** The session state maintains an immutable list of Pydantic `EvidenceStep` objects:
  ```python
  class EvidenceStep(BaseModel):
      step_index: int
      action_executed: str
      source_doc_reference: str
      user_reported_observation: str
      verification_status: str  # VERIFIED_NORMAL, VERIFIED_ABNORMAL, BLOCKED
      timestamp: str
  ```
- **The Result:** The timeline acts as an unalterable flight data recorder. The `ResolutionReviewAgent` inspects the entire history before every decision, ensuring previous steps are never repeated and every claim is substantiated by audited telemetry.

### Pillar 5: Resolution Review Agent (Quantitative Confidence & Formal Escalation)
- **The Problem:** Knowing when to stop troubleshooting is as important as knowing where to start. Systems must objectively distinguish between a resolved issue, an ongoing investigation, and a critical failure requiring human escalation.
- **How It Works:** After each operator observation, the agent evaluates the response using regex word-boundary matching:
  - If the observation confirms recovery (e.g., *"power restored to -11.5 dBm, normal operational"*):
    * `status` transitions to `RESOLVED`
    * `confidence` jumps to `98%`
    * Generates a formal `[RESOLUTION CONFIRMED]` summary.
  - If the observation confirms fault persistence (e.g., *"Rx power is -28.2 dBm, abnormal"*):
    * Status remains `IN_PROGRESS`
    * Confidence recalculates dynamically based on completed progress:
      $$\text{Confidence} = \min\left(75, \frac{\text{Steps Completed}}{\text{Total Steps}} \times 70 + 15\right)$$
    * Loads next approved step.
  - If a safety boundary or procedural exhaustion occurs:
    * Status transitions to `MANDATORY_HALT_TECHNICIAN_REQUIRED` or `ESCALATED`
    * Confidence registers at `92% - 94%` (high certainty that physical intervention is required)
    * Compiles a comprehensive Incident Escalation Record detailing incident ID, metadata, evidence history, required spare parts, and torque ratings for certified human dispatch.
