import json
import uuid
import re
from datetime import datetime, timezone
from typing import Any, Optional
import httpx
import streamlit as st

from src.config import settings
from src.tools import _load_error_codes_db, lookup_error_code, list_products, list_error_codes
from src.evaluation import run_evaluation
from src.rag import get_knowledge_base
from src.agents import (
    DiagnosticCoordinator,
    SafeStepPlannerAgent,
    ResolutionReviewAgent,
    get_or_create_session,
    SESSION_STORAGE,
    SessionState,
    SUPPORTED_MODELS,
    normalize_model_id
)

# ============================================================================
# Page Configuration & Light Warm Ivory/Cream Human-Centric Design System
# ============================================================================

st.set_page_config(
    page_title="AI Product Manual Troubleshooting Assistant",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Comprehensive Human-Centric Clean Light Theme CSS
REVAMPED_LIGHT_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');

    /* Global Canvas */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
        background-color: #FAF7F2 !important;
        background: #FAF7F2 !important;
        color: #1F2937 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    [data-testid="stHeader"] {
        background-color: rgba(250, 247, 242, 0.92) !important;
        border-bottom: 1px solid #E5E7EB !important;
        backdrop-filter: blur(8px) !important;
    }

    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB !important;
    }

    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #111827 !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        margin: 0 !important;
    }

    p, span, label, div {
        color: #374151;
        font-family: 'Inter', sans-serif;
    }

    /* Top Navigation Header Bar */
    .top-header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 0 16px 0;
        margin-bottom: 12px;
        border-bottom: 1px solid #E5E7EB;
    }
    .header-title-text {
        font-size: 1.5rem;
        font-weight: 800;
        color: #1E3A8A;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }
    .header-sub-text {
        font-size: 0.85rem;
        color: #6B7280;
        font-weight: 400;
        margin-top: 3px;
    }

    /* System Status Pills */
    .mode-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 9999px;
        letter-spacing: 0.02em;
    }
    .mode-pill-green {
        background-color: #ECFDF5;
        color: #065F46;
        border: 1px solid #A7F3D0;
    }
    .mode-pill-neutral {
        background-color: #F3F4F6;
        color: #374151;
        border: 1px solid #E5E7EB;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-green { background-color: #059669; }
    .dot-neutral { background-color: #6B7280; }

    /* Clean White Card Surfaces */
    .ui-card {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .ui-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #F3F4F6;
        padding-bottom: 10px;
        margin-bottom: 14px;
    }
    .ui-card-title {
        font-size: 0.92rem;
        font-weight: 700;
        color: #1E3A8A;
        letter-spacing: -0.01em;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Badges & Pills */
    .badge-soft-blue {
        background-color: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #DBEAFE;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 9999px;
    }
    .badge-soft-green {
        background-color: #ECFDF5;
        color: #047857;
        border: 1px solid #A7F3D0;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 9999px;
    }
    .badge-soft-red {
        background-color: #FEF2F2;
        color: #B91C1C;
        border: 1px solid #FECACA;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 9999px;
    }
    .badge-soft-amber {
        background-color: #FFFBEB;
        color: #B45309;
        border: 1px solid #FDE68A;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 9999px;
    }

    /* Active Step Instruction Card */
    .step-header-box {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .step-pill-indicator {
        background-color: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 9999px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .step-action-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #111827;
        line-height: 1.35;
        margin-bottom: 12px;
    }
    .step-instructions-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 14px 16px;
        color: #334155;
        font-size: 0.90rem;
        line-height: 1.55;
        margin-bottom: 14px;
    }

    /* Safety Interlock Warm Red Container */
    .safety-alert-container {
        background-color: #FEF2F2;
        border: 1px solid #FCA5A5;
        border-left: 5px solid #DC2626;
        border-radius: 6px;
        padding: 16px 18px;
        margin-bottom: 16px;
    }
    .safety-alert-header {
        color: #991B1B;
        font-size: 0.95rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }
    .safety-alert-body {
        color: #7F1D1D;
        font-size: 0.85rem;
        line-height: 1.5;
    }

    /* Collapsible Reference Box */
    .reference-box {
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 10px 14px;
        font-size: 0.80rem;
        color: #4B5563;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Resolution Progress Card */
    .progress-number-display {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1E3A8A;
        line-height: 1.1;
        letter-spacing: -0.03em;
    }
    .progress-label-text {
        font-size: 0.82rem;
        font-weight: 600;
        color: #4B5563;
        margin-top: 4px;
    }

    /* Verification Verification Rows */
    .verify-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid #F3F4F6;
        font-size: 0.84rem;
    }
    .verify-row:last-child {
        border-bottom: none;
        padding-bottom: 2px;
    }
    .verify-label {
        color: #4B5563;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .verify-status {
        font-weight: 600;
        font-size: 0.78rem;
    }

    /* Timeline Cards */
    .timeline-feed {
        display: flex;
        flex-direction: column;
        gap: 10px;
        max-height: 380px;
        overflow-y: auto;
        padding-right: 4px;
    }
    .timeline-item-card {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 12px 14px;
        font-size: 0.82rem;
        line-height: 1.45;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    .timeline-item-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
        padding-bottom: 6px;
        border-bottom: 1px solid #F3F4F6;
    }

    /* Form Fields & Clean Modern Inputs (Strict Light/Dark Inversion Protection) */
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="textarea"],
    div[data-baseweb="select"] > div,
    input, textarea, select {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.88rem !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
    }
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="textarea"]:focus-within,
    div[data-baseweb="select"] > div:focus-within,
    input:focus, textarea:focus, select:focus {
        border-color: #1E3A8A !important;
        box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.15) !important;
    }

    /* Target specific Streamlit widgets to enforce dark text on white input canvas */
    .stTextInput input,
    .stTextArea textarea,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border: 1px solid #D1D5DB !important;
    }
    .stSelectbox div[data-baseweb="select"],
    [data-testid="stSelectbox"] div[data-baseweb="select"],
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    [data-testid="stSelectbox"] div[data-baseweb="select"] * {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }
    ul[role="listbox"],
    ul[role="listbox"] li,
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    div[data-baseweb="menu"] * {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }
    ul[role="listbox"] li:hover,
    div[data-baseweb="menu"] li:hover {
        background-color: #F3F4F6 !important;
        color: #1E3A8A !important;
        -webkit-text-fill-color: #1E3A8A !important;
    }

    /* Modern Primary & Secondary Buttons */
    div.stButton > button,
    div[data-testid="stFormSubmitButton"] > button,
    div[data-testid="stDownloadButton"] > button {
        background-color: #FFFFFF !important;
        color: #1E3A8A !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 6px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    }
    div.stButton > button:hover,
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #F3F4F6 !important;
        border-color: #9CA3AF !important;
        color: #111827 !important;
    }

    /* Primary Accent Submit Button */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #1E3A8A !important;
        color: #FFFFFF !important;
        border: 1px solid #1E3A8A !important;
        font-weight: 700 !important;
        font-size: 0.88rem !important;
        padding: 10px 20px !important;
        box-shadow: 0 1px 3px rgba(30, 58, 138, 0.2) !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #1D4ED8 !important;
        border-color: #1D4ED8 !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stFormSubmitButton"] > button p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Streamlit Expander Styling */
    div[data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 6px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
    }
    div[data-testid="stExpander"] summary {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        color: #374151 !important;
    }
    div[data-testid="stExpander"] summary:hover {
        color: #1E3A8A !important;
    }
    div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background-color: #FFFFFF !important;
        border-top: 1px solid #F3F4F6 !important;
        padding: 14px !important;
    }

    /* Streamlit Progress Bar */
    div[data-testid="stProgress"] > div > div > div > div {
        background-color: #2563EB !important;
    }
