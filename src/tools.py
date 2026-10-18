import json
import logging
import re
from typing import Any, Optional
from src.config import ERROR_CODES_PATH

logger = logging.getLogger("ApplianceDiagnostics.Tools")


_error_db_cache: Optional[dict[str, Any]] = None


def _load_error_codes_db() -> dict[str, Any]:
    """
    Internal loader for structured error codes JSON database.
    """
    global _error_db_cache
    if _error_db_cache is None:
        if not ERROR_CODES_PATH.exists():
            raise FileNotFoundError(f"Diagnostic error code database not found at: {ERROR_CODES_PATH}")
        with open(ERROR_CODES_PATH, "r", encoding="utf-8") as f:
            _error_db_cache = json.load(f)
    return _error_db_cache


def load_error_db() -> dict[str, Any]:
    """Public alias to load error code database dictionary."""
    return _load_error_codes_db()


def list_products() -> list[str]:
    """All unique product names in the error database."""
    db = load_error_db()
    return sorted({record.get("model", record.get("model_id", "General")) for record in db.values()})


def list_error_codes(product: Optional[str] = None) -> list[dict]:
    """List of error codes, optionally filtered by product."""
    db = load_error_db()
    return [
        {
            "code": code,
            "symptom": rec.get("symptom", rec.get("description", "")),
            "severity": rec.get("severity", "MEDIUM"),
            "model": rec.get("model", rec.get("model_id", "")),
        }
        for code, rec in db.items()
        if product is None or rec.get("model") == product or rec.get("model_id") == product
    ]


def _normalize_code(code: str) -> str:
    """Removes extra spaces and special punctuation for fuzzy matching."""
    return re.sub(r'[\s\-_]+', '', code.strip().upper())


def lookup_error_code(code: str) -> dict[str, Any]:
    """
    Queries data/error_codes.json for model and error code with case-insensitive search.
    Handles exact, normalized, prefix, and alias matches.
    Always returns a structured Python dictionary.
    """
    try:
        if not code or not isinstance(code, str) or not code.strip():
            return {
                "status": "INVALID_INPUT",
                "found": False,
                "code": str(code),
                "product": "UNKNOWN",
                "model_id": "UNKNOWN",
                "model": "UNKNOWN",
                "subsystem": "GENERAL",
                "symptom": "",
                "description": "",
                "severity": "LOW",
                "requires_technician": False,
                "requires_authorized_technician": False,
                "citation": "N/A",
                "initial_steps": [],
                "initial_isolation_checks": [],
                "safety_boundary": "Parameter validation check.",
                "technician_authorization_boundary": "Parameter validation check.",
                "error_message": "Invalid error code supplied. Expected non-empty string.",
                "message": "Invalid error code supplied."
            }

        raw_query = code.strip()
        query_upper = raw_query.upper()
        norm_query = _normalize_code(query_upper)
        database = _load_error_codes_db()

        matched_record: Optional[dict[str, Any]] = None
        matched_key = ""

        # 1. Exact match against DB keys (case-insensitive)
        for key, record in database.items():
            if key.upper() == query_upper or record.get("code", "").upper() == query_upper:
                matched_record = record
                matched_key = key
                break

        # 2. Normalized match (ignoring spaces, dashes, e.g. "F06E01" vs "F06 E01", "BLNK5" vs "BLNK-5")
        if not matched_record:
            for key, record in database.items():
                if _normalize_code(key) == norm_query or _normalize_code(record.get("code", "")) == norm_query:
                    matched_record = record
                    matched_key = key
                    break

        # 3. Substring match
        if not matched_record:
            for key, record in database.items():
                if norm_query in _normalize_code(key) or norm_query in _normalize_code(record.get("code", "")):
                    matched_record = record
                    matched_key = key
                    break

        if matched_record:
            req_tech = matched_record.get("requires_authorized_technician", matched_record.get("requires_technician", False))
            steps = matched_record.get("initial_steps") or matched_record.get("initial_isolation_checks") or []
            citation = matched_record.get("citation", "MANUAL-REF-STANDARD")
            model_id = matched_record.get("model_id") or matched_record.get("model", "UNKNOWN")
            prod = matched_record.get("model") or model_id
            subsystem = matched_record.get("subsystem", "GENERAL")
            desc = matched_record.get("description", "")
            symptom = matched_record.get("symptom", desc)
            severity = matched_record.get("severity", "MEDIUM")

            tech_boundary = matched_record.get("technician_authorization_boundary")
            if not tech_boundary:
                if req_tech:
                    tech_boundary = f"MANDATORY HALT: Invasive component replacement or sealed system servicing on {model_id} requires Authorized Field Technician."
                else:
                    tech_boundary = "Level 1 operator may execute non-invasive external inspections, filter cleanouts, and basic electrical checks."

            return {
                "status": "SUCCESS",
                "found": True,
                "code": matched_record.get("code", matched_key),
                "model_id": model_id,
                "model": prod,
                "product": prod,
                "subsystem": subsystem,
                "symptom": symptom,
                "description": desc,
                "severity": severity,
                "requires_technician": req_tech,
                "requires_authorized_technician": req_tech,
                "citation": citation,
                "initial_steps": steps,
                "initial_isolation_checks": steps,
                "safety_boundary": tech_boundary,
                "technician_authorization_boundary": tech_boundary,
                "applicable_firmware": matched_record.get("applicable_firmware", "ANY"),
                "error_message": None
            }

        prefix = query_upper.split("-")[0] if "-" in query_upper else ""
        similar = [c for c in database if prefix and c.startswith(prefix)]

        return {
            "status": "NOT_FOUND",
            "found": False,
            "code": query_upper,
            "product": "UNKNOWN",
            "model_id": "UNKNOWN",
            "model": "UNKNOWN",
            "subsystem": "GENERAL",
            "symptom": "",
            "description": f"Error code '{query_upper}' was not located in active appliance diagnostic database.",
            "severity": "LOW",
            "requires_technician": False,
            "requires_authorized_technician": False,
            "citation": "N/A",
            "initial_steps": [],
            "initial_isolation_checks": [],
            "safety_boundary": "No boundary defined.",
            "technician_authorization_boundary": "No boundary defined.",
            "error_message": f"Error code '{query_upper}' not found in corporate appliance diagnostic database.",
            "message": f"Error code '{query_upper}' not found in database.",
            "similar_codes": similar[:5],
            "available_codes": list(database.keys())
        }

    except Exception as exc:
        logger.error(f"Execution fault in lookup_error_code for {code}: {str(exc)}", exc_info=True)
        return {
            "status": "SYSTEM_FAULT",
            "code": str(code),
            "model_id": "UNKNOWN",
            "model": "UNKNOWN",
            "subsystem": "GENERAL",
            "description": "",
            "severity": "CRITICAL",
            "requires_technician": False,
            "requires_authorized_technician": False,
            "citation": "N/A",
            "initial_steps": [],
            "initial_isolation_checks": [],
            "technician_authorization_boundary": "System fault encountered.",
            "error_message": f"Database read failure: {str(exc)}"
        }


