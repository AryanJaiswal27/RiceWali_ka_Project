"""
service.py  -  Diagnostic Service Orchestration & Case Management Layer

Coordinates multi-tier RAG retrieval, structured entity extraction, session memory,
ordered safe checks, anti-looping prevention, and field handover dossiers.
Exposed to FastAPI REST endpoints, Streamlit operator console, and evaluation benchmark.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from src.config import settings
from src.extractor import extract_diagnostic_entities
from src.llm import ask_llm, llm_available, run_agent
from src.rag import get_knowledge_base
from src.tools import (
    get_troubleshooting_checklist,
    list_error_codes,
    list_products,
    lookup_error_code,
    search_manual,
    steps_from_manual_passage,
)


class CaseError(Exception):
    """Business logic and validation exceptions."""


@dataclass
class DiagnosticSession:
    session_id: str
    product: str
    symptom: str
    error_code: Optional[str] = None
    software_version: str = "UNKNOWN"
    operating_conditions: dict = field(default_factory=dict)
    extracted_entities: dict = field(default_factory=dict)
    severity: str = "STANDARD"
    safety_boundary: str = ""
    technician_work_required: Optional[str] = None
    steps: list = field(default_factory=list)
    current_index: int = 0
    timeline: list = field(default_factory=list)
    attempted_action_texts: list = field(default_factory=list)
    retrieved_documents: list = field(default_factory=list)
    status: str = "IN_PROGRESS"  # IN_PROGRESS | RESOLVED | ESCALATED
    introduction: str = ""
    warnings: list = field(default_factory=list)
    tool_log: list = field(default_factory=list)
    record: Optional[dict] = None
    llm_used: bool = False


SESSIONS: dict[str, DiagnosticSession] = {}


def new_session_id() -> str:
    return "CASE-" + uuid.uuid4().hex[:8].upper()


def get_session(session_id: str) -> Optional[DiagnosticSession]:
    return SESSIONS.get(session_id)


def current_step(session: DiagnosticSession) -> Optional[dict]:
    if session.status != "IN_PROGRESS" or session.current_index >= len(session.steps):
        return None
    return session.steps[session.current_index]


def session_to_dict(session: DiagnosticSession) -> dict:
    data = asdict(session)
    data["current_step"] = current_step(session)
    data["total_steps"] = len(session.steps)
    data["attempted_count"] = len(session.timeline)
    return data


# ============================================================================
# Service Layer Agents: Retrieval, Ordering, Review & Safety Halts
# ============================================================================

class ServiceRetrievalAgent:
    """Extracts entities, executes 3-factor re-ranking RAG, and builds safe ordered checks."""

    @staticmethod
    def run(session: DiagnosticSession) -> None:
        extracted = extract_diagnostic_entities(
            raw_text=session.symptom,
            explicit_code=session.error_code,
            explicit_product=session.product,
            supported_products=list_products(),
        )
        session.extracted_entities = extracted.to_dict()
        if extracted.software_version != "UNKNOWN":
            session.software_version = extracted.software_version
        if extracted.operating_conditions:
            session.operating_conditions.update(extracted.operating_conditions)
        if not session.error_code and extracted.error_code:
            session.error_code = extracted.error_code

        # Assemble steps deterministically
        steps, sources_note = ServiceRetrievalAgent._build_steps(session)
        session.steps = steps

        # Template or LLM intro
        session.introduction = ServiceRetrievalAgent._build_intro(session, sources_note)

    @staticmethod
    def _build_steps(session: DiagnosticSession) -> tuple[list[dict], str]:
        # Path 1: Official Error Code
        if session.error_code:
            info = lookup_error_code(session.error_code)
            if info.get("found"):
                # Check for product match
                info_prod = info.get("product") or info.get("model")
                if info_prod and session.product and info_prod != session.product and session.product != "General Household Appliance":
                    session.warnings.append(
                        f"Code '{info['code']}' belongs to {info_prod}, not {session.product}. Proceeding with multi-tier symptom search."
                    )
                else:
                    checklist = get_troubleshooting_checklist(info["code"])
                    session.severity = info["severity"]
                    session.safety_boundary = info.get("safety_boundary", info.get("technician_authorization_boundary", ""))
                    session.error_code = info["code"]
                    rag_result = search_manual(session.symptom, session.product, session.software_version)
                    session.retrieved_documents = rag_result.get("results", [])
                    return checklist["steps"], f"Official Error Code {info['code']} ({info.get('symptom', '')[:60]})"

        # Path 2: Multi-Criteria 3-Factor Re-Ranking
        rag_data = search_manual(
            query=f"{session.symptom} {session.error_code or ''}",
            product=session.product,
            software_version=session.software_version,
        )
        session.retrieved_documents = rag_data.get("results", [])

        assembled_steps: list[dict] = []
        seen_texts: set[str] = set()

        for hit in session.retrieved_documents:
            passage_steps = steps_from_manual_passage(hit)
            for st in passage_steps:
                norm_text = st["text"].strip().lower()
                if norm_text not in seen_texts:
                    seen_texts.add(norm_text)
                    st["number"] = len(assembled_steps) + 1
                    assembled_steps.append(st)

        # Safety ordering: Non-invasive first, invasive/technician stops at the end
        safe_steps = [s for s in assembled_steps if not s.get("is_stop_step")]
        stop_steps = [s for s in assembled_steps if s.get("is_stop_step")]
        final_steps = safe_steps + stop_steps
        for idx, s in enumerate(final_steps, start=1):
            s["number"] = idx

        top_ref = session.retrieved_documents[0]["title"] if session.retrieved_documents else "Technical Manual"
        return final_steps, f"Multi-Tier Re-Ranked Source: {top_ref}"

    @staticmethod
    def _build_intro(session: DiagnosticSession, sources_note: str) -> str:
        text = f"Welcome. We are analyzing your **{session.product}**."
        if session.error_code:
            text += f" Diagnostic Code: `{session.error_code}`."
        text += f" Matched against **{sources_note}** using 3-factor composite re-ranking. We will guide you through sequential safe checks one step at a time."
        if any(s.get("is_stop_step") for s in session.steps):
            text += " For your safety, hazardous internal procedures will automatically halt and dispatch a certified technician."
        return text


class ServiceReviewAgent:
    """Tracks attempted actions, prevents looping, advances steps, and issues handover packages."""

    @staticmethod
    def review(session: DiagnosticSession, outcome: str, note: str = "") -> None:
        step = current_step(session)
        if step is None:
            return

        action_text = step["text"].strip()
        record_entry = {
            "step_number": step["number"],
            "action": action_text,
            "source": step.get("source", "Standard Manual"),
            "doc_type": step.get("doc_type", "product_manual"),
            "outcome": outcome,
            "observed_result": note.strip() or ("Problem fixed by this action." if outcome == "fixed" else "Symptom persists; check unverified."),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        session.timeline.append(record_entry)
        session.attempted_action_texts.append(action_text.lower())

        if outcome == "fixed":
            session.status = "RESOLVED"
            ServiceReviewAgent._finish(session, reason="Issue successfully resolved by customer verification.")
            return

        # Advance step with anti-looping de-duplication
        session.current_index += 1
        while session.current_index < len(session.steps):
            next_text = session.steps[session.current_index]["text"].strip().lower()
            if next_text in session.attempted_action_texts:
                session.current_index += 1
            else:
                break

        if session.current_index >= len(session.steps):
            ServiceReviewAgent.escalate(
                session,
                "All approved safe checks were attempted without resolution. Authorized technician required."
            )
        elif session.steps[session.current_index].get("is_stop_step"):
            stop_step = session.steps[session.current_index]
            session.technician_work_required = stop_step["text"]
            ServiceReviewAgent.escalate(
                session,
                f"Safety boundary reached: Next required procedure ({stop_step['text'][:60]}...) requires an authorized certified technician."
            )

    @staticmethod
    def escalate(session: DiagnosticSession, reason: str) -> None:
        session.status = "ESCALATED"
        ServiceReviewAgent._finish(session, reason=reason)

    @staticmethod
    def _finish(session: DiagnosticSession, reason: str) -> None:
        stop_steps = [s for s in session.steps if s.get("is_stop_step")]
        technician_work = session.technician_work_required or (stop_steps[0]["text"] if stop_steps else None)

        record = {
            "ticket_id": f"ESC-{session.session_id}",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "disposition": session.status,
            "reason": reason,
            "device_profile": {
                "product": session.product,
                "software_version": session.software_version,
                "operating_conditions": session.operating_conditions,
                "error_code": session.error_code or "None",
            },
            "symptoms_reported": session.extracted_entities.get("symptoms", [session.symptom]),
            "severity_rating": session.severity,
            "attempted_steps_history": session.timeline,
            "total_attempts": len(session.timeline),
            "safety_boundary": session.safety_boundary or "Standard appliance operational safety limits apply.",
            "technician_work_required": technician_work,
            "recommended_next_action": (
                "Case closed. Maintain regular preventive maintenance schedule."
                if session.status == "RESOLVED"
                else (
                    f"Dispatch Certified Field Technician. Review customer diagnostic history ({len(session.timeline)} steps tried). "
                    f"Required action: {technician_work or 'Inspect and test subsystem with CAT-III / calibrated gauges.'}"
                )
            ),
            "document_sources": sorted(
                {t["source"] for t in session.timeline if "source" in t} | {s["source"] for s in stop_steps if "source" in s}
            ),
        }

        # Build Field Handover Markdown Ticket
        dp = record["device_profile"]
        lines = [
            f"# 🛡️ Field Service Escalation Handover Ticket // `{record['ticket_id']}`",
            f"**Generated:** {record['created_at']}  •  **Disposition:** `{record['disposition']}`  •  **Severity:** `{record['severity_rating']}`",
            "",
            "## 1. Equipment Profile",
            f"- **Product Model:** {dp['product']}",
            f"- **Firmware / Revision:** {dp['software_version']}",
            f"- **Error Code:** `{dp['error_code']}`",
            f"- **Reported Symptoms:** {', '.join(record['symptoms_reported'])}",
            "",
            "## 2. Escalation Justification & Safety Interlock",
            f"> **Reason for Escalation:** {record['reason']}",
            f"> **Regulatory Safety Boundary:** {record['safety_boundary']}",
            "",
            "## 3. Customer Attempted Action Chronology (Diagnostic Memory)",
        ]
        if not record["attempted_steps_history"]:
            lines.append("*(Immediate safety stop triggered prior to invasive customer checks)*")
        else:
            for item in record["attempted_steps_history"]:
                lines.append(f"- **Step {item['step_number']}:** {item['action']}")
                lines.append(f"  - *Outcome:* `{item['outcome'].upper()}` — {item['observed_result']} *(Source: {item['source']})*")

        lines.extend([
            "",
            "## 4. Mandated Technician Directive",
            f"**Required Procedure:** {record['technician_work_required'] or 'Perform comprehensive subsystem diagnostic.'}",
            f"**Recommended Action:** {record['recommended_next_action']}",
            "",
            "## 5. Document Citations & Audit Trail",
        ])
        for src in record["document_sources"]:
            lines.append(f"- `{src}`")

        record["ticket_markdown"] = "\n".join(lines)
        record["summary"] = f"Appliance: {session.product}. Result: {session.status}. Steps attempted: {len(session.timeline)}. Safety halt verified."
        session.record = record


# ============================================================================
# Public API Functions
# ============================================================================

def start_case(
    product: str,
    symptom: str,
    error_code: Optional[str] = None,
    software_version: Optional[str] = None,
    operating_conditions: Optional[dict] = None,
) -> dict:
    """Initialize a troubleshooting case, extract entities, retrieve documents, and build initial steps."""
    if product not in list_products() and product != "General Household Appliance":
        # Check if product is in supported hardware
        if product not in settings.supported_hardware:
            raise CaseError(f"Unknown product '{product}'. Please select from supported models.")

    if not symptom or not symptom.strip():
        raise CaseError("Please provide an error code or natural-language problem description.")

    session = DiagnosticSession(
        session_id=new_session_id(),
        product=product,
        symptom=symptom.strip(),
        error_code=(error_code or "").strip().upper() or None,
        software_version=(software_version or "UNKNOWN").strip(),
        operating_conditions=operating_conditions or {},
    )
    SESSIONS[session.session_id] = session

    # Run Retrieval & Re-Ranking
    ServiceRetrievalAgent.run(session)

    # Initial safety gates
    if not session.steps:
        ServiceReviewAgent.escalate(
            session,
            "No approved technical procedures or service bulletins matched this symptom.",
        )
    elif session.steps[0].get("is_stop_step"):
        ServiceReviewAgent.escalate(
            session,
            "Immediate safety stop: The initial isolation procedure requires an authorized certified technician.",
        )

    return session_to_dict(session)


def report_result(session_id: str, outcome: str, note: str = "") -> dict:
    """Record customer observation for current step, prevent loops, and determine next step."""
    session = get_session(session_id)
    if session is None:
        raise CaseError(f"Case '{session_id}' not found. It may have expired or the server restarted.")
    if outcome not in ("fixed", "not_fixed"):
        raise CaseError("Outcome must be either 'fixed' or 'not_fixed'.")

    ServiceReviewAgent.review(session, outcome, note)
    return session_to_dict(session)


def escalate_case(session_id: str) -> dict:
    """Manual customer request to immediately halt and escalate to an authorized technician."""
    session = get_session(session_id)
    if session is None:
        raise CaseError(f"Case '{session_id}' not found.")
    if session.status == "IN_PROGRESS":
        ServiceReviewAgent.escalate(session, "Customer requested immediate escalation to a certified technician.")
    return session_to_dict(session)


def get_case(session_id: str) -> dict:
    session = get_session(session_id)
    if session is None:
        raise CaseError(f"Case '{session_id}' not found.")
    return session_to_dict(session)


def extract_entities(text: str, explicit_product: Optional[str] = None) -> dict:
    return extract_diagnostic_entities(
        raw_text=text,
        explicit_product=explicit_product,
        supported_products=list_products(),
    ).to_dict()


def system_status() -> dict:
    kb = get_knowledge_base()
    tier_counts: dict[str, int] = {}
    for c in kb.raw_chunks:
        dt = c.get("doc_type", "manual")
        tier_counts[dt] = tier_counts.get(dt, 0) + 1

    return {
        "status": "operational",
        "llm_mode": "TCS GenAI Lab MaaS Online" if llm_available() else "Deterministic Standalone (No API Key)",
        "search_mode": "ChromaDB Vector Store (Cosine Embeddings)" if kb.mode == "vector" else "Keyword / Multi-Criteria Re-Ranker",
        "total_documents_indexed": len(kb.raw_chunks),
        "document_tiers": tier_counts,
        "products": list_products(),
    }