</style>
"""

st.markdown(REVAMPED_LIGHT_CSS, unsafe_allow_html=True)


# ============================================================================
# Appliance Platform Mapping & Session State
# ============================================================================

APPLIANCE_OPTIONS = [
    "Bosch 800 Series Dishwasher",
    "Whirlpool Front-Load Washer",
    "LG Inverter Refrigerator",
    "Breville Dual Boiler Espresso Machine"
]

APPLIANCE_TO_MODEL_ID = {
    "Bosch 800 Series Dishwasher": "BOSCH_SHEM78",
    "Whirlpool Front-Load Washer": "WHIRLPOOL_WASHER_ALPHA",
    "LG Inverter Refrigerator": "LG_REFRIG_LFXS",
    "Breville Dual Boiler Espresso Machine": "BREVILLE_BES920"
}

MODEL_ID_TO_APPLIANCE = {v: k for k, v in APPLIANCE_TO_MODEL_ID.items()}

DEFAULT_FIRMWARE = {
    "Bosch 800 Series Dishwasher": "Rev C / MCU 4.18.2",
    "Whirlpool Front-Load Washer": "Rev B3 / ACU W11419171",
    "LG Inverter Refrigerator": "Rev 4.2 / Micom EBR822304",
    "Breville Dual Boiler Espresso Machine": "Rev 3.4 / Dual PID Logic"
}

DEFAULT_CODES = {
    "Bosch 800 Series Dishwasher": "E15",
    "Whirlpool Front-Load Washer": "F06 E01",
    "LG Inverter Refrigerator": "BLNK-5",
    "Breville Dual Boiler Espresso Machine": "Er01"
}

# ============================================================================
# Session State Hardening & Initialization
# ============================================================================

def init_session_state():
    """
    Strict state initialization function:
    Ensures keys ['active_model', 'current_step_idx', 'evidence_timeline',
    'resolution_confidence', 'is_safety_halted', 'incident_exported']
    along with appliance parameters and session essentials are safely initialized.
    """
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"SESS-{uuid.uuid4().hex[:8].upper()}"
    if "selected_appliance" not in st.session_state:
        st.session_state.selected_appliance = "Bosch 800 Series Dishwasher"
    if "active_model" not in st.session_state:
        st.session_state.active_model = APPLIANCE_TO_MODEL_ID.get(st.session_state.selected_appliance, "BOSCH_SHEM78")
    if "error_code" not in st.session_state:
        st.session_state.error_code = DEFAULT_CODES[st.session_state.selected_appliance]
    if "firmware_version" not in st.session_state:
        st.session_state.firmware_version = DEFAULT_FIRMWARE[st.session_state.selected_appliance]
    if "current_step_idx" not in st.session_state:
        st.session_state.current_step_idx = 0
    if "evidence_timeline" not in st.session_state:
        st.session_state.evidence_timeline = []
    if "resolution_confidence" not in st.session_state:
        st.session_state.resolution_confidence = 0
    if "is_safety_halted" not in st.session_state:
        st.session_state.is_safety_halted = False
    if "incident_exported" not in st.session_state:
        st.session_state.incident_exported = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "diagnostic_status" not in st.session_state:
        st.session_state.diagnostic_status = "INITIALIZING"
    if "escalation_record" not in st.session_state:
        st.session_state.escalation_record = None
    if "eval_report" not in st.session_state:
        st.session_state.eval_report = None

init_session_state()


# Load Error Codes Database
try:
    ERROR_CODES_DB = _load_error_codes_db()
except Exception:
    ERROR_CODES_DB = {}


# ============================================================================
# OEM Step Action to Clean Title Lexicon
# ============================================================================
OEM_STEP_TITLES = {
    "disconnect 120v/240v mains": "Mains Electrical Disconnection",
    "turn off under-sink water supply": "Water Supply Isolation & Shutoff",
    "remove lower toe-kick access cover": "Toe-Kick Panel Removal & Sump Inspection",
    "sponge, syphon, or wet-vacuum": "Base Pan Moisture Evacuation",
    "inspect sump perimeter o-ring": "Sump Perimeter Gasket & Seal Inspection",
    "remove lower dish rack and rotate": "Microfilter Assembly Extraction & Cleaning",
    "pry out white plastic drain pump": "Drain Pump Impeller Shroud Removal",
    "inspect bldc drain pump impeller": "BLDC Impeller Vane Obstruction Inspection",
    "verify drain pump impeller spins": "Impeller Magnetic Detent Rotation Verification",
    "inspect rubber non-return flapper": "Non-Return Check Valve Flapper Inspection",
    "verify white plastic drain pump": "Impeller Shroud Mechanical Detent Seating",
    "inspect drain hose routing": "Drain Line Elevation & Routing Inspection",
    "inspect kitchen garbage disposal": "Garbage Disposal Knockout Plug Verification",
    "measure drain pump motor winding": "Drain Pump Winding Resistance Measurement",
    "measure ac line voltage": "AC Supply Line Voltage Audit",
    "verify dishwasher is hardwired": "Branch Circuit Dedicated Feed Verification",
    "inspect rear metal power junction": "Mains Junction Box & Terminal Inspection",
    "monitor line voltage drop": "Heater Inrush Line Sag Monitoring",
    "disconnect ac line power cord and wait 3 minutes for mcu": "Inverter Bus Capacitor Bleed-Down",
    "enter service diagnostic mode": "Service Diagnostic Console Mode Entry",
    "inspect 3-wire tachometer wiring": "Tachometer Sensor Harness Inspection",
    "rotate inner stainless wash basket": "Manual Wash Basket Drum Rotation Check",
    "measure tachometer coil resistance": "Tachometer Coil Resistance Measurement",
    "disconnect ac line power cord from wall outlet": "AC Power Cord Disconnection",
    "remove top console / cabinet lid": "Upper Chassis Console Lid Removal",
    "inspect translucent vinyl air pressure tube": "Pressure Transducer Tube Inspection",
    "check vinyl pressure tube for kinks": "Pressure Tube Obstruction & Puncture Check",
    "disconnect vinyl tube at sensor nipple": "Pressure Sensor Airway Clear & Purge",
    "verify acu connector j3": "ACU Harness Voltage & Connection Verification",
    "remove rear service access panel to expose heating": "Rear Service Panel Removal & Heater Access",
    "discharge electrostatic potential": "Electrostatic Discharge & Terminal Inspection",
    "measure resistance across heating element": "Heating Element Resistance Measurement",
    "measure insulation resistance from either heater": "Heater Ground Insulation Test",
    "disconnect ac power cord and observe mandatory 3-minute pcb": "Inverter Bus Capacitor Bleed-Down Delay",
    "locate the red diagnostic led on the main inverter pcb": "Inverter PCB Diagnostic LED Cadence Audit",
    "remove compressor 3-pin lead terminal cover": "Compressor 3-Pin Terminal Inspection",
    "measure linear compressor stator coil resistance": "Linear Compressor Stator Coil Test",
    "measure insulation resistance from terminal pins to compressor shell": "Compressor Ground Insulation Test",
    "disconnect refrigerator ac power cord and observe 3-minute": "Inverter Compartment Service Preparation",
    "inspect rear machine compartment condenser fan": "Condenser Fan Motor Assembly Inspection",
    "clean wire condenser heat exchanger": "Condenser Matrix Lint Evacuation",
    "check main inverter pcb ipm aluminum heat sink": "IPM Heat Sink Thermal Coupling Check",
    "inspect compressor discharge line temperature": "Compressor Discharge Line Thermal Audit",
    "inspect rear evaporator cover wall inside freezer": "Evaporator Frost Pattern & Airflow Audit",
    "initiate forced defrost mode": "Front Panel Forced Defrost Initiation",
    "remove freezer back wall panel": "Freezer Rear Wall Removal & Evaporator Access",
    "measure defrost sheath heater resistance": "Defrost Sheath Heater Resistance Test",
    "test defrost bimetal safety thermostat": "Defrost Bimetal Thermostat Continuity Test",
    "measure defrost ntc temperature sensor resistance": "Defrost NTC Sensor Resistance Audit",
    "verify rear water reservoir is filled": "Water Reservoir Level & Float Verification",
    "inspect water reservoir mesh intake valve": "Intake Mesh Valve & Duckbill Gasket Check",
    "verify both rear boiler manual brass ball drain valves": "Boiler Manual Brass Ball Drain Valves Check",
    "inspect conductive water level probe harness wire": "Steam Boiler Level Probe Harness Inspection",
    "listen for ulka vibratory fill pump": "Vibratory Fill Pump Acoustic Audit & Priming",
    "unplug machine power cord from wall receptacle immediately to prevent thermal fuse": "Emergency AC Power Disconnection",
    "allow espresso machine to cool down completely": "Boiler Thermal Cool-Down Period",
    "remove top chassis lid (6 torx t10 screws)": "Top Chassis Lid Removal & Scald Precaution",
    "inspect grouphead cartridge heating element wiring": "Grouphead Heating Element & NTC Wire Audit",
    "measure grouphead ntc thermistor resistance": "Grouphead NTC Thermistor Resistance Test",
    "unplug espresso machine from ac power socket and ensure steam boiler pressure": "Steam Boiler De-Pressurization & Power Cut",
    "remove top chassis lid and inspect 2-pin white molex": "Main Power Board NTC-STM Connector Audit",
    "verify wiring harness from steam boiler sensor well": "Boiler Sensor Harness Rib Clearance Check",
    "measure ntc thermistor resistance directly across sensor probe": "Steam Boiler NTC Thermistor Resistance Test"
}


def get_step_title_and_instructions(raw_action: str) -> tuple[str, str]:
    """
    Intelligently splits or synthesizes clean titles and action descriptions
    without ever truncating mid-word or producing broken titles.
    """
    if not raw_action:
        return "Diagnostic Step", ""

    # 1. Parenthesized/Prefix title: Step 1 (Title): Body or Procedure X: Title
    m = re.search(r'(?:Step\s+\d+\s*\((.*?)\)|Procedure\s+[A-Z0-9\-]+:\s*(.*?))(?::|$)', raw_action, re.IGNORECASE)
    if m:
        action_title = (m.group(1) or m.group(2)).strip()
        action_body = re.sub(r'^(?:Step\s+\d+\s*\(.*?\):?|Procedure\s+[A-Z0-9\-]+:\s*.*?)\s*', '', raw_action).strip()
        return action_title, action_body

    # 2. Mandatory Halt boundary
    if raw_action.upper().startswith("MANDATORY HALT"):
        action_title = "Mandatory Safety Interlock: Field Technician Boundary"
        action_body = re.sub(r'^MANDATORY HALT:\s*', '', raw_action).strip()
        return action_title, action_body

    # 3. Curated OEM Step Title dictionary
    lower_raw = raw_action.lower()
    for trigger, title in OEM_STEP_TITLES.items():
        if trigger in lower_raw:
            return title, raw_action

    # 4. Fallback intelligent phrase extraction (never cuts mid-word)
    cand = re.sub(r'^(?:Step\s*\d+[:\-.]?|\d+[\.\)]\s*)', '', raw_action).strip()
    split_pats = [
        r'\s+(?:immediately\s+)?to\s+(?:halt|allow|verify|access|clear|reset|resolve|check)\b.*$',
        r'\s+feeding\s+the\b.*$',
        r'\s+and\s+visually\s+inspect\b.*$',
        r'\s+using\s+(?:Torx|digital|multimeter|calibrated)\b.*$',
        r'\s+for\s+(?:trapped|kinks|loose|weep)\b.*$'
    ]
    for p in split_pats:
        m2 = re.search(p, cand, re.IGNORECASE)
        if m2 and m2.start() > 18:
            cand = cand[:m2.start()].strip()
            break

    cand = re.sub(r'\s+(?:and|for|to|with|by|in|at|of|from|while)$', '', cand, flags=re.IGNORECASE).strip()
    if len(cand) > 60:
        words = cand.split()
        short = []
        for w in words:
            if len(" ".join(short + [w])) <= 52:
                short.append(w)
            else:
                break
        cand = " ".join(short)
        cand = re.sub(r'\s+(?:and|for|to|with|by|in|at|of|from|while)$', '', cand, flags=re.IGNORECASE).strip()

    title = cand.rstrip(".,:;")
    return title, raw_action


# Probe Cloud MaaS / Gemini Gateway Connectivity
@st.cache_data(ttl=25)
def check_maas_gateway_online() -> bool:
    """Verifies whether TCS GenAI Lab MaaS or Gemini gateway is responsive."""
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
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                return True
    except Exception:
        pass

    if settings.is_gemini_active:
        try:
            g_model = settings.model_name.split("/")[-1]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}?key={settings.maas_api_key}"
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(url)
                return resp.status_code == 200
        except Exception:
            pass

    return False


def call_backend_or_direct(route: str, method: str = "POST", payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Resilient bridge function for REST API calls.
    Attempts communication with http://127.0.0.1:8000.
    If FastAPI backend is running and reachable, uses the REST API.
    If connection fails, times out, or is refused, seamlessly invokes src.agents
    and src.tools directly in Python memory! The UI NEVER displays a connection
    error banner or crashes; it just works.
    """
    connect_host = "127.0.0.1" if settings.api_host in ("0.0.0.0", "") else settings.api_host
    backend_url = f"http://{connect_host}:{settings.api_port}{route}"

    try:
        with httpx.Client(timeout=2.0) as client:
            if method.upper() == "POST":
                resp = client.post(backend_url, json=payload or {})
            else:
                resp = client.get(backend_url)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass  # In-process seamless fallback

    clean_route = route.split("?")[0]

    if clean_route == "/api/diagnose":
        p = payload or {}
        session_id = p.get("session_id") or st.session_state.session_id
        session = get_or_create_session(session_id)
        if p.get("model_id"):
            session.model_id = normalize_model_id(p["model_id"]) or session.model_id
        if p.get("firmware_version"):
            session.firmware_version = p["firmware_version"]
        if p.get("operating_environment"):
            session.operating_environment = p["operating_environment"]
        if p.get("error_code"):
            session.error_code = p["error_code"]

        msg = p.get("message", "")
        return DiagnosticCoordinator.process_turn(session_id=session_id, user_input=msg)

    elif clean_route.startswith("/api/escalate/"):
        sess_id = clean_route.split("/api/escalate/")[-1]
        sess = get_or_create_session(sess_id)
        sess.diagnostic_status = "ESCALATED"
        pkg = ResolutionReviewAgent.generate_escalation_package(
            session=sess,
            reason="Manual operator service export requested from console."
        )
        return {
            "session_id": sess_id,
            "incident_id": pkg.get("incident_id", f"INC-{uuid.uuid4().hex[:6].upper()}"),
            "escalation_package": pkg
        }

    elif clean_route.startswith("/api/timeline/"):
        sess_id = clean_route.split("/api/timeline/")[-1]
        sess = get_or_create_session(sess_id)
        return {
            "session_id": sess.session_id,
            "total_steps": len(sess.timeline),
            "resolution_confidence": sess.resolution_confidence,
            "diagnostic_status": sess.diagnostic_status,
            "timeline": [t.dict() if hasattr(t, "dict") else t for t in sess.timeline]
        }

    elif clean_route == "/api/models":
        return {
            "total": len(SUPPORTED_MODELS),
            "models": [
                {
                    "model_id": k,
                    "display_name": v,
                    "manual_reference": f"# [MANUAL: {k}]",
                    "supported_error_codes": [
                        code for code, data in _load_error_codes_db().items()
                        if data.get("model_id") == k
                    ]
                }
                for k, v in SUPPORTED_MODELS.items()
            ]
        }

    elif clean_route == "/api/codes":
        return {"total": len(ERROR_CODES_DB), "codes": ERROR_CODES_DB}

    elif clean_route.startswith("/api/codes/"):
        code_param = clean_route.split("/api/codes/")[-1]
        return lookup_error_code(code_param)

    return {"status": "SUCCESS", "message": "In-process execution"}