def get_component_checklist(component: str, model: str = "") -> list[dict[str, Any]]:
    """
    Retrieves authorized inspection routines for specific subsystems:
    Drainage, Optical, Hydraulic, Inverter, Thermal.
    Tailors the routines based on the target equipment platform when specified:
    - Bosch 800 Series Dishwasher (BOSCH_SHEM78)
    - Whirlpool Front-Load Washer (WHIRLPOOL_WASHER_ALPHA)
    - LG Smart French-Door Refrigerator (LG_REFRIG_LFXS)
    - Breville Dual Boiler Espresso Machine (BREVILLE_BES920)

    Always returns a structured list of inspection step dictionaries.
    """
    try:
        if not component or not isinstance(component, str) or not component.strip():
            return [{
                "step_index": 1,
                "subsystem": "GENERAL",
                "action": "Specify a valid subsystem: Drainage, Optical, Hydraulic, Inverter, or Thermal.",
                "disruption_level": "NON_DISRUPTIVE",
                "requires_technician": False,
                "requires_authorized_technician": False,
                "boundary_condition": "Parameter validation check.",
                "citation": "APPLIANCE-GEN-CHECKLIST"
            }]

        comp_norm = component.lower().strip()
        model_norm = (model or "").lower().strip()
        checklist: list[dict[str, Any]] = []

        # 1. DRAINAGE SUBSYSTEM
        if any(term in comp_norm for term in ["drain", "drainage", "pump", "sump", "filter", "hose", "flapper", "impeller"]):
            if "bosch" in model_norm or "shem78" in model_norm or "shpm78" in model_norm:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Drainage",
                        "action": "Remove lower dish rack, twist stainless microfilter cylinder 90 degrees counter-clockwise, and clean mesh basket under hot water.",
                        "disruption_level": "NON_DISRUPTIVE",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Consumer maintenance routine.",
                        "citation": "BOSCH_SHEM78_SM_SEC4.3"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Drainage",
                        "action": "Pry white plastic drain pump impeller cover from sump housing and verify 5-vane impeller is free of glass shards, seeds, or debris.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Inspect impeller rotation detents; do not pry shaft with metal picks.",
                        "citation": "BOSCH_SHEM78_SM_SEC4.4"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Drainage",
                        "action": "Inspect rubber non-return flapper check valve adjacent to impeller to verify it seats flat against orifice and is not warped or stuck.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Verify supple seal.",
                        "citation": "BOSCH_SHEM78_SM_SEC4.4"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Drainage",
                        "action": "Measure BLDC drain pump motor winding resistance across 3 terminals (nominal: 85 to 105 Ohms balanced).",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: Replacing BLDC drain pump or lower wire harness requires Authorized Field Technician.",
                        "citation": "BOSCH_SHEM78_SM_SEC4.4"
                    }
                ])
            elif "whirlpool" in model_norm or "alpha" in model_norm or "vmw" in model_norm or "washer" in model_norm:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Drainage",
                        "action": "Place shallow catch pan beneath lower front access door and drain standing water using auxiliary pull-out drain tube.",
                        "disruption_level": "NON_DISRUPTIVE",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Operator routine water clearance.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.3"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Drainage",
                        "action": "Unscrew round coin trap filter plug counter-clockwise, extract lint basket, and clear coins, hairpins, and lint accumulation.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Re-tighten filter plug to prevent tub leakage.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.3"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Drainage",
                        "action": "Spin drain pump impeller through filter housing cavity to verify magnetic pulsing without motor shaft seizure.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Check for foreign object binding.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.3"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Drainage",
                        "action": "Replace drain pump motor assembly and calibrate ACU drain pump triac driver.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: ACU board or drain pump replacement requires Authorized Field Technician.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.3"
                    }
                ])
            else:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Drainage",
                        "action": "Inspect drain hose routing for elevation loops, kinks, pinching, or disposal barb knockout blockage.",
                        "disruption_level": "NON_DISRUPTIVE",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "External visual inspection.",
                        "citation": "APPLIANCE-DRN-STD-01"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Drainage",
                        "action": "Remove and inspect debris trap filter, cleaning food particles and lint under warm running water.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Standard operator maintenance.",
                        "citation": "APPLIANCE-DRN-STD-02"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Drainage",
                        "action": "Measure drain pump winding resistance and verify free impeller rotation.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Multi-meter verification.",
                        "citation": "APPLIANCE-DRN-STD-03"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Drainage",
                        "action": "Replace drain pump assembly or main control board driver circuitry.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: Electrical drive replacement requires Authorized Field Technician.",
                        "citation": "APPLIANCE-DRN-STD-04"
                    }
                ])

        # 2. OPTICAL SUBSYSTEM
        elif any(term in comp_norm for term in ["optic", "optical", "turbidity", "sensor", "aquasensor", "prism", "phototransistor"]):
            checklist.extend([
                {
                    "step_index": 1,
                    "subsystem": "Optical",
                    "action": "Locate optical turbidity sensor (AquaSensor) in sump chamber or door optical encoder.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_technician": False,
                    "requires_authorized_technician": False,
                    "boundary_condition": "Read-only inspection.",
                    "citation": "BOSCH_SHEM78_SM_SEC4.6"
                },
                {
                    "step_index": 2,
                    "subsystem": "Optical",
                    "action": "Wipe optical prism lens surface with 99% isopropyl alcohol swab to eliminate calcium deposit glaze or grease film.",
                    "disruption_level": "LOW_DISRUPTION",
                    "requires_technician": False,
                    "requires_authorized_technician": False,
                    "boundary_condition": "Do not use abrasive scouring pads on optical prism.",
                    "citation": "BOSCH_SHEM78_SM_SEC4.6"
                },
                {
                    "step_index": 3,
                    "subsystem": "Optical",
                    "action": "Run diagnostic sensor calibration program to verify phototransistor signal voltage (nominal: 3.8V to 4.6V DC in clear water).",
                    "disruption_level": "LOW_DISRUPTION",
                    "requires_technician": False,
                    "requires_authorized_technician": False,
                    "boundary_condition": "Verify baseline calibration voltage.",
                    "citation": "BOSCH_SHEM78_SM_SEC4.6"
                },
                {
                    "step_index": 4,
                    "subsystem": "Optical",
                    "action": "Extract optical sensor harness and replace optoelectronic transmitter module in sump wall.",
                    "disruption_level": "CRITICAL_INVASIVE",
                    "requires_technician": True,
                    "requires_authorized_technician": True,
                    "boundary_condition": "MANDATORY HALT: Optical sensor module replacement and watertight sump resealing requires Authorized Field Technician.",
                    "citation": "BOSCH_SHEM78_SM_SEC4.6"
                }
            ])

        # 3. HYDRAULIC SUBSYSTEM
        elif any(term in comp_norm for term in ["hydraul", "water", "pressure", "valve", "solenoid", "boiler fill", "air dome", "aps", "flood"]):
            if "breville" in model_norm or "bes920" in model_norm or "bes980" in model_norm or "espresso" in model_norm:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Hydraulic",
                        "action": "Verify rear water reservoir is seated, cold filtered water is present, and magnetic level float is free at top of chamber.",
                        "disruption_level": "NON_DISRUPTIVE",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Operator level reservoir inspection.",
                        "citation": "BREVILLE_BES920XL_SM_SEC3.1"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Hydraulic",
                        "action": "Inspect silicone intake valve and stainless mesh filter screen at machine water reservoir floor for calcium scale buildup.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Clean mesh under warm water.",
                        "citation": "BREVILLE_BES920XL_SM_SEC3.1"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Hydraulic",
                        "action": "Check rear brass manual boiler drain petcock valves; verify they are turned fully horizontal to seal boilers.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Inspect for valve weeping.",
                        "citation": "BREVILLE_BES920XL_SM_SEC3.1"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Hydraulic",
                        "action": "Remove top chassis cover, disconnect conductive water level probe on steam boiler, and clean green verdigris corrosion from spade connector.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "WARNING: Ensure machine is completely cooled down and depressurized (0 bar).",
                        "citation": "BREVILLE_BES920XL_SM_SEC3.1"
                    },
                    {
                        "step_index": 5,
                        "subsystem": "Hydraulic",
                        "action": "Replace 2-way brass boiler fill solenoid valve or rebuild 15-bar ULKA hydraulic pump assembly.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: 15-bar hydraulic manifold and brass solenoid replacement requires Authorized Field Technician.",
                        "citation": "BREVILLE_BES920XL_SM_SEC3.1"
                    }
                ])
            elif "whirlpool" in model_norm or "alpha" in model_norm or "washer" in model_norm:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Hydraulic",
                        "action": "Inspect 1/4-inch clear vinyl pressure sensor tube between Analog Pressure Sensor (APS) and tub sump air dome for kinks, tears, or suds blockage.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Ensure cabinet top lid is removed with power disconnected.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.1"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Hydraulic",
                        "action": "Disconnect vinyl tube from APS sensor nipple and blow gently down tube to purge trapped detergent foam or lint from sump air dome bell.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Verify free airflow through lower air bell.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.1"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Hydraulic",
                        "action": "Verify 5.0 VDC reference voltage across ACU connector J3 pins 1 and 3.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Multi-meter probe check.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.1"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Hydraulic",
                        "action": "Replace Analog Pressure Sensor or replace multi-port cold/hot water inlet valve manifold.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: Transducer replacement or valve manifold install requires Authorized Field Technician.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.1"
                    }
                ])
            elif "bosch" in model_norm or "shem78" in model_norm:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Hydraulic",
                        "action": "Turn off water shutoff valve and inspect lower condensation base trough for water pooling triggering E15 float switch.",
                        "disruption_level": "NON_DISRUPTIVE",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Disconnect 120V/240V power at breaker before removing toe-kick.",
                        "citation": "BOSCH_SHEM78_SM_SEC4.1"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Hydraulic",
                        "action": "Evacuate moisture from lower trough using sponge or wet-vacuum to allow EPS float disc to drop back to rest position.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Confirm float microswitch clicks open.",
                        "citation": "BOSCH_SHEM78_SM_SEC4.1"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Hydraulic",
                        "action": "Inspect water inlet valve hose connector and sump perimeter gasket for active drip trails.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Visual leak tracing.",
                        "citation": "BOSCH_SHEM78_SM_SEC4.1"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Hydraulic",
                        "action": "Replace circulation heat pump volute seal, water inlet valve, or sump silicone gasket assembly.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: 240V base pan electrical hazard; mechanical teardown requires Authorized Field Technician.",
                        "citation": "BOSCH_SHEM78_SM_SEC4.1"
                    }
                ])
            else:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Hydraulic",
                        "action": "Audit incoming water supply pressure, shutoff valve positions, and braided line connections.",
                        "disruption_level": "NON_DISRUPTIVE",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "External hydraulic audit.",
                        "citation": "APPLIANCE-HYD-STD-01"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Hydraulic",
                        "action": "Inspect inlet filter mesh screens and pressure sensing lines for calcium or debris restriction.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Mechanical cleaning routine.",
                        "citation": "APPLIANCE-HYD-STD-02"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Hydraulic",
                        "action": "Replace pressurized hydraulic valves or internal flow manifold components.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: Pressurized hydraulic repairs require Authorized Field Technician.",
                        "citation": "APPLIANCE-HYD-STD-03"
                    }
                ])

        # 4. INVERTER SUBSYSTEM
        elif any(term in comp_norm for term in ["inverter", "compressor", "motor", "drive", "ipm", "tach", "blnk", "pmsm", "bldc"]):
            if "lg" in model_norm or "lfxs" in model_norm or "lrfcs" in model_norm or "refrig" in model_norm:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Inverter",
                        "action": "Observe 3-minute PCB bleed-down delay, remove machine compartment rear cover, and count red diagnostic LED blinks on Main Inverter Board.",
                        "disruption_level": "NON_DISRUPTIVE",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Verify blink pattern (5 blinks: locked rotor, 6 blinks: IPM overcurrent).",
                        "citation": "LG_LFXS_SERVICEMAN_SEC6.2"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Inverter",
                        "action": "Inspect condenser cooling fan assembly to verify fan blades spin freely and are not choked by lint or wire harnesses.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Clean wire condenser grid with vacuum brush.",
                        "citation": "LG_LFXS_SERVICEMAN_SEC6.3"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Inverter",
                        "action": "Measure linear compressor stator resistance across pins U and V (nominal: 6.0 to 11.0 Ohms; > 5 Megohms to ground).",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Ensure AC line cord is disconnected.",
                        "citation": "LG_LFXS_SERVICEMAN_SEC6.2"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Inverter",
                        "action": "Replace Linear Inverter Compressor (FLB075LANA) involving flammable R600a Isobutane evacuation, nitrogen purge, and flameless Lokring fittings.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: Flammable R600a refrigerant requires EPA Universal Certified Field Technician.",
                        "citation": "LG_LFXS_SERVICEMAN_SEC6.2"
                    }
                ])
            elif "whirlpool" in model_norm or "alpha" in model_norm or "washer" in model_norm:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Inverter",
                        "action": "Unplug washer, wait 3 minutes for MCU bus capacitors to discharge, and remove rear sheet metal panel.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "High voltage DC bus bleed-down check.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.2"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Inverter",
                        "action": "Inspect 3-wire tachometer sensor harness between MCU connector J9 and motor stator hub for wire chafe or broken pins.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Visual wiring continuity check.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.2"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Inverter",
                        "action": "Measure tachometer generator resistance across connector J9 pins 1 and 2 (nominal: 115 to 130 Ohms).",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Multimeter resistance check.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.2"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Inverter",
                        "action": "Replace 3-phase direct-drive motor stator core or Motor Control Unit (MCU) inverter board.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: Direct drive stator rotor replacement requires Authorized Field Technician.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.2"
                    }
                ])
            else:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Inverter",
                        "action": "Audit AC mains supply line voltage under load to confirm absence of voltage sag below 98V AC.",
                        "disruption_level": "NON_DISRUPTIVE",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Voltage multimeter check.",
                        "citation": "APPLIANCE-INV-STD-01"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Inverter",
                        "action": "Inspect inverter drive PCB for capacitor bulging, heat sink thermal paste dry-out, or fuse burnout.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Visual board inspection.",
                        "citation": "APPLIANCE-INV-STD-02"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Inverter",
                        "action": "Measure 3-phase motor stator winding balance across all three phase legs.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Resistance balance check.",
                        "citation": "APPLIANCE-INV-STD-03"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Inverter",
                        "action": "Replace inverter drive board or BLDC drive motor assembly.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: Inverter power electronics replacement requires Authorized Field Technician.",
                        "citation": "APPLIANCE-INV-STD-04"
                    }
                ])

        # 5. THERMAL SUBSYSTEM
        elif any(term in comp_norm for term in ["thermal", "heater", "heat", "temp", "ntc", "thermistor", "defrost", "runaway", "grouphead"]):
            if "breville" in model_norm or "bes920" in model_norm or "espresso" in model_norm:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Thermal",
                        "action": "Unplug machine immediately from wall receptacle and allow unit to cool completely to ambient room temperature (minimum 45 minutes).",
                        "disruption_level": "NON_DISRUPTIVE",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "SCALDING HAZARD: Do not open hot boiler fittings.",
                        "citation": "BREVILLE_BES920XL_SM_SEC3.2"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Thermal",
                        "action": "Remove top chassis cover (6 Torx T10 screws) and inspect grouphead NTC thermistor harness wires for insulation chafe against brass collar.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Visual wiring check.",
                        "citation": "BREVILLE_BES920XL_SM_SEC3.2"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Thermal",
                        "action": "Measure NTC thermistor resistance at room temperature (nominal: 50k Ohms at 25 C / 77 F).",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Multimeter resistance check.",
                        "citation": "BREVILLE_BES920XL_SM_SEC3.3"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Thermal",
                        "action": "Test grouphead Solid State Relay (SSR) for shorted triac output providing uncontrolled continuous 120V to heater.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Bench test SSR triac gate.",
                        "citation": "BREVILLE_BES920XL_SM_SEC3.2"
                    },
                    {
                        "step_index": 5,
                        "subsystem": "Thermal",
                        "action": "Replace grouphead cartridge heating element, SSR module, or threaded steam boiler NTC probe.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: 15-bar pressurized steam boiler teardown requires Authorized Field Technician.",
                        "citation": "BREVILLE_BES920XL_SM_SEC3.2"
                    }
                ])
            elif "lg" in model_norm or "lfxs" in model_norm or "refrig" in model_norm:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Thermal",
                        "action": "Remove freezer compartment rear back wall panel to expose aluminum defrost sheath heater and evaporator coil fins.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Disconnect AC power cord before panel removal.",
                        "citation": "LG_LFXS_SERVICEMAN_SEC6.7"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Thermal",
                        "action": "Measure defrost sheath heater resistance across 2-pin harness connector (nominal: 80 to 120 Ohms; open indicates broken heater).",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Multimeter resistance test.",
                        "citation": "LG_LFXS_SERVICEMAN_SEC6.7"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Thermal",
                        "action": "Test defrost bimetal thermal safety fuse continuity (must read 0 Ohms closed when chilled below freezing; open indicates blown safety fuse).",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Bimetal continuity test.",
                        "citation": "LG_LFXS_SERVICEMAN_SEC6.7"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Thermal",
                        "action": "Measure defrost NTC temperature sensor resistance (nominal: 30k Ohms at 0 C / 32 F, 10k Ohms at 25 C / 77 F).",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Temperature thermistor calibration curve.",
                        "citation": "LG_LFXS_SERVICEMAN_SEC6.7"
                    },
                    {
                        "step_index": 5,
                        "subsystem": "Thermal",
                        "action": "Replace Main Micom PCB defrost power relay or replace evaporator defrost sheath heater assembly.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: PCB repair or sealed evaporator defrost component install requires Authorized Field Technician.",
                        "citation": "LG_LFXS_SERVICEMAN_SEC6.7"
                    }
                ])
            elif "whirlpool" in model_norm or "washer" in model_norm:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Thermal",
                        "action": "Unplug washer from wall outlet and remove rear cabinet service access panel.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Power disconnect mandatory.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.4"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Thermal",
                        "action": "Inspect wash heating element terminals at lower tub base for thermal burns or loose spade connectors.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Visual inspection.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.4"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Thermal",
                        "action": "Measure wash heating element resistance (nominal: 12 to 18 Ohms; infinite indicates blown heating element).",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Multimeter resistance check.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.4"
                    },
                    {
                        "step_index": 4,
                        "subsystem": "Thermal",
                        "action": "Measure ground insulation resistance between heater terminal and tub metal ground (> 10 Megohms).",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Ground fault leakage test.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.4"
                    },
                    {
                        "step_index": 5,
                        "subsystem": "Thermal",
                        "action": "Replace failed wash heating element and compression gasket, or replace ACU heater relay.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: Heating element replacement requires Authorized Field Technician.",
                        "citation": "WHIRLPOOL_W11663204_REV_B_SEC5.4"
                    }
                ])
            else:
                checklist.extend([
                    {
                        "step_index": 1,
                        "subsystem": "Thermal",
                        "action": "Inspect heating element terminal wiring and thermal sensor harness connections.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Visual terminal inspection.",
                        "citation": "APPLIANCE-THM-STD-01"
                    },
                    {
                        "step_index": 2,
                        "subsystem": "Thermal",
                        "action": "Measure heating element resistance and verify proper resistance reading.",
                        "disruption_level": "LOW_DISRUPTION",
                        "requires_technician": False,
                        "requires_authorized_technician": False,
                        "boundary_condition": "Multimeter measurement.",
                        "citation": "APPLIANCE-THM-STD-02"
                    },
                    {
                        "step_index": 3,
                        "subsystem": "Thermal",
                        "action": "Replace heating element or thermal regulation relay.",
                        "disruption_level": "CRITICAL_INVASIVE",
                        "requires_technician": True,
                        "requires_authorized_technician": True,
                        "boundary_condition": "MANDATORY HALT: Thermal element replacement requires Authorized Field Technician.",
                        "citation": "APPLIANCE-THM-STD-03"
                    }
                ])

        else:
            # Fallback general inspection
            checklist.extend([
                {
                    "step_index": 1,
                    "subsystem": "GENERAL",
                    "action": f"Perform non-invasive visual inspection of {component} subsystem wiring and mechanical fittings.",
                    "disruption_level": "NON_DISRUPTIVE",
                    "requires_technician": False,
                    "requires_authorized_technician": False,
                    "boundary_condition": "Read-only inspection.",
                    "citation": "APPLIANCE-GEN-STD-01"
                },
                {
                    "step_index": 2,
                    "subsystem": "GENERAL",
                    "action": f"Measure operating supply voltages and signal continuity on {component} control harnesses.",
                    "disruption_level": "LOW_DISRUPTION",
                    "requires_technician": False,
                    "requires_authorized_technician": False,
                    "boundary_condition": "Multimeter measurement.",
                    "citation": "APPLIANCE-GEN-STD-02"
                },
                {
                    "step_index": 3,
                    "subsystem": "GENERAL",
                    "action": f"Invasive disassembly and electro-mechanical component replacement for {component}.",
                    "disruption_level": "CRITICAL_INVASIVE",
                    "requires_technician": True,
                    "requires_authorized_technician": True,
                    "boundary_condition": "MANDATORY HALT: Invasive component replacement requires Authorized Field Technician.",
                    "citation": "APPLIANCE-GEN-STD-03"
                }
            ])

        return checklist

    except Exception as exc:
        logger.error(f"Execution fault in get_component_checklist: {str(exc)}", exc_info=True)
        return [{
            "step_index": 1,
            "subsystem": "SYSTEM_FAULT",
            "action": f"Routine generation fault: {str(exc)}",
            "disruption_level": "NON_DISRUPTIVE",
            "requires_technician": False,
            "requires_authorized_technician": False,
            "boundary_condition": "Exception handled safely.",
            "citation": "APPLIANCE-FAULT"
        }]


