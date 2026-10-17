import json
import logging
from typing import Any, Optional
from src.config import ERROR_CODES_PATH

logger = logging.getLogger("IndustrialDiagnostics.Tools")


def _load_error_codes_db() -> dict[str, Any]:
    """
    Internal loader for structured error codes JSON database.
    """
    if not ERROR_CODES_PATH.exists():
        raise FileNotFoundError(f"Diagnostic error code database not found at: {ERROR_CODES_PATH}")
    with open(ERROR_CODES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def lookup_error_code(code: str) -> dict[str, Any]:
    """
    Queries the local JSON database and returns structured metadata.
    Handles exact, case-insensitive, and partial prefix matches.
    """
    try:
        if not code or not isinstance(code, str):
            return {
                "status": "INVALID_INPUT",
                "code": str(code),
                "error_message": "Invalid error code supplied. Expected non-empty string.",
                "requires_authorized_technician": False
            }

        clean_code = code.strip().upper()
        database = _load_error_codes_db()

        # Direct exact match
        if clean_code in database:
            record = database[clean_code]
            return {
                "status": "SUCCESS",
                "code": record.get("code", clean_code),
                "model": record.get("model", "UNKNOWN"),
                "subsystem": record.get("subsystem", "GENERAL"),
                "symptom": record.get("symptom", "Not specified"),
                "description": record.get("description", ""),
                "severity": record.get("severity", "MEDIUM"),
                "requires_authorized_technician": record.get("requires_authorized_technician", False),
                "technician_authorization_boundary": record.get("technician_authorization_boundary", "Standard field procedures apply."),
                "initial_isolation_checks": record.get("initial_isolation_checks", []),
                "applicable_firmware": record.get("applicable_firmware", "All"),
                "error_message": None
            }

        # Fuzzy / prefix search across codes and symptoms
        for key, record in database.items():
            if clean_code in key or clean_code in record.get("code", "").upper():
                return {
                    "status": "SUCCESS",
                    "code": record.get("code", key),
                    "model": record.get("model", "UNKNOWN"),
                    "subsystem": record.get("subsystem", "GENERAL"),
                    "symptom": record.get("symptom", "Not specified"),
                    "description": record.get("description", ""),
                    "severity": record.get("severity", "MEDIUM"),
                    "requires_authorized_technician": record.get("requires_authorized_technician", False),
                    "technician_authorization_boundary": record.get("technician_authorization_boundary", "Standard field procedures apply."),
                    "initial_isolation_checks": record.get("initial_isolation_checks", []),
                    "applicable_firmware": record.get("applicable_firmware", "All"),
                    "error_message": None
                }

        return {
            "status": "NOT_FOUND",
            "code": clean_code,
            "error_message": f"Error code '{clean_code}' not found in corporate diagnostic database.",
            "requires_authorized_technician": False,
            "available_codes": list(database.keys())
        }

    except Exception as exc:
        logger.error(f"Execution fault in lookup_error_code for {code}: {str(exc)}", exc_info=True)
        return {
            "status": "SYSTEM_FAULT",
            "code": code,
            "error_message": f"Database read failure: {str(exc)}",
            "requires_authorized_technician": False
        }


def get_component_checklist(component: str, model: str) -> list[dict[str, Any]]:
    """
    Retrieves authorized inspection routines for specific hardware components
    filtered by target model specifications.
    Always returns a structured list of inspection step dictionaries.
    """
    try:
        if not component or not model:
            return [{
                "step_index": 0,
                "subsystem": "UNKNOWN",
                "action": "Specify both valid component and hardware model.",
                "disruption_level": "NONE",
                "requires_authorized_technician": False,
                "boundary_condition": "Parameter validation check.",
                "reference_standard": "Corporate IT Standard v4"
            }]

        comp_norm = component.lower().strip()
        model_norm = model.lower().strip()
        checklist: list[dict[str, Any]] = []

        is_apex = "apex" in model_norm or "arpx" in model_norm
        is_coreswitch = "coreswitch" in model_norm or "cs4k" in model_norm or "4000" in model_norm

        # 1. OPTICAL / TRANSCEIVER / SFP / FIBER
        if any(term in comp_norm for term in ["optic", "transceiver", "sfp", "fiber", "wan", "laser"]):
            checklist.extend([
                {
                    "step_index": 1,
                    "subsystem": "Optical Interface",
                    "action": "Query interface digital optical telemetry (DOM) via management CLI.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Read-only CLI query. No optical link disruption.",
                    "reference_standard": "IEEE 802.3ba / SFF-8472 DOM"
                },
                {
                    "step_index": 2,
                    "subsystem": "Optical Physical Layer",
                    "action": "Inspect LC connector seating and verify patch cable mechanical latch lock.",
                    "disruption_level": "LOW_DISRUPTION",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Operator level verification. Do not unseat while active traffic flows.",
                    "reference_standard": "Telcordia GR-326-CORE"
                },
                {
                    "step_index": 3,
                    "subsystem": "Optical Interface Cleaning",
                    "action": "Clean LC ferrule endface with dry cassette lint-free optical cleaner.",
                    "disruption_level": "LOW_DISRUPTION",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Class 1M radiation safety: Never inspect active fiber with magnifying optics.",
                    "reference_standard": "IEC 61300-3-35"
                },
                {
                    "step_index": 4,
                    "subsystem": "Transceiver Cage Hardware",
                    "action": "Unlatch and replace optical transceiver module (FRU).",
                    "disruption_level": "CRITICAL_INVASIVE",
                    "requires_authorized_technician": True,
                    "boundary_condition": "MANDATORY HALT: SFP28 transceiver replacement requires Certified Field Technician.",
                    "reference_standard": "NEBS Level 3 Physical Maintenance"
                }
            ])

        # 2. THERMAL / COOLING / FAN
        elif any(term in comp_norm for term in ["thermal", "fan", "cooling", "temp", "rpm", "airflow"]):
            checklist.extend([
                {
                    "step_index": 1,
                    "subsystem": "Chassis Environment",
                    "action": "Query thermal sensor matrix across all chassis zones via CLI.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Continuous telemetry capture. Standard threshold <= 85 C.",
                    "reference_standard": "ASHRAE TC 9.9 Thermal Guidelines"
                },
                {
                    "step_index": 2,
                    "subsystem": "Airflow Path Inspection",
                    "action": "Verify rack cold aisle intake temperature (<25 C) and inspect front/rear grilles for dust obstruction.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Exterior inspection only. Do not remove chassis top panels.",
                    "reference_standard": "Telcordia GR-63-CORE Airflow Integrity"
                },
                {
                    "step_index": 3,
                    "subsystem": "Fan Module Extraction",
                    "action": "Perform hot-swap extraction and replacement of fan unit / fan tray.",
                    "disruption_level": "CRITICAL_INVASIVE",
                    "requires_authorized_technician": True,
                    "boundary_condition": "MANDATORY HALT: 180-second thermal interlock window requires Authorized Field Technician with pre-aligned spare.",
                    "reference_standard": "IEC 62368-1 Industrial Safety"
                }
            ])

        # 3. POWER / PSU
        elif any(term in comp_norm for term in ["power", "psu", "voltage", "feed", "ac", "dc"]):
            checklist.extend([
                {
                    "step_index": 1,
                    "subsystem": "Power Telemetry",
                    "action": "Execute 'show system power' to audit AC input voltage, frequency, and secondary DC bus current.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Read-only telemetry verification.",
                    "reference_standard": "IEEE Std 1100 Power Quality"
                },
                {
                    "step_index": 2,
                    "subsystem": "External Feed Verification",
                    "action": "Check rear C14/C20 power cord retention clip and inspect PDU branch circuit breaker.",
                    "disruption_level": "LOW_DISRUPTION",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Do not manipulate upstream PDU switches without change control window.",
                    "reference_standard": "NFPA 70 National Electrical Code"
                },
                {
                    "step_index": 3,
                    "subsystem": "Power Module Replacement",
                    "action": "Disengage PSU lever and hot-swap redundant power supply module.",
                    "disruption_level": "CRITICAL_INVASIVE",
                    "requires_authorized_technician": True,
                    "boundary_condition": "MANDATORY HALT: Hazardous 400V stored internal DC bus. Authorized Field Technician mandatory.",
                    "reference_standard": "IEC 60950-1 / IEC 62368-1"
                }
            ])

        # 4. ROUTING / BGP / CONTROL PLANE
        elif any(term in comp_norm for term in ["bgp", "routing", "rib", "fib", "cpu", "control"]):
            checklist.extend([
                {
                    "step_index": 1,
                    "subsystem": "Control Plane Telemetry",
                    "action": "Audit BGP summary, prefix ingress table, and hold-time negotiations.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Operator level software telemetry.",
                    "reference_standard": "RFC 4271 BGP-4 Protocol Standard"
                },
                {
                    "step_index": 2,
                    "subsystem": "MTU & Interface Harmonization",
                    "action": "Verify MTU settings between local WAN interface and peer provider endpoint.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Read-only configuration audit.",
                    "reference_standard": "RFC 791 Internet Protocol"
                },
                {
                    "step_index": 3,
                    "subsystem": "Soft Reconfiguration",
                    "action": "Issue soft route refresh ('clear ip bgp <neighbor> soft in') without tearing down TCP session.",
                    "disruption_level": "LOW_DISRUPTION",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Soft reset allowed by L2 Network Administrator.",
                    "reference_standard": "RFC 2918 Route Refresh"
                }
            ])

        # 5. BACKPLANE / INTERCONNECT / ASIC
        elif any(term in comp_norm for term in ["backplane", "bus", "fabric", "serdes", "crc", "asic", "buffer"]):
            checklist.extend([
                {
                    "step_index": 1,
                    "subsystem": "Switch Fabric Telemetry",
                    "action": "Capture SerDes lane bit error rates and priority-queue tail drop counters.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Software register audit via diagnostic CLI.",
                    "reference_standard": "IEEE 802.3cd High-Speed Interconnect"
                },
                {
                    "step_index": 2,
                    "subsystem": "Dynamic Buffer Tuning",
                    "action": "Switch dynamic microburst buffer profile to ultra-burst mode.",
                    "disruption_level": "LOW_DISRUPTION",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Software QoS tuning. Requires network change authorization.",
                    "reference_standard": "Corporate Network QoS Policy"
                },
                {
                    "step_index": 3,
                    "subsystem": "Line Card & Backplane Reseating",
                    "action": "Extract line card, inspect backplane guide pins, and reseat using calibrated torque tool.",
                    "disruption_level": "CRITICAL_INVASIVE",
                    "requires_authorized_technician": True,
                    "boundary_condition": "MANDATORY HALT: Highly sensitive high-density backplane pins. Requires Authorized Field Technician.",
                    "reference_standard": "NEBS Level 3 Physical Maintenance"
                }
            ])

        # 6. POE / POWER OVER ETHERNET
        elif any(term in comp_norm for term in ["poe", "inline", "wattage", "pse", "pd"]):
            checklist.extend([
                {
                    "step_index": 1,
                    "subsystem": "PoE Power Distribution",
                    "action": "Audit inline power consumption per port and review total line card draw.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Read-only power allocation query.",
                    "reference_standard": "IEEE 802.3at / 802.3bt PoE Standards"
                },
                {
                    "step_index": 2,
                    "subsystem": "Port Priority Shedding",
                    "action": "Reassign non-critical access ports to Low Priority to preserve core infrastructure budget.",
                    "disruption_level": "LOW_DISRUPTION",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Operator level software configuration.",
                    "reference_standard": "Corporate Switch Management Standard"
                },
                {
                    "step_index": 3,
                    "subsystem": "Physical Loop Resistance Test",
                    "action": "Run Time Domain Reflectometry (TDR) test on overloaded cable runs to detect conductor fault.",
                    "disruption_level": "LOW_DISRUPTION",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Cable diagnostics may briefly flap endpoint link state.",
                    "reference_standard": "TIA-568-C.2 Balanced Twisted-Pair Cabling"
                }
            ])

        # 7. NVRAM / CRYPTO / STORAGE / TAMPER
        elif any(term in comp_norm for term in ["nvram", "flash", "storage", "crypto", "hsm", "tamper", "enclave"]):
            checklist.extend([
                {
                    "step_index": 1,
                    "subsystem": "Integrity State Capture",
                    "action": "Export cryptographic syslog and crash dump to secure TFTP/SCP audit repository.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Do not attempt chassis reboot or reset.",
                    "reference_standard": "FIPS 140-3 Security Requirements"
                },
                {
                    "step_index": 2,
                    "subsystem": "Secure Module Servicing",
                    "action": "Service physical NVRAM / Cryptographic HSM enclave using cryptographic authorization tokens.",
                    "disruption_level": "CRITICAL_INVASIVE",
                    "requires_authorized_technician": True,
                    "boundary_condition": "MANDATORY HALT: Physical enclosure breach protection. Authorized Field Technician / Security Engineer required.",
                    "reference_standard": "FIPS 140-3 Level 3 Physical Security"
                }
            ])

        # Fallback General Checklist
        if not checklist:
            checklist = [
                {
                    "step_index": 1,
                    "subsystem": f"{component.capitalize()} Telemetry",
                    "action": f"Capture diagnostic status and error counters for '{component}' on {model}.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Telemetry query via management plane.",
                    "reference_standard": "Corporate Standard Engineering Procedure"
                },
                {
                    "step_index": 2,
                    "subsystem": f"{component.capitalize()} Cabling & Seating",
                    "action": f"Perform non-invasive verification of external interfaces connecting to '{component}'.",
                    "disruption_level": "LOW_DISRUPTION",
                    "requires_authorized_technician": False,
                    "boundary_condition": "Visual inspection and cable seating verification.",
                    "reference_standard": "Corporate Standard Engineering Procedure"
                },
                {
                    "step_index": 3,
                    "subsystem": f"{component.capitalize()} Hardware Servicing",
                    "action": f"Invasive physical maintenance or replacement of '{component}' assembly.",
                    "disruption_level": "CRITICAL_INVASIVE",
                    "requires_authorized_technician": True,
                    "boundary_condition": "MANDATORY HALT: Invasive hardware modifications require Authorized Field Technician.",
                    "reference_standard": "Corporate IT Standard v4"
                }
            ]

        return checklist

    except Exception as exc:
        logger.error(f"Error formulating component checklist for {component} on {model}: {str(exc)}", exc_info=True)
        return [{
            "step_index": 0,
            "subsystem": "SYSTEM_FAULT",
            "action": f"Failed to retrieve checklist due to error: {str(exc)}",
            "disruption_level": "NONE",
            "requires_authorized_technician": False,
            "boundary_condition": "Error trap.",
            "reference_standard": "Internal Exception Handler"
        }]