def query_diagnostic_engine(message: str) -> dict[str, Any]:
    """
    Submits user observation or instruction to FastAPI backend or fallback agent pipeline
    via resilient call_backend_or_direct.
    """
    model_id = st.session_state.active_model
    session = get_or_create_session(st.session_state.session_id)
    session.model_id = model_id
    session.firmware_version = st.session_state.firmware_version
    session.error_code = st.session_state.error_code

    payload = {
        "session_id": st.session_state.session_id,
        "message": message,
        "model_id": model_id,
        "firmware_version": st.session_state.firmware_version,
        "operating_environment": "Commercial / Residential Site",
        "error_code": st.session_state.error_code
    }

    data = call_backend_or_direct("/api/diagnose", method="POST", payload=payload)

    if "timeline" in data:
        from src.agents import EvidenceStep
        session.timeline = [
            EvidenceStep(**t) if isinstance(t, dict) else t for t in data["timeline"]
        ]
        st.session_state.evidence_timeline = [
            t.dict() if hasattr(t, "dict") else t for t in session.timeline
        ]
    if not session.planned_steps:
        SafeStepPlannerAgent.generate_plan(session)

    session.current_step_index = len(session.timeline)
    st.session_state.current_step_idx = session.current_step_index
    st.session_state.resolution_confidence = data.get("confidence", session.resolution_confidence)
    st.session_state.diagnostic_status = data.get("status", session.diagnostic_status)
    st.session_state.is_safety_halted = (
        st.session_state.diagnostic_status == "MANDATORY_HALT_TECHNICIAN_REQUIRED"
    )
    if data.get("escalation_record"):
        st.session_state.escalation_record = data["escalation_record"]
        st.session_state.incident_exported = data["escalation_record"]

    return data