# ============================================================================
# Multi-Tier RAG & Evaluation Helper Tools
# ============================================================================

def get_troubleshooting_checklist(code: str) -> dict[str, Any]:
    """Return ordered diagnostic steps for an error code with safety flags."""
    info = lookup_error_code(code)
    if not info.get("found"):
        return {"found": False, "code": info.get("code", code), "message": info.get("message", "Not found"), "steps": []}

    steps = []
    checks = info.get("initial_isolation_checks") or info.get("initial_steps") or []
    for number, text in enumerate(checks, start=1):
        is_stop = text.lower().startswith("halt procedure") or "technician" in text.lower() or "mandatory halt" in text.lower()
        steps.append({
            "number": number,
            "text": text,
            "is_stop_step": is_stop,
            "requires_technician": is_stop,
            "source": f"Error DB / {info['code']}",
            "doc_type": "error_code_database",
        })
    return {
        "found": True,
        "code": info["code"],
        "product": info.get("product", info.get("model")),
        "severity": info["severity"],
        "safety_boundary": info.get("safety_boundary", info.get("technician_authorization_boundary")),
        "steps": steps,
    }


def search_manual(
    query: str,
    product: Optional[str] = None,
    software_version: Optional[str] = None,
) -> dict[str, Any]:
    """Search manuals, bulletins, known issues, and escalation rules via 3-Factor Re-Ranking."""
    from src.rag import get_knowledge_base

    hits = get_knowledge_base().search(
        query=query,
        product=product,
        software_version=software_version,
    )
    return {
        "found": bool(hits),
        "results": [
            {
                "procedure_id": h["id"],
                "title": h["title"],
                "product": h["product"],
                "doc_type": h.get("doc_type", "product_manual"),
                "disruption_level": h.get("disruption_level", "Standard"),
                "needs_technician": h.get("needs_technician", False),
                "composite_score": h.get("composite_score", 0.0),
                "similarity_score": h.get("similarity_score", 0.0),
                "model_score": h.get("model_score", 0.0),
                "authority_score": h.get("authority_score", 0.60),
                "ordered_checks": h.get("ordered_checks", []),
                "hazard_tags": h.get("hazard_tags", []),
                "text": h["text"],
            }
            for h in hits
        ],
    }


