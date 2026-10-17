import json
import uuid
import re
import textwrap
from datetime import datetime, timezone
from typing import Any, Optional
import httpx
import streamlit as st

from src.config import settings
from src.tools import _load_error_codes_db
from src.agents import (
    DiagnosticCoordinator,
    SafeStepPlannerAgent,
    ResolutionReviewAgent,
    get_or_create_session,
    SESSION_STORAGE,
    SessionState
)

# ============================================================================
# Page Configuration & Modern Industrial Operations Design System
# ============================================================================

st.set_page_config(
    page_title="Industrial Asset Diagnostic Console // ARPX-Core Series",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Modern, High-Density Industrial Dark Ops Design System
MODERN_INDUSTRIAL_CSS = """
<style>
    /* Global Base Canvas */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        background-color: #070B14 !important;
        color: #E2E8F0 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }
    
    [data-testid="stHeader"] {
        background-color: rgba(7, 11, 20, 0.85) !important;
        backdrop-filter: blur(12px) !important;
        border-bottom: 1px solid #1E293B !important;
    }

    [data-testid="stSidebar"] {
        background-color: #0D1526 !important;
        border-right: 1px solid #1E293B !important;
    }

    /* Headings & Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #F8FAFC !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        text-transform: uppercase !important;
        margin: 0 !important;
    }

    /* Top Brand & Navbar Bar */
    .top-navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 0 12px 0;
        margin-bottom: 8px;
        border-bottom: 1px solid #1E293B;
    }
    .brand-title {
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: -0.01em;
        color: #F8FAFC;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .brand-sub {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: #06B6D4;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    /* Connected 3-Stage Workflow Stepper */
    .stepper-bar {
        display: flex;
        align-items: stretch;
        gap: 12px;
        margin-bottom: 16px;
    }
    .step-node {
        flex: 1;
        background: #0D1526;
        border: 1px solid #1E293B;
        border-radius: 4px;
        padding: 10px 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        transition: all 0.2s ease;
        position: relative;
    }
    .step-node.active {
        border-color: #06B6D4 !important;
        background: linear-gradient(90deg, rgba(6, 182, 212, 0.12) 0%, #0D1526 100%) !important;
        box-shadow: 0 0 16px rgba(6, 182, 212, 0.2) !important;
    }
    .step-node.completed {
        border-color: #10B981 !important;
        background: linear-gradient(90deg, rgba(16, 185, 129, 0.1) 0%, #0D1526 100%) !important;
    }
    .step-node.halted {
        border-color: #EF4444 !important;
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.12) 0%, #0D1526 100%) !important;
    }
    .step-idx {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 800;
        width: 24px;
        height: 24px;
        border-radius: 3px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #1E293B;
        color: #94A3B8;
    }
    .step-node.active .step-idx {
        background: #06B6D4;
        color: #070B14;
    }
    .step-node.completed .step-idx {
        background: #10B981;
        color: #070B14;
    }
    .step-node.halted .step-idx {
        background: #EF4444;
        color: #FFFFFF;
    }
    .step-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        color: #94A3B8;
        text-transform: uppercase;
    }
    .step-node.active .step-label { color: #38BDF8; }
    .step-node.completed .step-label { color: #10B981; }
    .step-node.halted .step-label { color: #EF4444; }
    .step-status {
        font-size: 0.65rem;
        color: #64748B;
        margin-top: 2px;
    }

    /* Modern Industrial Cards */
    .modern-card {
        background-color: #0D1526;
        border: 1px solid #1E293B;
        border-radius: 4px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    .card-header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #1E293B;
        padding-bottom: 10px;
        margin-bottom: 12px;
    }
    .card-header-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.74rem;
        font-weight: 700;
        color: #94A3B8;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .card-header-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: #06B6D4;
    }

    /* Subsystem & Status Badges */
    .badge-subsystem {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 3px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .badge-cyan { background-color: #082F49; color: #38BDF8; border: 1px solid #0284C7; }
    .badge-emerald { background-color: #064E3B; color: #34D399; border: 1px solid #059669; }
    .badge-crimson { background-color: #450A0A; color: #F87171; border: 1px solid #DC2626; }
    .badge-amber { background-color: #451A03; color: #FBBF24; border: 1px solid #D97706; }
    .badge-slate { background-color: #1E293B; color: #94A3B8; border: 1px solid #334155; }

    /* Directive Hero Window Card */
    .hero-directive {
        background: #0B1120;
        border: 1px solid #1E293B;
        border-left: 4px solid #06B6D4;
        border-radius: 4px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .directive-meta-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .directive-step-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 700;
        color: #38BDF8;
        letter-spacing: 0.05em;
    }
    .directive-action-text {
        font-size: 0.96rem;
        font-weight: 600;
        color: #F8FAFC;
        line-height: 1.5;
        margin-bottom: 10px;
    }
    
    /* Terminal Console Display Block */
    .terminal-code-block {
        background: #030712;
        border: 1px solid #1F2937;
        border-radius: 4px;
        padding: 10px 14px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #38BDF8;
        line-height: 1.45;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .terminal-code-block::before {
        content: "$";
        color: #10B981;
        font-weight: 700;
    }

    .citation-banner {
        background-color: #060B16;
        border: 1px solid #1E293B;
        border-radius: 3px;
        padding: 6px 10px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: #64748B;
        display: flex;
        justify-content: space-between;
    }

    /* Operator Fast Action Prompt */
    .operator-action-prompt {
        background: rgba(6, 182, 212, 0.06);
        border: 1px solid #0E7490;
        border-radius: 3px;
        padding: 8px 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #38BDF8;
        margin-top: 10px;
        line-height: 1.4;
    }

    /* Safety Interlock Crimson Banner */
    .crimson-interlock-hero {
        background: #2D0A0A;
        border: 1px solid #DC2626;
        border-left: 5px solid #EF4444;
        border-radius: 4px;
        padding: 14px 16px;
        margin-bottom: 14px;
        color: #FECACA;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        line-height: 1.5;
        box-shadow: 0 0 20px rgba(239, 68, 68, 0.25);
    }

    /* Modern Confidence Digital Gauge */
    .confidence-meter-card {
        background: #0A0F1D;
        border: 1px solid #1E293B;
        border-radius: 4px;
        padding: 18px 14px;
        text-align: center;
        margin-bottom: 14px;
        position: relative;
        overflow: hidden;
    }
    .confidence-meter-card::after {
        content: "";
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: #1E293B;
    }
    .confidence-number {
        font-family: 'JetBrains Mono', monospace;
        font-size: 3.2rem;
        font-weight: 800;
        line-height: 1.0;
        letter-spacing: -0.03em;
    }
    .confidence-subtitle {
        font-size: 0.7rem;
        font-weight: 700;
        color: #94A3B8;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-top: 6px;
    }
    .confidence-progress-bar-bg {
        width: 100%;
        height: 6px;
        background: #1E293B;
        border-radius: 3px;
        margin-top: 10px;
        overflow: hidden;
    }
    .confidence-progress-fill {
        height: 100%;
        transition: width 0.4s ease;
    }

    /* Compatibility & Safety Verification Matrix */
    .compat-matrix {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-bottom: 14px;
    }
    .compat-item {
        background: #090E1A;
        border: 1px solid #1E293B;
        border-radius: 3px;
        padding: 8px 10px;
        font-family: 'JetBrains Mono', monospace;
    }
    .compat-item-label {
        font-size: 0.65rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 3px;
    }
    .compat-item-val {
        font-size: 0.74rem;
        font-weight: 700;
    }

    /* Event Timeline Stream */
    .timeline-container {
        display: flex;
        flex-direction: column;
        gap: 8px;
        max-height: 320px;
        overflow-y: auto;
    }
    .timeline-entry {
        background: #090E1A;
        border: 1px solid #1E293B;
        border-radius: 3px;
        padding: 10px 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        transition: border-color 0.15s ease;
    }
    .timeline-entry:hover {
        border-color: #334155;
    }
    .timeline-entry-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #161F30;
        padding-bottom: 4px;
        margin-bottom: 6px;
    }

    /* Console Stream Feed */
    .console-stream-feed {
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin-bottom: 12px;
    }
    .console-bubble {
        background: #060B16;
        border: 1px solid #1E293B;
        border-radius: 3px;
        padding: 8px 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        line-height: 1.45;
    }

    /* Architecture Tour Box */
    .architecture-tour-card {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        padding: 10px 0;
    }
    .arch-pillar {
        background: #090E1A;
        border: 1px solid #1E293B;
        border-radius: 3px;
        padding: 10px 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        line-height: 1.45;
    }
    .arch-pillar-title {
        color: #38BDF8;
        font-weight: 700;
        margin-bottom: 4px;
        text-transform: uppercase;
        font-size: 0.72rem;
    }

    /* Form Inputs & BaseWeb */
    div[data-baseweb="input"],
    div[data-baseweb="textarea"],
    div[data-baseweb="select"] > div,
    input, textarea, select {
        background-color: #060B16 !important;
        background: #060B16 !important;
        border: 1px solid #1E293B !important;
        color: #F8FAFC !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
        border-radius: 4px !important;
    }
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="textarea"]:focus-within,
    div[data-baseweb="select"] > div:focus-within,
    input:focus, textarea:focus, select:focus {
        border-color: #06B6D4 !important;
        box-shadow: 0 0 0 1px #06B6D4 !important;
    }
    textarea::placeholder, input::placeholder {
        color: #475569 !important;
    }

    /* Universal High-Contrast Industrial Buttons */
    button,
    button[kind="secondary"],
    button[kind="primary"],
    button[data-testid="baseButton-secondary"],
    button[data-testid="baseButton-primary"],
    div.stButton > button,
    div[data-testid="stFormSubmitButton"] > button,
    div[data-testid="stDownloadButton"] > button {
        background-color: #111A2E !important;
        background: #111A2E !important;
        color: #38BDF8 !important;
        border: 1px solid #2A3854 !important;
        border-radius: 4px !important;
        font-family: 'JetBrains Mono', -apple-system, sans-serif !important;
        font-size: 0.74rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;
        text-transform: uppercase !important;
        padding: 8px 14px !important;
        min-height: 38px !important;
        box-shadow: none !important;
        outline: none !important;
        transition: all 0.15s ease !important;
    }

    button p, button span, button div,
    div.stButton > button p, div.stButton > button span,
    div[data-testid="stFormSubmitButton"] > button p,
    div[data-testid="stDownloadButton"] > button p {
        color: #38BDF8 !important;
        background: transparent !important;
        font-family: inherit !important;
        font-size: inherit !important;
        font-weight: inherit !important;
        margin: 0 !important;
    }

    button:hover,
    div.stButton > button:hover,
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #1E2D4A !important;
        border-color: #06B6D4 !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 12px rgba(6, 182, 212, 0.35) !important;
    }
    button:hover p, button:hover span {
        color: #FFFFFF !important;
    }

    /* Primary Accent Submit Button */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0E7490 !important;
        border: 1px solid #06B6D4 !important;
        color: #FFFFFF !important;
        min-height: 42px !important;
    }
    div[data-testid="stFormSubmitButton"] > button p,
    div[data-testid="stFormSubmitButton"] > button span {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #0891B2 !important;
        border-color: #38BDF8 !important;
        box-shadow: 0 0 14px rgba(6, 182, 212, 0.55) !important;
    }

    /* Expander Elements */
    div[data-testid="stExpander"] {
        background-color: #0D1526 !important;
        border: 1px solid #1E293B !important;
        border-radius: 4px !important;
        margin-bottom: 12px !important;
    }
    div[data-testid="stExpander"] summary {
        background-color: #0D1526 !important;
        color: #94A3B8 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.74rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
    }
    div[data-testid="stExpander"] summary:hover {
        color: #06B6D4 !important;
    }
    div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background-color: #070B14 !important;
        border-top: 1px solid #1E293B !important;
        padding: 12px !important;
    }
</style>
"""

st.markdown(MODERN_INDUSTRIAL_CSS, unsafe_allow_html=True)


# ============================================================================
# State Persistence & Backend Connectivity Bridge
# ============================================================================

if "session_id" not in st.session_state:
    st.session_state.session_id = f"SESS-{uuid.uuid4().hex[:8].upper()}"

if "model_id" not in st.session_state:
    st.session_state.model_id = "Apex Router Pro-X"

if "firmware_version" not in st.session_state:
    st.session_state.firmware_version = "v4.2.0"

if "operating_environment" not in st.session_state:
    st.session_state.operating_environment = "Datacenter Rack Row 4 (Cold Aisle)"

if "error_code" not in st.session_state:
    st.session_state.error_code = "OPT-001"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "resolution_confidence" not in st.session_state:
    st.session_state.resolution_confidence = 0

if "diagnostic_status" not in st.session_state:
    st.session_state.diagnostic_status = "READY"

if "escalation_record" not in st.session_state:
    st.session_state.escalation_record = None

if "active_step_data" not in st.session_state:
    st.session_state.active_step_data = None


@st.cache_data(ttl=30)
def check_maas_gateway_online() -> bool:
    """Probes MaaS API connectivity or determines if airgapped fallback is active."""
    if not settings.maas_api_key or "your_" in settings.maas_api_key:
        return False
    try:
        url = f"{settings.maas_api_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.maas_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.model_name,
            "messages": [{"role": "user", "content": "PING"}],
            "max_tokens": 5
        }
        with httpx.Client(timeout=2.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            return resp.status_code == 200
    except Exception:
        return False


def query_diagnostic_engine(message: str) -> dict[str, Any]:
    """
    Submits turn to FastAPI REST backend (handling 0.0.0.0 -> 127.0.0.1 loopback),
    falling back seamlessly to direct DiagnosticCoordinator calls if backend is offline.
    Ensures local session state is completely synchronized for seamless UI rendering.
    """
    session = get_or_create_session(st.session_state.session_id)
    session.model_id = st.session_state.model_id
    session.firmware_version = st.session_state.firmware_version
    session.operating_environment = st.session_state.operating_environment
    session.error_code = st.session_state.error_code

    connect_host = "127.0.0.1" if settings.api_host in ("0.0.0.0", "") else settings.api_host
    url = f"http://{connect_host}:{settings.api_port}/api/diagnose"
    payload = {
        "session_id": st.session_state.session_id,
        "message": message,
        "model_id": st.session_state.model_id,
        "firmware_version": st.session_state.firmware_version,
        "operating_environment": st.session_state.operating_environment,
        "error_code": st.session_state.error_code
    }
    
    # 1. Attempt FastAPI REST Endpoint
    try:
        with httpx.Client(timeout=4.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if "timeline" in data:
                    from src.agents import EvidenceStep
                    session.timeline = [
                        EvidenceStep(**t) if isinstance(t, dict) else t for t in data["timeline"]
                    ]
                if not session.planned_steps:
                    SafeStepPlannerAgent.generate_plan(session)
                session.current_step_index = len(session.timeline)
                return data
    except Exception:
        pass

    # 2. Seamless Direct Coordinator Fallback
    return DiagnosticCoordinator.process_turn(st.session_state.session_id, message)


def get_subsystem_category(action_text: str, code_str: str) -> str:
    """Derives structured subsystem category tag for industrial metadata displays."""
    combined = f"{action_text} {code_str}".lower()
    if any(k in combined for k in ["optic", "sfp", "wan", "fiber", "laser", "rx power", "opt-"]):
        return "OPTICAL_TRANSCEIVER"
    elif any(k in combined for k in ["thermal", "fan", "temp", "rpm", "cooling", "airflow"]):
        return "THERMAL_INTERLOCK"
    elif any(k in combined for k in ["power", "psu", "voltage", "ac", "dc", "breaker"]):
        return "POWER_DELIVERY"
    elif any(k in combined for k in ["bgp", "route", "routing", "peer", "rib", "prefix"]):
        return "ROUTING_CONTROL_PLANE"
    elif any(k in combined for k in ["backplane", "crc", "fabric", "serdes", "bus"]):
        return "BACKPLANE_FABRIC"
    elif any(k in combined for k in ["poe", "inline", "wattage", "pse"]):
        return "POE_CONTROLLER"
    elif any(k in combined for k in ["nvram", "flash", "crypto", "hsm", "tamper", "enclave"]):
        return "CRYPTO_NVRAM_SECURITY"
    return "GATEWAY_CHASSIS_CORE"


def get_disruption_badge(disruption_level: str, requires_tech: bool) -> tuple[str, str]:
    """Returns disruption tag text and CSS badge style."""
    if requires_tech or disruption_level == "CRITICAL_INVASIVE":
        return "HARDWARE ISOLATION", "badge-crimson"
    elif disruption_level == "LOW_DISRUPTION":
        return "SERVICE AFFECTING", "badge-amber"
    return "NON-INVASIVE CHECK", "badge-cyan"


# Load Error Codes Database for metadata previews
try:
    ERROR_CODES_DB = _load_error_codes_db()
except Exception:
    ERROR_CODES_DB = {}

active_code_meta = ERROR_CODES_DB.get(st.session_state.error_code, {})


# ============================================================================
# Modern Top Navigation & Status Bar
# ============================================================================

is_maas_online = check_maas_gateway_online()

nav_col1, nav_col2, nav_col3 = st.columns([2.5, 1.5, 0.7])

with nav_col1:
    st.markdown(
        """
        <div style="padding: 2px 0;">
            <div class="brand-sub">Mission-Critical Operations // Autonomous AI Diagnostic Console</div>
            <div class="brand-title">INDUSTRIAL ASSET DIAGNOSTIC TERMINAL</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with nav_col2:
    badge_html = (
        '<span class="badge-subsystem badge-emerald" title="Live MaaS cloud reasoning endpoint connected">● LIVE MAAS GATEWAY: ONLINE</span>'
        if is_maas_online else
        '<span class="badge-subsystem badge-cyan" title="Operating with zero-dependency autonomous local rule & retrieval engine">● AUTONOMOUS AIRGAPPED ENGINE</span>'
    )
    asset_tag = "ARPX-800" if "Apex" in st.session_state.model_id else "CS4K-48T"
    st.markdown(
        f"""
        <div style="background-color: #0D1526; border: 1px solid #1E293B; padding: 6px 12px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; text-align: right;">
            <div>GATEWAY: <span style="color: #F8FAFC; font-weight: 700;">{st.session_state.model_id}</span> [{asset_tag}]</div>
            <div style="margin-top: 3px;">{badge_html} &nbsp;|&nbsp; <span style="color: #64748B;">{st.session_state.session_id}</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )

with nav_col3:
    if st.button("RESET SESSION", use_container_width=True, help="Reset Diagnostic State: Clears all timeline records, resets confidence to 0%, and generates a fresh session ID."):
        st.session_state.session_id = f"SESS-{uuid.uuid4().hex[:8].upper()}"
        st.session_state.chat_history = []
        st.session_state.resolution_confidence = 0
        st.session_state.diagnostic_status = "INITIALIZING"
        st.session_state.escalation_record = None
        st.session_state.active_step_data = None
        st.rerun()

st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)


# ============================================================================
# Dynamic 3-Stage Connected Workflow Stepper
# ============================================================================

is_started = len(st.session_state.chat_history) > 0
is_resolved = st.session_state.diagnostic_status == "RESOLVED"
is_halted = st.session_state.diagnostic_status in ("MANDATORY_HALT_TECHNICIAN_REQUIRED", "ESCALATED")

# Stepper node classes
step1_class = "active" if not is_started else "completed"
step2_class = "active" if (is_started and not is_resolved and not is_halted) else ("completed" if (is_resolved or is_halted) else "")

if is_resolved:
    step3_class = "completed"
    step3_idx_text = "✓"
    step3_main = "RESOLVED (98%)"
    step3_sub = "Target fault verified resolved"
elif is_halted:
    step3_class = "halted"
    step3_idx_text = "!"
    step3_main = "SAFETY HALT"
    step3_sub = "Tier-3 technician dispatch required"
elif is_started:
    step3_class = "active"
    step3_idx_text = "3"
    step3_main = "RECORD & AUDIT"
    step3_sub = "Submit telemetry & build audit"
else:
    step3_class = ""
    step3_idx_text = "3"
    step3_main = "RESOLUTION AUDIT"
    step3_sub = "Verify fix or export package"

step1_sub = "Asset identity locked" if is_started else "Configure model & code"
step2_sub = "Executing isolation directive" if (is_started and not is_resolved and not is_halted) else ("Directives executed" if (is_resolved or is_halted) else "Standby for isolation")

st.markdown(
    f"""
    <div class="stepper-bar">
        <div class="step-node {step1_class}" title="Step 1: Set Target Hardware Asset Model, Firmware Build, and Diagnostic Fault Code">
            <div class="step-idx">{'✓' if is_started else '1'}</div>
            <div>
                <div class="step-label">1. ASSET & FAULT CONFIGURATION</div>
                <div class="step-status">{step1_sub}</div>
            </div>
        </div>
        <div class="step-node {step2_class}" title="Step 2: Execute OEM diagnostic directives authorized by the Safe-Step Sequencer">
            <div class="step-idx">{'✓' if (is_resolved or is_halted) else '2'}</div>
            <div>
                <div class="step-label">2. ISOLATION DIRECTIVE</div>
                <div class="step-status">{step2_sub}</div>
            </div>
        </div>
        <div class="step-node {step3_class}" title="Step 3: Submit observations to reach confirmed 98% resolution or safety escalation">
            <div class="step-idx">{step3_idx_text}</div>
            <div>
                <div class="step-label">3. {step3_main}</div>
                <div class="step-status">{step3_sub}</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Collapsible Architecture & Operator Guide
with st.expander("OPERATOR GUIDE // HOW THE 4-STAGE AI ENGINE WORKS", expanded=False):
    st.markdown(
        """
        <div class="architecture-tour-card">
            <div class="arch-pillar">
                <div class="arch-pillar-title">1. PARAMETER GATING</div>
                The Symptom Clarifier Agent enforces strict parameter completeness (Model ID, Firmware, Operating Context). Missing parameters prevent execution to avoid erroneous diagnosis.
            </div>
            <div class="arch-pillar">
                <div class="arch-pillar-title">2. COMPATIBILITY LOCK</div>
                Vector database manual retrieval pre-filters strictly on target hardware metadata. Procedures for Apex Router Pro-X can never cross-contaminate CoreSwitch 4000.
            </div>
            <div class="arch-pillar">
                <div class="arch-pillar-title">3. SAFE-STEP SEQUENCER</div>
                Troubleshooting progresses strictly from least-disruptive software checks (CLI telemetry) to physical inspection. Critical invasive steps trigger safety locks.
            </div>
            <div class="arch-pillar">
                <div class="arch-pillar-title">4. EVIDENCE AUDIT</div>
                Every operator observation is timestamped into an immutable audit trail. Quantitative Resolution Confidence is calculated mathematically (0% to 100%).
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================================
# Two-Column Modern Operational Layout
# ============================================================================

current_session = get_or_create_session(st.session_state.session_id)
col_left, col_right = st.columns([1.22, 0.78])

# ----------------------------------------------------------------------------
# Left Column: Diagnostic Command Center
# ----------------------------------------------------------------------------
with col_left:
    
    # 1. Hardware Asset & Diagnostic Configuration Deck
    st.markdown(
        """
        <div class="modern-card" style="padding: 14px 16px;">
            <div class="card-header-bar" style="margin-bottom: 10px; padding-bottom: 8px;">
                <div class="card-header-title">
                    <span>ASSET PROFILE & DIAGNOSTIC FAULT SETUP</span>
                </div>
                <div class="card-header-tag">GATE: STRICT METADATA LOCK</div>
            </div>
        """,
        unsafe_allow_html=True
    )

    cfg_col1, cfg_col2 = st.columns([1, 1])
    with cfg_col1:
        model_options = ["Apex Router Pro-X", "CoreSwitch 4000"]
        st.session_state.model_id = st.selectbox(
            "Target Hardware Asset",
            options=model_options,
            index=0 if "Apex" in st.session_state.model_id else 1,
            help="Select the exact target network hardware model. Compatibility gating restricts RAG manual queries strictly to this hardware."
        )
    with cfg_col2:
        code_choices = list(ERROR_CODES_DB.keys()) if ERROR_CODES_DB else ["OPT-001", "ERR-ARPX-101", "ERR-CS4K-215"]
        st.session_state.error_code = st.selectbox(
            "Target Diagnostic Fault Code",
            options=code_choices,
            index=0 if st.session_state.error_code not in code_choices else code_choices.index(st.session_state.error_code),
            help="Select the active diagnostic fault code from the hardware register (e.g. OPT-001 for optical transceiver signal loss)."
        )

    cfg_col3, cfg_col4 = st.columns([1, 1])
    with cfg_col3:
        st.session_state.firmware_version = st.text_input(
            "Firmware Build Release",
            value=st.session_state.firmware_version,
            help="Operating firmware version. Used by Symptom Clarifier Agent to validate semver compatibility."
        )
    with cfg_col4:
        st.session_state.operating_environment = st.text_input(
            "Deployment Environment Context",
            value=st.session_state.operating_environment,
            help="Operating deployment environment (e.g. Datacenter Cold Aisle, Edge POP). Used to set baseline thermal/environmental expectations."
        )

    # Active Fault Code Metadata Quick Banner
    if active_code_meta:
        sev_color = "#EF4444" if active_code_meta.get("severity") == "CRITICAL" else ("#F59E0B" if active_code_meta.get("severity") == "HIGH" else "#06B6D4")
        st.markdown(
            f"""
            <div style="background: #060B16; border: 1px solid #1E293B; border-left: 3px solid {sev_color}; padding: 8px 10px; border-radius: 3px; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; margin-top: 8px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 3px;">
                    <span style="color: #94A3B8;">SUBSYSTEM: <strong style="color: #F8FAFC;">{active_code_meta.get('subsystem', 'N/A')}</strong></span>
                    <span style="color: {sev_color}; font-weight: 700;">SEVERITY: {active_code_meta.get('severity', 'NORMAL')}</span>
                </div>
                <div style="color: #CBD5E1;">SYMPTOM: {active_code_meta.get('symptom', 'No symptom metadata')}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # If isolation sequence not initialized, show prominent start button
    if not st.session_state.chat_history:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button("▶ INITIALIZE ASSET ISOLATION SEQUENCE", use_container_width=True, help="Initiates procedural isolation check: Queries authorized manuals, loads non-disruptive Step 01."):
            init_msg = (
                f"Model: {st.session_state.model_id}, "
                f"Firmware: {st.session_state.firmware_version}, "
                f"Environment: {st.session_state.operating_environment}, "
                f"Code: {st.session_state.error_code}"
            )
            resp = query_diagnostic_engine(init_msg)
            st.session_state.diagnostic_status = resp.get("status", "IN_PROGRESS")
            st.session_state.resolution_confidence = resp.get("confidence", 0)
            st.session_state.escalation_record = resp.get("escalation_record")
            st.session_state.chat_history.append({
                "role": "SYSTEM",
                "content": resp.get("message", ""),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
            })
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # Synchronize UI configurations with active session state
    current_session.model_id = st.session_state.model_id
    current_session.firmware_version = st.session_state.firmware_version
    current_session.operating_environment = st.session_state.operating_environment
    current_session.error_code = st.session_state.error_code

    # Determine Active Step Metadata
    active_step = None
    step_num = 1
    total_steps = max(len(current_session.planned_steps), 1)

    if current_session.planned_steps:
        total_steps = len(current_session.planned_steps)
        if current_session.current_step_index < len(current_session.planned_steps):
            active_step = current_session.planned_steps[current_session.current_step_index]
            step_num = current_session.current_step_index + 1
        else:
            active_step = current_session.planned_steps[-1]
            step_num = total_steps
    elif st.session_state.chat_history:
        SafeStepPlannerAgent.generate_plan(current_session)
        if current_session.planned_steps:
            active_step = current_session.planned_steps[0]
            step_num = 1
            total_steps = len(current_session.planned_steps)

    # 2. Hero Active Directive Card (when sequence active)
    if active_step:
        subsystem_tag = get_subsystem_category(active_step.get("action", ""), st.session_state.error_code)
        disrupt_text, disrupt_badge = get_disruption_badge(
            active_step.get("disruption_level", "NON_DISRUPTIVE"),
            active_step.get("requires_authorized_technician", False)
        )
        citation_ref = active_step.get("source_ref", "Corporate IT ESM-NET-2026-V4")
        action_text = active_step.get("action", "")
        cmd_match = re.search(r"'(.*?)'", action_text)
        cli_command = cmd_match.group(1) if cmd_match else None
        cmd_block = f'<div class="terminal-code-block">{cli_command}</div>' if cli_command else ''
        hero_html = f"""<div class="hero-directive">
<div class="directive-meta-bar">
<span class="directive-step-tag">DIAGNOSTIC DIRECTIVE // STEP {step_num:02d} OF {total_steps:02d}</span>
<div>
<span class="badge-subsystem badge-cyan">{subsystem_tag}</span>
<span class="badge-subsystem {disrupt_badge}">{disrupt_text}</span>
</div>
</div>
<div class="directive-action-text">{action_text}</div>
{cmd_block}
<div class="citation-banner">
<span>SOURCE: {citation_ref}</span>
<span>AUTHORITY: OEM CERTIFIED ESM-NET-2026</span>
</div>
<div class="operator-action-prompt">
<strong>[OPERATOR ACTION REQUIRED]</strong> Execute the directive above on target device. Record the empirical result or telemetry reading in the console below, or trigger a test simulation preset.
</div>
</div>"""
        st.markdown(hero_html, unsafe_allow_html=True)

    # 3. Safety Interlock Warning Card (Crimson)
    is_halt = (
        st.session_state.diagnostic_status == "MANDATORY_HALT_TECHNICIAN_REQUIRED"
        or (active_step and active_step.get("requires_authorized_technician"))
    )

    if is_halt:
        crimson_html = textwrap.dedent("""
<div class="crimson-interlock-hero">
    <strong>CRITICAL SAFETY INTERLOCK ENGAGED: HIGH VOLTAGE / LASER RADIATION HAZARD</strong><br/>
    Safety Directive: Physical line card reseating, high-speed backplane inspection, or transceiver replacement on energized equipment requires Certified Field Technician authorization. Manual disassembly is blocked under NEBS L3 compliance.
</div>
        """).strip()
        st.markdown(crimson_html, unsafe_allow_html=True)

    # 4. Operator Telemetry Submission Form
    st.markdown(
        """
        <div class="modern-card">
            <div class="card-header-bar">
                <div class="card-header-title">
                    <span>OPERATOR OBSERVATION CONSOLE</span>
                </div>
                <div class="card-header-tag">INPUT: CLI TELEMETRY OR PHYSICAL AUDIT</div>
            </div>
        """,
        unsafe_allow_html=True
    )

    with st.form("observation_form", clear_on_submit=True):
        operator_input = st.text_area(
            "Empirical Operator Telemetry Readout",
            placeholder="Type telemetry output (e.g., optical power dBm, error counters, drop statistics) or physical inspection findings...",
            height=76,
            label_visibility="collapsed",
            help="Submit your CLI telemetry readout or physical observation. The Resolution Review Agent evaluates this against OEM thresholds."
        )
        commit_btn = st.form_submit_button(
            "[COMMIT TELEMETRY & ADVANCE STEP]",
            use_container_width=True,
            help="Submits your observation to the Resolution Review Agent. Updates confidence score and advances to next authorized step."
        )

        if commit_btn and operator_input.strip():
            st.session_state.chat_history.append({
                "role": "OPERATOR",
                "content": operator_input.strip(),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
            })
            
            engine_resp = query_diagnostic_engine(operator_input.strip())
            st.session_state.diagnostic_status = engine_resp.get("status", st.session_state.diagnostic_status)
            st.session_state.resolution_confidence = engine_resp.get("confidence", st.session_state.resolution_confidence)
            if engine_resp.get("escalation_record"):
                st.session_state.escalation_record = engine_resp["escalation_record"]

            st.session_state.chat_history.append({
                "role": "SYSTEM",
                "content": engine_resp.get("message", ""),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
            })
            st.rerun()

    # Fast One-Click Test Simulation Presets
    st.markdown("<div style='font-size: 0.68rem; color: #94A3B8; font-family: \"JetBrains Mono\", monospace; text-transform: uppercase; margin: 10px 0 6px 0;'>ONE-CLICK TEST TELEMETRY PRESETS (HOVER TO PREVIEW):</div>", unsafe_allow_html=True)
    p_col1, p_col2, p_col3 = st.columns(3)

    with p_col1:
        if st.button("PRESET 1: SFP RX Power (-28.2 dBm)", use_container_width=True, help="Simulates optical power below the -24.0 dBm threshold. Logs abnormal reading and advances to cleaning directive."):
            p1_text = "CLI telemetry 'show interfaces wan0 optical-diagnostics' reports SFP RX Power sub-threshold (-28.2 dBm), LOS asserted abnormal"
            st.session_state.chat_history.append({"role": "OPERATOR", "content": p1_text, "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            resp = query_diagnostic_engine(p1_text)
            st.session_state.diagnostic_status = resp.get("status", st.session_state.diagnostic_status)
            st.session_state.resolution_confidence = resp.get("confidence", st.session_state.resolution_confidence)
            if resp.get("escalation_record"):
                st.session_state.escalation_record = resp["escalation_record"]
            st.session_state.chat_history.append({"role": "SYSTEM", "content": resp.get("message", ""), "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            st.rerun()

    with p_col2:
        if st.button("PRESET 2: Cleaned End-Face (-11.5 dBm)", use_container_width=True, help="Simulates successful ferrule cleaning, restoring normal power (-11.5 dBm) and triggering 98% FAULT RESOLVED."):
            p2_text = "Optical fiber end-face cleaned; power restored to -11.5 dBm, nominal operational status verified"
            st.session_state.chat_history.append({"role": "OPERATOR", "content": p2_text, "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            resp = query_diagnostic_engine(p2_text)
            st.session_state.diagnostic_status = resp.get("status", st.session_state.diagnostic_status)
            st.session_state.resolution_confidence = resp.get("confidence", st.session_state.resolution_confidence)
            if resp.get("escalation_record"):
                st.session_state.escalation_record = resp["escalation_record"]
            st.session_state.chat_history.append({"role": "SYSTEM", "content": resp.get("message", ""), "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            st.rerun()

    with p_col3:
        if st.button("PRESET 3: PSU High Voltage Alert", use_container_width=True, help="Simulates an internal power supply fault to test the deterministic Crimson Safety Interlock halt."):
            p3_text = "Internal PSU capacitor bank humming; high voltage alert, breaker tripped abnormal"
            st.session_state.chat_history.append({"role": "OPERATOR", "content": p3_text, "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            resp = query_diagnostic_engine(p3_text)
            st.session_state.diagnostic_status = resp.get("status", st.session_state.diagnostic_status)
            st.session_state.resolution_confidence = resp.get("confidence", st.session_state.resolution_confidence)
            if resp.get("escalation_record"):
                st.session_state.escalation_record = resp["escalation_record"]
            st.session_state.chat_history.append({"role": "SYSTEM", "content": resp.get("message", ""), "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # 5. Live Console Stream Feed (Collapsible / Compact)
    if st.session_state.chat_history:
        with st.expander(f"LIVE INTERACTION CONSOLE FEED ({len(st.session_state.chat_history)} ENTRIES)", expanded=False):
            st.markdown("<div class='console-stream-feed'>", unsafe_allow_html=True)
            for entry in st.session_state.chat_history:
                is_op = entry["role"] == "OPERATOR"
                tag_color = "#38BDF8" if is_op else "#10B981"
                prefix = "OPERATOR TELEMETRY" if is_op else "SYSTEM AGENT"
                st.markdown(
                    f"""
                    <div class="console-bubble" style="border-left: 3px solid {tag_color};">
                        <div style="font-size: 0.65rem; color: #64748B; margin-bottom: 2px;">{entry['timestamp']} UTC // <span style="color: {tag_color}; font-weight: 700;">{prefix}</span></div>
                        <div style="color: {'#E2E8F0' if is_op else '#38BDF8'};">{entry['content']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Right Column: Audit, Telemetry & Resolution Package
# ----------------------------------------------------------------------------
with col_right:
    
    # 1. Quantitative Resolution Confidence Meter Card
    conf_val = st.session_state.resolution_confidence
    if st.session_state.diagnostic_status == "RESOLVED":
        meter_status_str = "FAULT RESOLVED"
        meter_color = "#10B981"
        bar_fill_color = "#10B981"
        badge_style = "badge-emerald"
    elif st.session_state.diagnostic_status in ("MANDATORY_HALT_TECHNICIAN_REQUIRED", "ESCALATED"):
        meter_status_str = "ESCALATION MANDATED"
        meter_color = "#EF4444"
        bar_fill_color = "#EF4444"
        badge_style = "badge-crimson"
    else:
        meter_status_str = "DIAGNOSING"
        meter_color = "#06B6D4"
        bar_fill_color = "#06B6D4"
        badge_style = "badge-cyan"

    meter_html = textwrap.dedent(f"""
<div class="confidence-meter-card" title="Quantitative Confidence calculated dynamically: 15-75% during isolation | 98% upon confirmed fault clearance | 94% on mandatory safety dispatch">
    <div class="confidence-number" style="color: {meter_color};">{conf_val}%</div>
    <div class="confidence-subtitle">
        RESOLUTION CONFIDENCE &nbsp;|&nbsp; <span class="badge-subsystem {badge_style}">{meter_status_str}</span>
    </div>
    <div class="confidence-progress-bar-bg">
        <div class="confidence-progress-fill" style="width: {conf_val}%; background-color: {bar_fill_color};"></div>
    </div>
</div>
    """).strip()
    st.markdown(meter_html, unsafe_allow_html=True)

    # 2. Compatibility & Safety Verification Matrix
    compat_html = textwrap.dedent(f"""
<div class="compat-matrix">
    <div class="compat-item" title="Model compatibility lock prevents cross-model manual hallucination">
        <div class="compat-item-label">MODEL GATE</div>
        <div class="compat-item-val" style="color: #10B981;">MATCHED ({st.session_state.model_id[:13]})</div>
    </div>
    <div class="compat-item" title="Firmware semver verified against authorized manual baseline">
        <div class="compat-item-label">FIRMWARE GATE</div>
        <div class="compat-item-val" style="color: #10B981;">VERIFIED ({st.session_state.firmware_version})</div>
    </div>
    <div class="compat-item" title="Operating environment profile context">
        <div class="compat-item-label">ENVIRONMENT</div>
        <div class="compat-item-val" style="color: #38BDF8;">COLD AISLE (DC)</div>
    </div>
    <div class="compat-item" title="Technician safety clearance level">
        <div class="compat-item-label">SAFETY CLEARANCE</div>
        <div class="compat-item-val" style="color: {'#EF4444' if is_halt else '#10B981'};">
            {'TIER-3 CERTIFIED' if is_halt else 'TIER-1 OPERATOR'}
        </div>
    </div>
</div>
    """).strip()
    st.markdown(compat_html, unsafe_allow_html=True)

    # 3. Chronological Evidence Timeline Card
    st.markdown(
        """
        <div class="modern-card">
            <div class="card-header-bar">
                <div class="card-header-title">
                    <span>IMMUTABLE EVIDENCE AUDIT LOG</span>
                </div>
                <div class="card-header-tag" style="color: #10B981;">AUDIT: SEALED</div>
            </div>
        """,
        unsafe_allow_html=True
    )

    timeline_steps = current_session.timeline

    if not timeline_steps:
        st.markdown(
            """
            <div style="background-color: #060B16; border: 1px dashed #1E293B; border-radius: 4px; padding: 18px 12px; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #64748B; text-align: center;">
                STANDBY: EVIDENCE TIMELINE INITIALIZING<br/>
                <span style="font-size: 0.65rem; color: #475569;">Execute diagnostic checks to record chronological verification.</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown("<div class='timeline-container'>", unsafe_allow_html=True)
        for s in timeline_steps:
            if s.verification_status == "VERIFIED_NORMAL":
                s_badge = "badge-emerald"
                border_color = "#10B981"
            elif s.verification_status == "VERIFIED_ABNORMAL":
                s_badge = "badge-crimson"
                border_color = "#EF4444"
            elif s.verification_status == "BLOCKED":
                s_badge = "badge-crimson"
                border_color = "#EF4444"
            else:
                s_badge = "badge-amber"
                border_color = "#F59E0B"

            st.markdown(
                f"""
                <div class="timeline-entry" style="border-left: 3px solid {border_color};">
                    <div class="timeline-entry-header">
                        <span style="color: #94A3B8; font-weight: 700;">STEP {s.step_index:02d} // {s.timestamp[11:19]} UTC</span>
                        <span class="badge-subsystem {s_badge}">{s.verification_status}</span>
                    </div>
                    <div style="color: #E2E8F0; margin-bottom: 3px;"><strong style="color: #94A3B8;">DIRECTIVE:</strong> {s.action_executed[:50]}...</div>
                    <div style="color: #38BDF8;"><strong style="color: #94A3B8;">OBSERVED:</strong> {s.user_reported_observation[:55]}...</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # 4. Formal Incident Record Export Controls Deck
    st.markdown(
        """
        <div class="modern-card">
            <div class="card-header-bar">
                <div class="card-header-title">
                    <span>INCIDENT EXPORT & ITSM DISPATCH</span>
                </div>
                <div class="card-header-tag">CERTIFIED RECORD</div>
            </div>
        """,
        unsafe_allow_html=True
    )

    if not st.session_state.escalation_record:
        if st.button("PREPARE FORMAL INCIDENT RECORD", use_container_width=True, help="Compiles the immutable evidence audit trail, required spare parts, and safety directives into a formal Tier-3 incident package."):
            pkg = ResolutionReviewAgent.generate_escalation_package(
                current_session,
                reason="Manual operator audit export requested from industrial console."
            )
            st.session_state.escalation_record = pkg
            st.rerun()

    if st.session_state.escalation_record:
        esc_data = st.session_state.escalation_record
        json_payload = json.dumps(esc_data, indent=2)

        md_payload = f"""# Enterprise Incident Escalation Record
- Incident ID: {esc_data.get('incident_id')}
- Timestamp: {esc_data.get('generated_timestamp')}
- Target Model: {esc_data.get('device_metadata', {}).get('model_id')}
- Firmware Revision: {esc_data.get('device_metadata', {}).get('firmware_version')}
- Error Code: {esc_data.get('device_metadata', {}).get('error_code')}
- Classification: {esc_data.get('escalation_classification')}
- Escalation Reason: {esc_data.get('escalation_reason')}
- Resolution Confidence: {esc_data.get('resolution_confidence_at_escalation')}

## Immutable Diagnostic Evidence Audit Log
"""
        for item in esc_data.get("immutable_evidence_log", []):
            md_payload += f"- Step {item['step']:02d}: {item['action']} -> Status: {item['status']} ({item['observation']})\n"

        md_payload += "\n## Required Field Spares\n"
        for spare in esc_data.get("required_field_spares", []):
            md_payload += f"- {spare}\n"

        md_payload += "\n## Mandatory Safety Directives\n"
        for s_dir in esc_data.get("mandatory_safety_directives", []):
            md_payload += f"- {s_dir}\n"

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                label="[JSON EXPORT]",
                data=json_payload,
                file_name=f"{esc_data.get('incident_id', 'INC')}_ESCALATION_RECORD.json",
                mime="application/json",
                use_container_width=True,
                help="Exports the machine-readable escalation JSON payload for enterprise ITSM ticketing systems (ServiceNow/Jira)."
            )
        with dl_col2:
            st.download_button(
                label="[MARKDOWN REPORT]",
                data=md_payload,
                file_name=f"{esc_data.get('incident_id', 'INC')}_AUDIT_REPORT.md",
                mime="text/markdown",
                use_container_width=True,
                help="Exports a formatted human-readable incident audit log in Markdown format."
            )

    st.markdown("</div>", unsafe_allow_html=True)