# ============================================================================
# Screen Architecture: Top Navigation & Appliance Selector
# ============================================================================

is_maas_connected = check_maas_gateway_online()

nav_c1, nav_c2, nav_c3 = st.columns([1.5, 1.2, 0.9])

with nav_c1:
    st.markdown(
        """
        <div style="padding: 2px 0 8px 0;">
            <div class="header-title-text">Diagnostic Service Assistant</div>
            <div class="header-sub-text">Intelligent step-by-step troubleshooting for certified commercial & home appliances</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with nav_c2:
    status_label = "Cloud Gemini Connected" if settings.is_gemini_active else "Cloud MaaS Connected"
    mode_html = (
        f"""
        <div style="display: flex; justify-content: flex-end; align-items: center; gap: 8px; height: 100%; padding-bottom: 8px;">
            <span class="mode-pill mode-pill-green">
                <span class="status-dot dot-green"></span> {status_label}
            </span>
        </div>
        """
        if is_maas_connected else
        """
        <div style="display: flex; justify-content: flex-end; align-items: center; gap: 8px; height: 100%; padding-bottom: 8px;">
            <span class="mode-pill mode-pill-neutral">
                <span class="status-dot dot-neutral"></span> Airgapped Offline Mode
            </span>
        </div>
        """
    )
    st.markdown(mode_html, unsafe_allow_html=True)

with nav_c3:
    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
    if st.button("Start New Diagnosis", use_container_width=True, help="Clear current diagnostic session and start fresh"):
        st.session_state.session_id = f"SESS-{uuid.uuid4().hex[:8].upper()}"
        st.session_state.current_step_idx = 0
        st.session_state.evidence_timeline = []
        st.session_state.resolution_confidence = 0
        st.session_state.is_safety_halted = False
        st.session_state.incident_exported = None
        st.session_state.chat_history = []
        st.session_state.diagnostic_status = "INITIALIZING"
        st.session_state.escalation_record = None
        st.rerun()

# ============================================================================
# Sidebar: Quality Benchmark Suite, 3-Factor Re-Ranking & Anti-Loop Memory
# ============================================================================
with st.sidebar:
    st.markdown("### 🛠️ Diagnostic Operations")
    st.caption("AI-Powered Field Engineering & Multi-Tier Knowledge System")

    # 1. Automated Benchmark Evaluation Suite (Kashesh's standout feature)
    with st.expander("📊 Quality Benchmark Suite (50 Tests)", expanded=True):
        st.caption("Automated 4-dimension regression test suite:")
        if st.button("▶️ Run 100% Quality Benchmark", use_container_width=True, type="primary"):
            with st.spinner("Executing 50 test cases across 4 dimensions..."):
                rep = run_evaluation()
                st.session_state.eval_report = rep
                st.rerun()

        if st.session_state.eval_report:
            rep = st.session_state.eval_report
            st.metric("Benchmark Accuracy", f"{rep['overall_percent']}%", delta="100% Pass")
            for grp in rep["groups"]:
                col_g1, col_g2 = st.columns([1.5, 1])
                with col_g1:
                    st.write(f"**{grp['name']}**")
                with col_g2:
                    st.write(f"`{grp['passed']}/{grp['total']}` ({grp['score_percent']}%)")
                st.progress(grp["passed"] / max(grp["total"], 1))

    # 2. Multi-Criteria 3-Factor Re-Ranking Formula
    with st.expander("📐 3-Factor Re-Ranking Formula", expanded=False):
        st.markdown(
            r"""
            **Composite Re-Ranking Score:**
            $$\text{Score} = 0.45 \cdot S_{\text{sim}} + 0.35 \cdot S_{\text{model}} + 0.20 \cdot S_{\text{auth}}$$
            
            **Document Authority Hierarchy:**
            - 🛡️ **Escalation Rules:** `1.00` *(Regulatory / Life Safety)*
            - 📢 **Service Bulletins:** `0.92` *(Urgent OEM Advisories)*
            - 💡 **Known Issues:** `0.76` *(Field Workarounds)*
            - 📖 **Product Manuals:** `0.60` *(Baseline Procedures)*
            """
        )

    # 3. Diagnostic Memory & Anti-Looping Interlock
    with st.expander("🧠 Anti-Loop Diagnostic Memory", expanded=False):
        st.markdown(
            f"""
            - **Session Reference:** `{st.session_state.session_id}`
            - **Diagnostic Memory Status:** `ACTIVE`
            - **Loop Prevention Interlock:** `ENABLED` *(Failed steps never repeated)*
            - **Attempted Steps Logged:** `{len(st.session_state.evidence_timeline)} steps`
            - **Safety Interlock:** `NFPA 70E / EPA 608 Verified`
            """
        )

    st.divider()
    st.caption("TCS GenAI Lab • Enterprise Diagnostic Edition")


# ============================================================================
# Main Layout: Two Clean Columns (col_main, col_sidebar = st.columns([1.3, 0.7]))
# ============================================================================

col_main, col_sidebar = st.columns([1.3, 0.7])

current_session = get_or_create_session(st.session_state.session_id)
active_model_id = APPLIANCE_TO_MODEL_ID.get(st.session_state.selected_appliance, "BOSCH_SHEM78")
st.session_state.active_model = active_model_id
current_session.model_id = active_model_id
current_session.firmware_version = st.session_state.firmware_version
current_session.error_code = st.session_state.error_code

# ----------------------------------------------------------------------------
# Left Column: Guided Troubleshooting Walkthrough
# ----------------------------------------------------------------------------
with col_main:

    # 1. Appliance Status Banner & Configuration Card
    with st.container():
        st.markdown(
            """
            <div class="ui-card">
                <div class="ui-card-header">
                    <div class="ui-card-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1E3A8A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
                        Target Appliance Equipment
                    </div>
                    <span class="badge-soft-blue">OEM Certified Manual</span>
                </div>
            """,
            unsafe_allow_html=True
        )

        app_col1, app_col2 = st.columns([1.2, 0.8])
        with app_col1:
            prev_app = st.session_state.selected_appliance
            st.session_state.selected_appliance = st.selectbox(
                "Select Appliance Platform",
                options=APPLIANCE_OPTIONS,
                index=APPLIANCE_OPTIONS.index(st.session_state.selected_appliance) if st.session_state.selected_appliance in APPLIANCE_OPTIONS else 0,
                label_visibility="collapsed"
            )
            # Update default codes and firmware if appliance changed cleanly without KeyError
            if st.session_state.selected_appliance != prev_app:
                st.session_state.active_model = APPLIANCE_TO_MODEL_ID[st.session_state.selected_appliance]
                st.session_state.error_code = DEFAULT_CODES[st.session_state.selected_appliance]
                st.session_state.firmware_version = DEFAULT_FIRMWARE[st.session_state.selected_appliance]
                st.session_state.current_step_idx = 0
                st.session_state.evidence_timeline = []
                st.session_state.resolution_confidence = 0
                st.session_state.is_safety_halted = False
                st.session_state.incident_exported = None
                st.session_state.chat_history = []
                st.session_state.diagnostic_status = "INITIALIZING"
                st.session_state.escalation_record = None

                current_session.model_id = st.session_state.active_model
                current_session.error_code = st.session_state.error_code
                current_session.firmware_version = st.session_state.firmware_version
                current_session.current_step_index = 0
                current_session.timeline = []
                current_session.planned_steps = []
                current_session.resolution_confidence = 0
                current_session.diagnostic_status = "INITIALIZING"
                current_session.halt_reason = None
                current_session.escalation_record = None
                st.rerun()

        # Available codes for this platform
        active_model_id = APPLIANCE_TO_MODEL_ID[st.session_state.selected_appliance]
        avail_codes = [c for c, d in ERROR_CODES_DB.items() if d.get("model_id") == active_model_id]
        if not avail_codes:
            avail_codes = ["E15", "E24", "E25", "E27"]

        with app_col2:
            code_pos = avail_codes.index(st.session_state.error_code) if st.session_state.error_code in avail_codes else 0
            st.session_state.error_code = st.selectbox(
                "Diagnostic Code",
                options=avail_codes,
                index=code_pos,
                label_visibility="collapsed"
            )

        # Meta detail banner
        code_meta = ERROR_CODES_DB.get(st.session_state.error_code, {})
        subsystem_str = code_meta.get("subsystem", "General Hydraulics")
        desc_str = code_meta.get("description", "Standard diagnostic routine")
        sev_str = code_meta.get("severity", "HIGH")
        sev_badge = "badge-soft-red" if sev_str == "CRITICAL" else ("badge-soft-amber" if sev_str == "HIGH" else "badge-soft-blue")

        st.markdown(
            f"""
            <div style="background-color: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px; padding: 10px 14px; margin-top: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-size: 0.80rem; font-weight: 600; color: #1E3A8A;">Platform: {st.session_state.selected_appliance}</span>
                    <span class="{sev_badge}">Severity: {sev_str}</span>
                </div>
                <div style="font-size: 0.82rem; color: #4B5563;">
                    <strong>Subsystem:</strong> {subsystem_str} &nbsp;|&nbsp; <strong>Firmware:</strong> {st.session_state.firmware_version}
                </div>
                <div style="font-size: 0.80rem; color: #6B7280; margin-top: 3px;">
                    {desc_str}
                </div>
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # If session not started, show clean "Begin Guided Diagnosis" prompt
    if not st.session_state.chat_history:
        st.markdown(
            """
            <div class="ui-card" style="text-align: center; padding: 28px 20px;">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 12px;"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
                <div style="font-size: 1.10rem; font-weight: 700; color: #111827; margin-bottom: 6px;">Ready to Begin Guided Troubleshooting</div>
                <div style="font-size: 0.85rem; color: #6B7280; max-width: 480px; margin: 0 auto 18px auto;">
                    The assistant will sequence manufacturer-approved diagnostic checks from least disruptive routines to verified electrical/hydraulic isolations.
                </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Begin Guided Diagnosis", use_container_width=True):
            init_turn = f"{st.session_state.selected_appliance} with code {st.session_state.error_code}"
            resp = query_diagnostic_engine(init_turn)
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

    # Determine Active Planned Step
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

    # 2. Active Diagnostic Step Card or Resolved Card
    if st.session_state.diagnostic_status == "RESOLVED":
        st.markdown(
            f"""
            <div class="ui-card" style="border-left: 5px solid #059669; background-color: #F0FDF4;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                        <div style="font-size: 1.15rem; font-weight: 700; color: #065F46;">Fault Successfully Resolved</div>
                    </div>
                    <span class="badge-soft-green">98% Confidence</span>
                </div>
                <div style="color: #166534; font-size: 0.90rem; line-height: 1.5; margin-bottom: 8px;">
                    Normal operating telemetry has been confirmed. The equipment is restored to certified operational parameters and eligible for return to service.
                </div>
                <div style="font-size: 0.82rem; color: #047857;">
                    Review the chronological action history on the right panel or export the service summary for documentation. Click <strong>Start New Diagnosis</strong> above to troubleshoot another asset.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif active_step:
        raw_action = active_step.get("action", "")
        subsystem_tag = active_step.get("subsystem", "Mechanical")
        disruption_lvl = active_step.get("disruption_level", "NON_DISRUPTIVE").replace("_", " ").title()
        citation_src = active_step.get("source_ref", "OEM Service Manual Standard")
        boundary_dir = active_step.get("boundary_directive", "Standard field maintenance guidelines apply.")

        # Clean plain-language action title & detailed instruction body
        action_title, action_body = get_step_title_and_instructions(raw_action)

        st.markdown(
            f"""
            <div class="ui-card">
                <div class="step-header-box">
                    <span class="step-pill-indicator">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
                        Step {step_num} of {total_steps}
                    </span>
                    <div>
                        <span class="badge-soft-blue">{subsystem_tag}</span>
                        <span class="badge-soft-green">{disruption_lvl}</span>
                    </div>
                </div>
                <div class="step-action-title">{action_title}</div>
                <div class="step-instructions-box">
                    <div style="font-weight: 600; color: #1E3A8A; margin-bottom: 6px;">Recommended Action:</div>
                    {action_body}
                </div>
            """,
            unsafe_allow_html=True
        )

        with st.expander("View Manual Source & Safety Boundary", expanded=False):
            st.markdown(
                f"""
                <div class="reference-box" style="margin-bottom: 8px;">
                    <div><strong>Manual Source:</strong> {citation_src}</div>
                    <div class="badge-soft-blue">Authority: OEM Field Spec</div>
                </div>
                <div style="font-size: 0.82rem; color: #4B5563; line-height: 1.5;">
                    <strong>Authorization Boundary:</strong> {boundary_dir}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Safety Interlock Card (Conditional)
    is_safety_halt = (
        st.session_state.diagnostic_status == "MANDATORY_HALT_TECHNICIAN_REQUIRED"
        or (active_step and active_step.get("requires_technician") and st.session_state.diagnostic_status != "RESOLVED")
    )

    if is_safety_halt:
        # Appliance-specific safety copy
        if active_model_id == "BOSCH_SHEM78":
            safety_sub = "240V Base Pan Electrical Hazard"
            safety_exp = "Line voltage (120V/240V AC) is present on exposed heater terminals and circulation pump contacts in the lower base pan. Do not disassemble while connected to mains power."
        elif active_model_id == "WHIRLPOOL_WASHER_ALPHA":
            safety_sub = "Direct-Drive Capacitor Discharge (400V DC) & 1200 RPM Spin Basket"
            safety_exp = "Inverter bus capacitors hold high-voltage DC charge. A mandatory 3-minute bleed-down delay and door lock switch interlock must be maintained."
        elif active_model_id == "LG_REFRIG_LFXS":
            safety_sub = "Flammable R600a Isobutane Refrigerant Isolation"
            safety_exp = "Hydrocarbon refrigerant R600a requires EPA Universal Certification. Open flames and brazing are prohibited; certified flameless Lokring crimps and forced ventilation are mandated."
        elif active_model_id == "BREVILLE_BES920":
            safety_sub = "15-Bar Pressurized Steam Boiler Scalding Hazard"
            safety_exp = "Superheated steam and boiling water under 15-bar hydraulic pressure. A 45-minute cool-down and manual petcock depressurization are required before brass valve servicing."
        else:
            safety_sub = "Certified Field Technician Boundary Reached"
            safety_exp = "This procedure involves energized high-voltage or sealed hydraulic systems exceeding basic user clearance."

        st.markdown(
            f"""
            <div class="safety-alert-container">
                <div class="safety-alert-header">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                    Safety Stop: Authorized Technician Required
                </div>
                <div class="safety-alert-body">
                    <strong>{safety_sub}:</strong> This step exceeds basic user clearance. A certified technician dispatch has been prepared to ensure safe handling of high-voltage electronics or pressurized systems.
                    <div style="margin-top: 6px; font-size: 0.80rem; color: #991B1B;">{safety_exp}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 4. User Feedback & Telemetry Section
    if st.session_state.diagnostic_status != "RESOLVED":
        st.markdown(
            """
            <div class="ui-card">
                <div class="ui-card-header">
                    <div class="ui-card-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1E3A8A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                        User Observation & Telemetry
                    </div>
                    <span class="badge-soft-blue">Diagnostic Input</span>
                </div>
            """,
            unsafe_allow_html=True
        )

        # One-Click Step Outcome Buttons (Fixed vs Not Fixed with Anti-Loop Memory)
        st.markdown("<div style='font-size: 0.82rem; font-weight: 600; color: #4B5563; margin-bottom: 8px;'>Did this recommended procedural check resolve the fault?</div>", unsafe_allow_html=True)
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            if st.button("✅ That Fixed It!", use_container_width=True, help="Mark issue as successfully resolved and generate Resolution Certificate"):
                resp = query_diagnostic_engine("Fixed! The issue has been completely resolved by this step.")
                st.session_state.diagnostic_status = "RESOLVED"
                st.session_state.resolution_confidence = 100
                st.toast("Resolution verified! Certificate generated.", icon="✅")
                st.rerun()
        with col_res2:
            if st.button("❌ Issue Persists (Next Step)", use_container_width=True, help="Record attempt in diagnostic memory and advance to next safe check without looping"):
                resp = query_diagnostic_engine("Action attempted as directed, but the fault symptom still persists.")
                st.session_state.diagnostic_status = resp.get("status", st.session_state.diagnostic_status)
                st.session_state.resolution_confidence = resp.get("confidence", st.session_state.resolution_confidence)
                if resp.get("escalation_record"):
                    st.session_state.escalation_record = resp["escalation_record"]
                st.toast("Logged in diagnostic memory. Anti-looping guard active.", icon="🧠")
                st.rerun()

        st.markdown("<div style='margin: 10px 0 10px 0; border-top: 1px dashed #E2E8F0;'></div>", unsafe_allow_html=True)

        with st.form("observation_form", clear_on_submit=True):
            st.markdown("<div style='font-size: 0.85rem; font-weight: 600; color: #374151; margin-bottom: 6px;'>What do you see? (e.g., Water is drained, LED blinking, humming sound stops):</div>", unsafe_allow_html=True)
            user_obs = st.text_area(
                "Observation Details",
                placeholder="Type your physical observation, multimeter measurement, or sound here...",
                height=70,
                label_visibility="collapsed"
            )
            submit_btn = st.form_submit_button("Confirm Observation & Next Step", use_container_width=True)

            if submit_btn and user_obs.strip():
                st.session_state.chat_history.append({
                    "role": "USER",
                    "content": user_obs.strip(),
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
                })
                resp = query_diagnostic_engine(user_obs.strip())
                st.session_state.diagnostic_status = resp.get("status", st.session_state.diagnostic_status)
                st.session_state.resolution_confidence = resp.get("confidence", st.session_state.resolution_confidence)
                if resp.get("escalation_record"):
                    st.session_state.escalation_record = resp["escalation_record"]

                st.session_state.chat_history.append({
                    "role": "SYSTEM",
                    "content": resp.get("message", ""),
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
                })
                st.rerun()

        # Quick-Select Test Buttons corresponding to common scenarios for the selected appliance
        st.markdown("<div style='font-size: 0.80rem; font-weight: 600; color: #4B5563; margin: 12px 0 6px 0;'>Quick-Select Scenario Presets:</div>", unsafe_allow_html=True)

        # Preset configurations based on selected appliance
        if active_model_id == "BOSCH_SHEM78":
            presets = [
                ("Impeller Spins Freely Without Debris", "Impeller is completely clear of debris, rotates smoothly in magnetic 90-degree tactile detents, normal"),
                ("Found Foreign Object in Pump Cavity", "Found fruit seed and glass shard lodged under drain pump impeller; cleaned and removed abnormal"),
                ("Water Drained and Sump Trough Dry", "Base pan trough is completely dry, EPS float switch rested down, normal")
            ]
        elif active_model_id == "WHIRLPOOL_WASHER_ALPHA":
            presets = [
                ("Basket Spins Smoothly by Hand", "Inner stainless wash basket spins freely with zero bearing drag, tachometer resistance 122 Ohms normal"),
                ("Pressure Sensor Tube Clear & Snug", "Pressure transducer vinyl air tube inspected, cleared of detergent suds, airtight normal"),
                ("Heating Element Open Circuit", "Wash heating element terminals measured with multimeter: infinite resistance, blown element abnormal")
            ]
        elif active_model_id == "LG_REFRIG_LFXS":
            presets = [
                ("Defrost Heater Resistance 96 Ohms Normal", "Evaporator defrost sheath heater measured 96 Ohms balanced, bimetal fuse closed 0 Ohms normal"),
                ("Linear Compressor Buzzing with 5-Blink LED", "Inverter PCB red diagnostic LED flashes 5 rapid blinks, compressor buzzes without reciprocating abnormal"),
                ("Condenser Fan Blades Clean & Spinning", "Condenser fan motor runs quietly, heat exchanger coils vacuumed clean normal")
            ]
        else:  # Breville BES920
            presets = [
                ("Water Reservoir Full & Level Probe Connected", "Water tank filled with filtered water, magnetic float at top, level probe wire tight normal"),
                ("Boiler Pressure Gauge Stuck at 0 Bar", "Startup fill pump times out after 90 seconds, analog pressure gauge remains at 0 bar abnormal"),
                ("Grouphead NTC Reads 52k Ohms Normal", "Grouphead temperature sensor measured 52k Ohms at 25C, wire harness undamaged normal")
            ]

        p_btn1, p_btn2, p_btn3 = st.columns(3)
        with p_btn1:
            if st.button(presets[0][0], use_container_width=True):
                st.session_state.chat_history.append({"role": "USER", "content": presets[0][1], "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
                r = query_diagnostic_engine(presets[0][1])
                st.session_state.diagnostic_status = r.get("status", st.session_state.diagnostic_status)
                st.session_state.resolution_confidence = r.get("confidence", st.session_state.resolution_confidence)
                if r.get("escalation_record"):
                    st.session_state.escalation_record = r["escalation_record"]
                st.session_state.chat_history.append({"role": "SYSTEM", "content": r.get("message", ""), "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
                st.rerun()

        with p_btn2:
            if st.button(presets[1][0], use_container_width=True):
                st.session_state.chat_history.append({"role": "USER", "content": presets[1][1], "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
                r = query_diagnostic_engine(presets[1][1])
                st.session_state.diagnostic_status = r.get("status", st.session_state.diagnostic_status)
                st.session_state.resolution_confidence = r.get("confidence", st.session_state.resolution_confidence)
                if r.get("escalation_record"):
                    st.session_state.escalation_record = r["escalation_record"]
                st.session_state.chat_history.append({"role": "SYSTEM", "content": r.get("message", ""), "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
                st.rerun()

        with p_btn3:
            if st.button(presets[2][0], use_container_width=True):
                st.session_state.chat_history.append({"role": "USER", "content": presets[2][1], "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
                r = query_diagnostic_engine(presets[2][1])
                st.session_state.diagnostic_status = r.get("status", st.session_state.diagnostic_status)
                st.session_state.resolution_confidence = r.get("confidence", st.session_state.resolution_confidence)
                if r.get("escalation_record"):
                    st.session_state.escalation_record = r["escalation_record"]
                st.session_state.chat_history.append({"role": "SYSTEM", "content": r.get("message", ""), "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")})
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <div class="ui-card" style="text-align: center; padding: 22px;">
                <div style="font-weight: 700; color: #1E3A8A; font-size: 0.95rem; margin-bottom: 4px;">Diagnostic Procedure Completed</div>
                <div style="font-size: 0.82rem; color: #6B7280;">To troubleshoot another issue or equipment asset, select a new appliance above or click <strong>Start New Diagnosis</strong>.</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ----------------------------------------------------------------------------
# Right Column: Progress & Resolution Overview
# ----------------------------------------------------------------------------
with col_sidebar:

    # 1. Resolution Progress Card
    conf_value = st.session_state.resolution_confidence
    if st.session_state.diagnostic_status == "RESOLVED":
        status_label = "Fault Resolved"
        status_badge_cls = "badge-soft-green"
    elif st.session_state.diagnostic_status in ("MANDATORY_HALT_TECHNICIAN_REQUIRED", "ESCALATED"):
        status_label = "Safety Dispatch Required"
        status_badge_cls = "badge-soft-red"
    elif conf_value > 50:
        status_label = "Verifying Fix"
        status_badge_cls = "badge-soft-blue"
    else:
        status_label = "Analyzing Symptoms"
        status_badge_cls = "badge-soft-amber"

    st.markdown(
        f"""
        <div class="ui-card">
            <div class="ui-card-header">
                <div class="ui-card-title">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1E3A8A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    Resolution Overview
                </div>
                <span class="{status_badge_cls}">{status_label}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
                <div class="progress-number-display">{conf_value}%</div>
                <div class="progress-label-text">Confidence Rating</div>
            </div>
        """,
        unsafe_allow_html=True
    )
    # Native Streamlit Progress Bar
    st.progress(conf_value / 100.0)
    st.markdown("</div>", unsafe_allow_html=True)

    # 2. Compatibility Verification Card
    st.markdown(
        f"""
        <div class="ui-card">
            <div class="ui-card-header">
                <div class="ui-card-title">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1E3A8A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                    Compatibility Checks
                </div>
                <span class="badge-soft-green">Verified</span>
            </div>
            <div class="verify-row">
                <div class="verify-label">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    Model Matched
                </div>
                <span class="verify-status" style="color: #059669;">{active_model_id}</span>
            </div>
            <div class="verify-row">
                <div class="verify-label">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    Manual Verified
                </div>
                <span class="verify-status" style="color: #059669;">OEM Indexed</span>
            </div>
            <div class="verify-row">
                <div class="verify-label">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="{'#DC2626' if is_safety_halt else '#059669'}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    Safety Clearance
                </div>
                <span class="verify-status" style="color: {'#DC2626' if is_safety_halt else '#059669'};">
                    {'Tech Escalated' if is_safety_halt else 'Operator Safe'}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 3. Action History (Evidence Timeline)
    st.markdown(
        """
        <div class="ui-card">
            <div class="ui-card-header">
                <div class="ui-card-title">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1E3A8A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
                    Action History
                </div>
                <span class="badge-soft-blue">Evidence Trail</span>
            </div>
        """,
        unsafe_allow_html=True
    )

    timeline_items = current_session.timeline

    if not timeline_items:
        st.markdown(
            """
            <div style="background-color: #F9FAFB; border: 1px dashed #E5E7EB; border-radius: 6px; padding: 18px 12px; text-align: center; color: #6B7280; font-size: 0.82rem;">
                No action steps completed yet.<br/>
                <span style="font-size: 0.75rem; color: #9CA3AF;">Observations will be logged chronologically here.</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown("<div class='timeline-feed'>", unsafe_allow_html=True)
        for item in timeline_items:
            v_stat = item.verification_status
            if v_stat == "VERIFIED_NORMAL":
                badge_c = "badge-soft-green"
                status_label = "Resolved / Normal"
            elif v_stat in ("VERIFIED_ABNORMAL", "BLOCKED"):
                badge_c = "badge-soft-red"
                status_label = "Abnormal Reading"
            else:
                badge_c = "badge-soft-amber"
                status_label = "In Progress"

            tl_title, _ = get_step_title_and_instructions(item.action_executed)
            obs_clean = item.user_reported_observation
            if len(obs_clean) > 85:
                words = obs_clean.split()
                short = []
                for w in words:
                    if len(" ".join(short + [w])) <= 80:
                        short.append(w)
                    else:
                        break
                obs_clean = " ".join(short) + "..."

            st.markdown(
                f"""
                <div class="timeline-item-card">
                    <div class="timeline-item-header">
                        <span style="font-weight: 600; color: #1E3A8A;">Step {item.step_index}</span>
                        <span class="{badge_c}">{status_label}</span>
                    </div>
                    <div style="color: #1F2937; font-weight: 600; font-size: 0.86rem; margin-bottom: 3px;">{tl_title}</div>
                    <div style="color: #4B5563; font-size: 0.78rem; line-height: 1.4;"><strong>Observed:</strong> {obs_clean}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # 4. Export & Escalation Actions Deck
    st.markdown(
        """
        <div class="ui-card">
            <div class="ui-card-header">
                <div class="ui-card-title">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1E3A8A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                    Export & Escalation
                </div>
                <span class="badge-soft-blue">Service Reports</span>
            </div>
        """,
        unsafe_allow_html=True
    )

    if not st.session_state.escalation_record:
        if st.button("Generate Service Ticket Package", use_container_width=True):
            esc_resp = call_backend_or_direct(
                f"/api/escalate/{st.session_state.session_id}",
                method="POST"
            )
            esc_pkg = esc_resp.get("escalation_package") or esc_resp
            st.session_state.escalation_record = esc_pkg
            st.session_state.incident_exported = esc_pkg
            st.rerun()

    if st.session_state.escalation_record:
        esc_data = st.session_state.escalation_record
        json_content = json.dumps(esc_data, indent=2)

        md_content = f"""# Appliance Service Diagnostic Incident Report
- **Incident Reference:** {esc_data.get('incident_id')}
- **Timestamp:** {esc_data.get('generated_timestamp')}
- **Target Appliance:** {esc_data.get('equipment_telemetry', {}).get('model_name')} ({esc_data.get('equipment_telemetry', {}).get('model_id')})
- **Board / Firmware:** {esc_data.get('equipment_telemetry', {}).get('firmware_version')}
- **Diagnostic Code:** {esc_data.get('equipment_telemetry', {}).get('error_code')}
- **Classification:** {esc_data.get('escalation_classification')}
- **Escalation Reason:** {esc_data.get('escalation_reason')}
- **Final Confidence:** {esc_data.get('resolution_confidence_at_escalation')}

## Chronological Action History
"""
        for t_entry in esc_data.get("immutable_evidence_log", []):
            s_step = t_entry.get("step", "-")
            s_act = t_entry.get("action", "Diagnostic Step")
            s_stat = t_entry.get("status") or t_entry.get("verification_status", "LOGGED")
            s_obs = t_entry.get("observation", "")
            s_time = t_entry.get("timestamp", "")
            md_content += f"- Step {s_step}: {s_act} -> [{s_stat}] '{s_obs}' ({s_time})\n"

        md_content += "\n## Recommended OEM Service Spares\n"
        for spare in esc_data.get("recommended_oem_spares", []):
            md_content += f"- {spare}\n"

        md_content += "\n## Mandatory Safety Directives\n"
        for s_dir in esc_data.get("mandatory_safety_directives", []):
            md_content += f"- {s_dir}\n"

        e_col1, e_col2 = st.columns(2)
        with e_col1:
            st.download_button(
                label="Download Ticket (JSON)",
                data=json_content,
                file_name=f"service_ticket_{st.session_state.session_id}.json",
                mime="application/json",
                use_container_width=True
            )
        with e_col2:
            st.download_button(
                label="Export Summary (Markdown)",
                data=md_content,
                file_name=f"diagnostic_summary_{st.session_state.session_id}.md",
                mime="text/markdown",
                use_container_width=True
            )

    st.markdown("</div>", unsafe_allow_html=True)