def steps_from_manual_passage(passage: dict) -> list[dict]:
    """Turn a manual, bulletin, or known issue into an ordered list of steps."""
    if passage.get("ordered_checks"):
        steps = []
        for check in passage["ordered_checks"]:
            req_tech = bool(check.get("requires_technician"))
            steps.append({
                "number": check.get("step", len(steps) + 1),
                "text": check.get("action", ""),
                "is_stop_step": req_tech or "halt procedure" in check.get("action", "").lower() or "mandatory halt" in check.get("action", "").lower(),
                "requires_technician": req_tech,
                "hazard_notice": check.get("hazard_notice", ""),
                "source": f"{passage.get('doc_type', 'Document').replace('_', ' ').title()} / {passage.get('id', passage.get('procedure_id', 'REF'))}",
                "doc_type": passage.get("doc_type", "product_manual"),
            })
        return steps

    steps = []
    text_content = passage.get("text", "")
    for line in text_content.splitlines():
        match = re.match(r"^\s*(\d+)\.\s+(.*)", line)
        if not match:
            match = re.match(r"^-\s*Step\s*(\d+)\s*(\([^)]+\))?:\s*(.*)", line, re.I)
            if match:
                text = match.group(3).strip()
                is_stop = bool(re.search(r"mandatory .*halt|authorized .*technician|halt procedure|certified technician", text, re.I))
                steps.append({
                    "number": len(steps) + 1,
                    "text": text,
                    "is_stop_step": is_stop,
                    "requires_technician": is_stop,
                    "hazard_notice": "Authorized technician required for hazardous invasive checks" if is_stop else "",
                    "source": f"Manual / {passage.get('id', passage.get('procedure_id', 'REF'))}",
                    "doc_type": passage.get("doc_type", "product_manual"),
                })
                continue
        if match:
            text = match.group(2).replace("**", "")
            is_stop = bool(re.search(r"mandatory safety halt|authorized .*technician|halt procedure|certified technician", text, re.I))
            steps.append({
                "number": len(steps) + 1,
                "text": text,
                "is_stop_step": is_stop,
                "requires_technician": is_stop,
                "hazard_notice": "Authorized technician required for hazardous invasive checks" if is_stop else "",
                "source": f"Manual / {passage.get('id', passage.get('procedure_id', 'REF'))}",
                "doc_type": passage.get("doc_type", "product_manual"),
            })
    return steps


def get_service_bulletin(bulletin_id: str) -> dict[str, Any]:
    """Look up a specific manufacturer service bulletin."""
    from src.config import SERVICE_BULLETINS_PATH
    if SERVICE_BULLETINS_PATH.exists():
        data = json.loads(SERVICE_BULLETINS_PATH.read_text(encoding="utf-8"))
        for item in data:
            if item["id"].strip().upper() == bulletin_id.strip().upper():
                return {"found": True, "bulletin": item}
    return {"found": False, "message": f"Service bulletin '{bulletin_id}' not found."}


def get_escalation_rule(rule_id: str) -> dict[str, Any]:
    """Look up an approved escalation rule and regulatory policy."""
    from src.config import ESCALATION_RULES_PATH
    if ESCALATION_RULES_PATH.exists():
        data = json.loads(ESCALATION_RULES_PATH.read_text(encoding="utf-8"))
        for item in data:
            if item["id"].strip().upper() == rule_id.strip().upper():
                return {"found": True, "rule": item}
    return {"found": False, "message": f"Escalation rule '{rule_id}' not found."}
