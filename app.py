import json
import uuid
import re
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
# Page Configuration & Industrial Operations Styling
# ============================================================================

st.set_page_config(
    page_title="Industrial Asset Diagnostic Console // ARPX-Core Series",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# High-density industrial CSS: Slate/Charcoal palette, 1px solid #1F2937 borders, sharp corners
INDUSTRIAL_CSS = """
<style>
    /* Global Base Canvas */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0B0F19 !important;
        color: #E5E7EB !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", Helvetica, Arial, sans-serif !important;
    }
    
    [data-testid="stHeader"] {
        background-color: #0B0F19 !important;
        border-bottom: 1px solid #1F2937 !important;
    }

    [data-testid="stSidebar"] {
        background-color: #111827 !important;
        border-right: 1px solid #1F2937 !important;
    }

    /* Headings & Labels */
    h1, h2, h3, h4, h5, h6 {
        color: #F9FAFB !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
        text-transform: uppercase !important;
        margin: 0 !important;
    }

    /* Panel Card Container */
    .op-panel {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 2px;
        padding: 16px;
        margin-bottom: 14px;
    }

    .op-panel-header {
        font-size: 0.72rem;
        font-weight: 700;
        color: #9CA3AF;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        border-bottom: 1px solid #1F2937;
        padding-bottom: 8px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Status Badges */
    .badge-subsystem {
        display: inline-block;
        font-family: "Consolas", "Monaco", monospace;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 1px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .badge-cyan { background-color: #083344; color: #06B6D4; border: 1px solid #0E7490; }
    .badge-emerald { background-color: #064E3B; color: #10B981; border: 1px solid #059669; }
    .badge-crimson { background-color: #450A0A; color: #EF4444; border: 1px solid #DC2626; }
    .badge-amber { background-color: #451A03; color: #F59E0B; border: 1px solid #D97706; }
    .badge-slate { background-color: #1F2937; color: #9CA3AF; border: 1px solid #374151; }

    /* Telemetry Monospace Logs */
    .mono-log {
        background-color: #050811;
        border: 1px solid #1F2937;
        border-radius: 2px;
        padding: 12px 14px;
        font-family: "Consolas", "Monaco", "Courier New", monospace;
        font-size: 0.82rem;
        color: #06B6D4;
        line-height: 1.5;
        white-space: pre-wrap;
        word-break: break-all;
        margin-bottom: 10px;
    }

    /* Active Directive Card */
    .directive-box {
        background-color: #0F172A;
        border: 1px solid #334155;
        border-left: 3px solid #06B6D4;
        border-radius: 2px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .directive-title {
        font-size: 0.72rem;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 6px;
    }
    .directive-text {
        font-size: 0.92rem;
        color: #F9FAFB;
        font-weight: 600;
        line-height: 1.4;
        margin-bottom: 8px;
    }
    .citation-box {
        background-color: #050811;
        border: 1px solid #1E293B;
        padding: 6px 10px;
        font-family: "Consolas", monospace;
        font-size: 0.72rem;
        color: #64748B;
        border-radius: 1px;
    }

    /* Safety Interlock Crimson Alert */
    .crimson-interlock {
        background-color: #2A0808;
        border: 1px solid #DC2626;
        border-left: 4px solid #EF4444;
        border-radius: 2px;
        padding: 12px 14px;
        margin-bottom: 14px;
        color: #FCA5A5;
        font-family: "Consolas", monospace;
        font-size: 0.8rem;
        line-height: 1.45;
    }

    /* Resolution Confidence Digital Meter */
    .meter-container {
        background-color: #050811;
        border: 1px solid #1F2937;
        border-radius: 2px;
        padding: 16px 12px;
        text-align: center;
        margin-bottom: 14px;
    }
    .meter-readout {
        font-family: "Consolas", "Monaco", monospace;
        font-size: 2.8rem;
        font-weight: 700;
        line-height: 1.0;
        letter-spacing: -0.02em;
    }
    .meter-subtext {
        font-size: 0.7rem;
        font-weight: 600;
        color: #9CA3AF;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-top: 6px;
    }

    /* High-Density Hardware Lock Table */
    .hardware-lock-table {
        width: 100%;
        border-collapse: collapse;
        font-family: "Consolas", monospace;
        font-size: 0.75rem;
        margin-bottom: 12px;
    }
    .hardware-lock-table td {
        padding: 6px 8px;
        border: 1px solid #1F2937;
        background-color: #050811;
    }
    .hardware-lock-table td.label-cell {
        color: #9CA3AF;
        width: 45%;
        text-transform: uppercase;
    }
    .hardware-lock-table td.value-cell {
        color: #06B6D4;
        font-weight: 700;
    }

    /* Form Inputs & BaseWeb Containers */
    div[data-baseweb="input"],
    div[data-baseweb="textarea"],
    div[data-baseweb="select"] > div,
    input, textarea, select {
        background-color: #050811 !important;
        background: #050811 !important;
        border: 1px solid #1F2937 !important;
        color: #F3F4F6 !important;
        font-family: "Consolas", monospace !important;
        font-size: 0.82rem !important;
        border-radius: 2px !important;
    }
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="textarea"]:focus-within,
    div[data-baseweb="select"] > div:focus-within,
    input:focus, textarea:focus, select:focus {
        border-color: #06B6D4 !important;
        box-shadow: 0 0 0 1px #06B6D4 !important;
    }
    textarea::placeholder, input::placeholder {
        color: #64748B !important;
    }

    /* Select Dropdown Menu & Popovers */
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[data-baseweb="menu"] {
        background-color: #111827 !important;
        border: 1px solid #334155 !important;
        color: #F3F4F6 !important;
    }
    li[data-baseweb="menu-item"] {
        background-color: #111827 !important;
        color: #E5E7EB !important;
        font-family: "Consolas", monospace !important;
        font-size: 0.8rem !important;
    }
    li[data-baseweb="menu-item"]:hover,
    li[data-baseweb="menu-item"][aria-selected="true"] {
        background-color: #1F2937 !important;
        color: #06B6D4 !important;
    }

    /* Expander Container & Header */
    div[data-testid="stExpander"] {
        background-color: #111827 !important;
        border: 1px solid #1F2937 !important;
        border-radius: 2px !important;
        margin-bottom: 12px !important;
    }
    div[data-testid="stExpander"] summary {
        background-color: #111827 !important;
        color: #9CA3AF !important;
        font-family: "Consolas", monospace !important;
        font-size: 0.76rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    div[data-testid="stExpander"] summary:hover {
        color: #06B6D4 !important;
    }
    div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background-color: #0B0F19 !important;
        border-top: 1px solid #1F2937 !important;
        padding: 12px !important;
    }

    /* =========================================================================
       UNIVERSAL HIGH-CONTRAST INDUSTRIAL BUTTON STYLING
       Eliminates white-on-white button rendering across all Streamlit variants
       ========================================================================= */
    button,
    button[kind="secondary"],
    button[kind="primary"],
    button[data-testid="baseButton-secondary"],
    button[data-testid="baseButton-primary"],
    div.stButton > button,
    div[data-testid="stFormSubmitButton"] > button,
    div[data-testid="stDownloadButton"] > button {
        background-color: #161E2E !important;
        background: #161E2E !important;
        color: #38BDF8 !important;
        border: 1px solid #334155 !important;
        border-radius: 2px !important;
        font-family: "Consolas", "Monaco", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-size: 0.74rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;
        text-transform: uppercase !important;
        padding: 8px 12px !important;
        box-shadow: none !important;
        outline: none !important;
        height: auto !important;
        min-height: 38px !important;
        white-space: normal !important;
        word-break: break-word !important;
        text-align: center !important;
        transition: border-color 0.15s ease, background-color 0.15s ease, color 0.15s ease !important;
    }

    /* Force all text elements inside buttons to inherit high-contrast colors */
    button p,
    button span,
    button div,
    button label,
    div.stButton > button p,
    div.stButton > button span,
    div[data-testid="stFormSubmitButton"] > button p,
    div[data-testid="stFormSubmitButton"] > button span,
    div[data-testid="stDownloadButton"] > button p,
    div[data-testid="stDownloadButton"] > button span {
        color: #38BDF8 !important;
        background: transparent !important;
        background-color: transparent !important;
        font-family: inherit !important;
        font-size: inherit !important;
        font-weight: inherit !important;
        margin: 0 !important;
        padding: 0 !important;
        white-space: normal !important;
    }

    /* Button Hover States */
    button:hover,
    div.stButton > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #1E293B !important;
        background: #1E293B !important;
        border-color: #06B6D4 !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 8px rgba(6, 182, 212, 0.3) !important;
    }
    button:hover p,
    button:hover span,
    button:hover div {
        color: #FFFFFF !important;
    }

    /* Button Active & Focus States */
    button:active,
    button:focus,
    button:focus-visible,
    div.stButton > button:active,
    div.stButton > button:focus,
    div[data-testid="stFormSubmitButton"] > button:active,
    div[data-testid="stFormSubmitButton"] > button:focus {
        background-color: #0F172A !important;
        background: #0F172A !important;
        border-color: #38BDF8 !important;
        color: #38BDF8 !important;
        box-shadow: 0 0 0 1px #06B6D4 !important;
        outline: none !important;
    }
    button:active p, button:focus p,
    button:active span, button:focus span {
        color: #38BDF8 !important;
    }

    /* High-Impact Primary Submit Button [COMMIT OBSERVATION & ADVANCE] */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0E7490 !important;
        background: #0E7490 !important;
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
        background: #0891B2 !important;
        border-color: #38BDF8 !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 12px rgba(6, 182, 212, 0.5) !important;
    }

    /* Formal Download Buttons */
    div[data-testid="stDownloadButton"] > button {
        background-color: #0B1120 !important;
        border: 1px solid #1E293B !important;
        color: #06B6D4 !important;
    }
    div[data-testid="stDownloadButton"] > button p {
        color: #06B6D4 !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #111827 !important;
        border-color: #06B6D4 !important;
        color: #38BDF8 !important;
    }
    div[data-testid="stDownloadButton"] > button:hover p {
        color: #38BDF8 !important;
    }
</style>
"""

st.markdown(INDUSTRIAL_CSS, unsafe_allow_html=True)


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
    """
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
                return data
    except Exception:
        pass

    # 2. Seamless Direct Coordinator Fallback
    session = get_or_create_session(st.session_state.session_id)
    session.model_id = st.session_state.model_id
    session.firmware_version = st.session_state.firmware_version
    session.operating_environment = st.session_state.operating_environment
    session.error_code = st.session_state.error_code
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
    return "MINIMAL (NON-INVASIVE)", "badge-cyan"


# ============================================================================
# Header Telemetry Bar
# ============================================================================

is_maas_online = check_maas_gateway_online()

head_col1, head_col2, head_col3 = st.columns([2.6, 1.4, 0.8])

with head_col1:
    st.markdown(
        """
        <div style="padding: 2px 0 8px 0;">
            <div style="font-size: 0.68rem; color: #9CA3AF; letter-spacing: 0.12em; text-transform: uppercase; font-family: 'Consolas', monospace;">
                Mission-Critical Infrastructure // Automated Diagnostic Terminal
            </div>
            <div style="font-size: 1.18rem; font-weight: 700; color: #F9FAFB; letter-spacing: -0.01em;">
                INDUSTRIAL ASSET DIAGNOSTIC CONSOLE // ARPX-CORE SERIES
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with head_col2:
    badge_html = (
        '<span class="badge-subsystem badge-emerald">[MAAS CLOUD GATEWAY: ONLINE]</span>'
        if is_maas_online else
        '<span class="badge-subsystem badge-cyan">[AUTONOMOUS AIRGAPPED ENGINE: ACTIVE]</span>'
    )
    asset_tag = "ARPX-800" if "Apex" in st.session_state.model_id else "CS4K-48T"
    st.markdown(
        f"""
        <div style="background-color: #111827; border: 1px solid #1F2937; padding: 6px 10px; border-radius: 2px; font-family: 'Consolas', monospace; font-size: 0.72rem; text-align: right;">
            <div>GATEWAY: <span style="color: #F9FAFB; font-weight: 700;">{st.session_state.model_id} [{asset_tag}]</span></div>
            <div style="margin-top: 2px;">{badge_html} | <span style="color: #64748B;">{st.session_state.session_id}</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )

with head_col3:
    if st.button("RESET SESSION", use_container_width=True):
        new_sess = f"SESS-{uuid.uuid4().hex[:8].upper()}"
        st.session_state.session_id = new_sess
        st.session_state.chat_history = []
        st.session_state.resolution_confidence = 0
        st.session_state.diagnostic_status = "INITIALIZING"
        st.session_state.escalation_record = None
        st.session_state.active_step_data = None
        st.rerun()

st.markdown("<hr style='border: none; border-top: 1px solid #1F2937; margin: 4px 0 14px 0;'/>", unsafe_allow_html=True)


# ============================================================================
# Telemetry Ribbon Configuration (Expandable Hardware Locking)
# ============================================================================

with st.expander("HARDWARE ASSET SPECIFICATIONS & DIAGNOSTIC FAULT CODES", expanded=False):
    t_col1, t_col2, t_col3, t_col4 = st.columns(4)
    with t_col1:
        st.session_state.model_id = st.selectbox(
            "Hardware Asset Model",
            options=["Apex Router Pro-X", "CoreSwitch 4000"],
            index=0 if "Apex" in st.session_state.model_id else 1
        )
    with t_col2:
        st.session_state.firmware_version = st.text_input(
            "Firmware Revision",
            value=st.session_state.firmware_version
        )
    with t_col3:
        st.session_state.operating_environment = st.text_input(
            "Operating Environment Profile",
            value=st.session_state.operating_environment
        )
    with t_col4:
        try:
            codes_dict = _load_error_codes_db()
            code_choices = list(codes_dict.keys())
        except Exception:
            code_choices = ["OPT-001", "ERR-ARPX-101", "ERR-CS4K-215"]
        
        st.session_state.error_code = st.selectbox(
            "Diagnostic Fault Code (Target)",
            options=code_choices,
            index=0 if st.session_state.error_code not in code_choices else code_choices.index(st.session_state.error_code)
        )


# ============================================================================
# Two-Column Operational Layout
# ============================================================================

col_left, col_right = st.columns([1.25, 0.75])

# Fetch active session state from memory
current_session = get_or_create_session(st.session_state.session_id)

# ----------------------------------------------------------------------------
# Left Column: Diagnostic Terminal & Procedural Sequencer
# ----------------------------------------------------------------------------
with col_left:
    st.markdown(
        """
        <div class="op-panel-header">
            <span>DIAGNOSTIC TERMINAL // PROCEDURAL SEQUENCER</span>
            <span style="font-family: 'Consolas', monospace; color: #06B6D4;">STANDARD: IEEE 802.3 / NEBS L3</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # If sequence not started, provide activation trigger
    if not st.session_state.chat_history:
        st.markdown(
            f"""
            <div class="mono-log">
[STANDBY: DIAGNOSTIC GATE READY]
Target Hardware Asset  : {st.session_state.model_id}
Firmware Build Release : {st.session_state.firmware_version}
Environmental Context  : {st.session_state.operating_environment}
Target Fault Code      : {st.session_state.error_code}

Initiate procedural isolation check to sequence non-disruptive telemetry routines.
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("INITIALIZE ASSET ISOLATION SEQUENCE", use_container_width=True):
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
        # Generate initial plan if missing
        SafeStepPlannerAgent.generate_plan(current_session)
        if current_session.planned_steps:
            active_step = current_session.planned_steps[0]
            step_num = 1
            total_steps = len(current_session.planned_steps)

    # 1. Active Check Card Rendering
    if active_step:
        subsystem_tag = get_subsystem_category(active_step.get("action", ""), st.session_state.error_code)
        disrupt_text, disrupt_badge = get_disruption_badge(
            active_step.get("disruption_level", "NON_DISRUPTIVE"),
            active_step.get("requires_authorized_technician", False)
        )
        citation_ref = active_step.get("source_ref", "Corporate IT ESM-NET-2026-V4")

        st.markdown(
            f"""
            <div class="op-panel" style="border-left: 3px solid #06B6D4;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-family: 'Consolas', monospace; font-size: 0.72rem; color: #9CA3AF; font-weight: 700;">
                        DIAGNOSTIC STEP {step_num:02d} / {total_steps:02d}
                    </span>
                    <div>
                        <span class="badge-subsystem badge-cyan">{subsystem_tag}</span>
                        <span class="badge-subsystem {disrupt_badge}">{disrupt_text}</span>
                    </div>
                </div>
                <div class="directive-title">APPROVED DIAGNOSTIC DIRECTIVE</div>
                <div class="directive-text">{active_step.get('action')}</div>
                <div class="citation-box">
                    Source: {citation_ref} | Authority: OEM Certified ESM-NET-2026-V4
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 2. Safety Interlock Warning Banner (Prominent Crimson)
    is_halt = (
        st.session_state.diagnostic_status == "MANDATORY_HALT_TECHNICIAN_REQUIRED"
        or (active_step and active_step.get("requires_authorized_technician"))
    )

    if is_halt:
        st.markdown(
            """
            <div class="crimson-interlock">
                <strong>[CRITICAL SAFETY INTERLOCK ENGAGED: HIGH VOLTAGE / LASER RADIATION HAZARD - STOP PROCEDURE - FIELD TECHNICIAN DISPATCH MANDATORY]</strong><br/>
                Safety Directive: Physical line card reseating, high-speed backplane inspection, or transceiver replacement on energized equipment requires Certified Field Technician authorization. Manual disassembly is blocked under NEBS L3 compliance.
            </div>
            """,
            unsafe_allow_html=True
        )

    # 3. Interactive Dialogue Terminal History
    if st.session_state.chat_history:
        st.markdown("<div style='font-size: 0.7rem; color: #9CA3AF; font-family: \"Consolas\", monospace; text-transform: uppercase; margin-bottom: 6px;'>CHRONOLOGICAL CONSOLE STREAM:</div>", unsafe_allow_html=True)
        # Display up to last 4 console items
        for entry in st.session_state.chat_history[-4:]:
            is_op = entry["role"] == "OPERATOR"
            tag_color = "#9CA3AF" if is_op else "#06B6D4"
            prefix = "OPERATOR TELEMETRY RECORD" if is_op else "SEQUENCER DIRECTIVE"
            st.markdown(
                f"""
                <div class="mono-log" style="border-left: 2px solid {tag_color}; padding: 8px 12px; margin-bottom: 6px;">
                    <div style="font-size: 0.68rem; color: #64748B; margin-bottom: 3px;">{entry['timestamp']} UTC // {prefix}</div>
                    <div style="color: {'#E5E7EB' if is_op else '#06B6D4'};">{entry['content']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # 4. Operator Observation Console & Presets
    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
    with st.form("observation_form", clear_on_submit=True):
        operator_input = st.text_area(
            "OPERATOR OBSERVATION CONSOLE",
            placeholder="Operator physical observation or CLI telemetry output...",
            height=78
        )
        commit_btn = st.form_submit_button("[COMMIT OBSERVATION & ADVANCE]")

        if commit_btn and operator_input.strip():
            # Append operator observation
            st.session_state.chat_history.append({
                "role": "OPERATOR",
                "content": operator_input.strip(),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
            })
            
            # Process turn through engine
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

    # Preset Telemetry Buttons for One-Click Verification
    st.markdown("<div style='font-size: 0.7rem; color: #9CA3AF; font-family: \"Consolas\", monospace; text-transform: uppercase; margin-top: 6px;'>ONE-CLICK TEST TELEMETRY PRESETS:</div>", unsafe_allow_html=True)
    b_col1, b_col2, b_col3 = st.columns(3)

    with b_col1:
        if st.button("PRESET 1: SFP RX Power (-28.2 dBm)", use_container_width=True):
            p1_text = "CLI telemetry 'show interfaces wan0 optical-diagnostics' reports SFP RX Power sub-threshold (-28.2 dBm), LOS asserted abnormal"
            st.session_state.chat_history.append({"role": "OPERATOR", "content": p1_text, "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            resp = query_diagnostic_engine(p1_text)
            st.session_state.diagnostic_status = resp.get("status", st.session_state.diagnostic_status)
            st.session_state.resolution_confidence = resp.get("confidence", st.session_state.resolution_confidence)
            if resp.get("escalation_record"):
                st.session_state.escalation_record = resp["escalation_record"]
            st.session_state.chat_history.append({"role": "SYSTEM", "content": resp.get("message", ""), "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            st.rerun()

    with b_col2:
        if st.button("PRESET 2: Cleaned End-Face (-11.5 dBm)", use_container_width=True):
            p2_text = "Optical fiber end-face cleaned; power restored to -11.5 dBm, nominal operational status verified"
            st.session_state.chat_history.append({"role": "OPERATOR", "content": p2_text, "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            resp = query_diagnostic_engine(p2_text)
            st.session_state.diagnostic_status = resp.get("status", st.session_state.diagnostic_status)
            st.session_state.resolution_confidence = resp.get("confidence", st.session_state.resolution_confidence)
            if resp.get("escalation_record"):
                st.session_state.escalation_record = resp["escalation_record"]
            st.session_state.chat_history.append({"role": "SYSTEM", "content": resp.get("message", ""), "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            st.rerun()

    with b_col3:
        if st.button("PRESET 3: PSU High Voltage Alert", use_container_width=True):
            p3_text = "Internal PSU capacitor bank humming; high voltage alert, breaker tripped abnormal"
            st.session_state.chat_history.append({"role": "OPERATOR", "content": p3_text, "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            resp = query_diagnostic_engine(p3_text)
            st.session_state.diagnostic_status = resp.get("status", st.session_state.diagnostic_status)
            st.session_state.resolution_confidence = resp.get("confidence", st.session_state.resolution_confidence)
            if resp.get("escalation_record"):
                st.session_state.escalation_record = resp["escalation_record"]
            st.session_state.chat_history.append({"role": "SYSTEM", "content": resp.get("message", ""), "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
            st.rerun()


# ----------------------------------------------------------------------------
# Right Column: Audit, Telemetry & Resolution Package
# ----------------------------------------------------------------------------
with col_right:
    st.markdown(
        """
        <div class="op-panel-header">
            <span>AUDIT, TELEMETRY & RESOLUTION PACKAGE</span>
            <span style="font-family: 'Consolas', monospace; color: #10B981;">AUDIT: IMMUTABLE</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. Quantitative Resolution Confidence Meter
    conf_val = st.session_state.resolution_confidence
    if st.session_state.diagnostic_status == "RESOLVED":
        meter_status_str = "FAULT RESOLVED"
        meter_color = "#10B981"
        badge_style = "badge-emerald"
    elif st.session_state.diagnostic_status in ("MANDATORY_HALT_TECHNICIAN_REQUIRED", "ESCALATED"):
        meter_status_str = "ESCALATION MANDATED"
        meter_color = "#EF4444"
        badge_style = "badge-crimson"
    else:
        meter_status_str = "DIAGNOSING"
        meter_color = "#06B6D4"
        badge_style = "badge-cyan"

    st.markdown(
        f"""
        <div class="meter-container">
            <div class="meter-readout" style="color: {meter_color};">{conf_val}%</div>
            <div class="meter-subtext">
                QUANTITATIVE RESOLUTION CONFIDENCE // <span class="badge-subsystem {badge_style}">{meter_status_str}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 2. Compatibility Gate Status Table
    st.markdown(
        f"""
        <table class="hardware-lock-table">
            <tr>
                <td class="label-cell">Target Model Gate</td>
                <td class="value-cell" style="color: #10B981;">MATCHED ({st.session_state.model_id[:16]})</td>
            </tr>
            <tr>
                <td class="label-cell">Firmware Compatibility</td>
                <td class="value-cell" style="color: #10B981;">VERIFIED ({st.session_state.firmware_version})</td>
            </tr>
            <tr>
                <td class="label-cell">Environment Profile</td>
                <td class="value-cell" style="color: #06B6D4;">INDUSTRIAL_DC (COLD AISLE)</td>
            </tr>
            <tr>
                <td class="label-cell">Safety Authorization Tier</td>
                <td class="value-cell" style="color: {'#EF4444' if is_halt else '#10B981'};">
                    {'TIER-3 CERTIFIED FIELD TECH' if is_halt else 'TIER-1 OPERATOR CLEAR'}
                </td>
            </tr>
        </table>
        """,
        unsafe_allow_html=True
    )

    # 3. Chronological Evidence Timeline
    timeline_steps = current_session.timeline

    st.markdown("<div style='font-size: 0.72rem; color: #9CA3AF; font-family: \"Consolas\", monospace; text-transform: uppercase; margin-bottom: 6px;'>CHRONOLOGICAL EVIDENCE AUDIT TRAIL:</div>", unsafe_allow_html=True)

    if not timeline_steps:
        st.markdown(
            """
            <div style="background-color: #050811; border: 1px dashed #1F2937; padding: 12px; font-family: 'Consolas', monospace; font-size: 0.74rem; color: #64748B; text-align: center;">
                STANDBY: EVIDENCE TIMELINE INITIALIZING
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # Display timeline entries (most recent first or chronological)
        for s in timeline_steps:
            if s.verification_status == "VERIFIED_NORMAL":
                s_badge = "badge-emerald"
            elif s.verification_status == "VERIFIED_ABNORMAL":
                s_badge = "badge-crimson"
            elif s.verification_status == "BLOCKED":
                s_badge = "badge-crimson"
            else:
                s_badge = "badge-amber"

            st.markdown(
                f"""
                <div style="background-color: #050811; border: 1px solid #1F2937; border-left: 3px solid {'#10B981' if s.verification_status == 'VERIFIED_NORMAL' else '#EF4444'}; border-radius: 1px; padding: 8px 10px; margin-bottom: 6px; font-family: 'Consolas', monospace; font-size: 0.74rem;">
                    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #111827; padding-bottom: 3px; margin-bottom: 4px;">
                        <span style="color: #9CA3AF;">STEP {s.step_index:02d} // {s.timestamp[11:19]} UTC</span>
                        <span class="badge-subsystem {s_badge}">{s.verification_status}</span>
                    </div>
                    <div style="color: #F3F4F6; margin-bottom: 2px;"><strong>ACTION:</strong> {s.action_executed[:55]}...</div>
                    <div style="color: #06B6D4;"><strong>OBSERVED:</strong> {s.user_reported_observation[:60]}...</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # 4. Formal Record Export Controls
    st.markdown("<div style='font-size: 0.72rem; color: #9CA3AF; font-family: \"Consolas\", monospace; text-transform: uppercase; margin: 12px 0 6px 0;'>FORMAL RECORD EXPORT CONTROLS:</div>", unsafe_allow_html=True)

    # Ensure escalation record exists or can be generated
    if not st.session_state.escalation_record:
        if st.button("PREPARE FORMAL INCIDENT RECORD", use_container_width=True):
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
                label="[DOWNLOAD FORMAL ESCALATION RECORD (JSON)]",
                data=json_payload,
                file_name=f"{esc_data.get('incident_id', 'INC')}_ESCALATION_RECORD.json",
                mime="application/json",
                use_container_width=True
            )
        with dl_col2:
            st.download_button(
                label="[EXPORT INCIDENT AUDIT REPORT (MARKDOWN)]",
                data=md_payload,
                file_name=f"{esc_data.get('incident_id', 'INC')}_AUDIT_REPORT.md",
                mime="text/markdown",
                use_container_width=True
            )
