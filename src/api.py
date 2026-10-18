import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import settings
from src.tools import lookup_error_code, _load_error_codes_db
from src.agents import (
    DiagnosticCoordinator,
    ResolutionReviewAgent,
    get_or_create_session,
    SESSION_STORAGE,
    SessionState,
    EvidenceStep,
    SUPPORTED_MODELS,
    normalize_model_id
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Product Manual Troubleshooting Assistant - Appliance Field Service Operations"
)

# Enable CORS for industrial dashboards and local tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Request & Response Schemas
# ============================================================================

class DiagnoseRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Diagnostic session identifier. Auto-generated if omitted.")
    message: str = Field(..., description="Operator observation, symptom statement, or error code.")
    model_id: Optional[str] = Field(default=None, description="Appliance model identifier (e.g. BOSCH_SHEM78, WHIRLPOOL_WASHER_ALPHA, LG_REFRIG_LFXS, BREVILLE_BES920)")
    firmware_version: Optional[str] = Field(default=None, description="Board revision or firmware version (e.g. Rev C, Rev B3)")
    operating_environment: Optional[str] = Field(default=None, description="Operating environment (e.g. Residential Kitchen, Commercial Cafe)")
    error_code: Optional[str] = Field(default=None, description="Appliance error code (e.g. E15, F06 E01, BLNK-5, Er01)")


class DiagnoseResponse(BaseModel):
    session_id: str
    model_id: Optional[str] = None
    status: str
    response_type: str
    message: str
    confidence: int
    timeline: list[dict[str, Any]]
    escalation_record: Optional[dict[str, Any]] = None


class TimelineResponse(BaseModel):
    session_id: str
    total_steps: int
    resolution_confidence: int
    diagnostic_status: str
    timeline: list[EvidenceStep]


class EscalateResponse(BaseModel):
    session_id: str
    incident_id: str
    escalation_package: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    timestamp: str
    supported_hardware: list[str]


class SupportedModelsResponse(BaseModel):
    total: int
    models: list[dict[str, Any]]


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System Health"])
def health_check() -> HealthResponse:
    """
    Operational readiness ping.
    """
    return HealthResponse(
        status="OPERATIONAL",
        app=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        supported_hardware=settings.supported_hardware
    )


@app.get("/api/models", response_model=SupportedModelsResponse, tags=["Appliance Platforms"])
def get_supported_models() -> SupportedModelsResponse:
    """
    Returns list of the 4 supported appliance platforms.
    """
    model_list = [
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
    return SupportedModelsResponse(
        total=len(model_list),
        models=model_list
    )


@app.post("/api/diagnose", response_model=DiagnoseResponse, tags=["Diagnostics"])
def diagnose(payload: DiagnoseRequest) -> DiagnoseResponse:
    """
    Primary session diagnostic progression loop.
    Manages session state, agent reasoning, safe-step planning, and evidence logging.
    """
    session_id = payload.session_id or f"sess-{uuid.uuid4().hex[:8]}"
    session = get_or_create_session(session_id)

    # Pre-populate session state if explicit parameters are provided in request
    if payload.model_id:
        norm_m = normalize_model_id(payload.model_id)
        if norm_m:
            session.model_id = norm_m
    if payload.firmware_version:
        session.firmware_version = payload.firmware_version
    if payload.operating_environment:
        session.operating_environment = payload.operating_environment
    if payload.error_code:
        session.error_code = payload.error_code

    try:
        result = DiagnosticCoordinator.process_turn(
            session_id=session_id,
            user_input=payload.message
        )
        return DiagnoseResponse(
            session_id=result["session_id"],
            model_id=result.get("model_id"),
            status=result["status"],
            response_type=result["response_type"],
            message=result["message"],
            confidence=result["confidence"],
            timeline=result["timeline"],
            escalation_record=result.get("escalation_record")
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagnostic execution failure: {str(exc)}"
        )


@app.get("/api/timeline/{session_id}", response_model=TimelineResponse, tags=["Telemetry & Audit"])
def get_timeline(session_id: str) -> TimelineResponse:
    """
    Retrieves chronological evidence history for a given diagnostic session.
    """
    if session_id not in SESSION_STORAGE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic session '{session_id}' not found."
        )

    session = SESSION_STORAGE[session_id]
    return TimelineResponse(
        session_id=session.session_id,
        total_steps=len(session.timeline),
        resolution_confidence=session.resolution_confidence,
        diagnostic_status=session.diagnostic_status,
        timeline=session.timeline
    )


@app.post("/api/escalate/{session_id}", response_model=EscalateResponse, tags=["Escalations"])
def escalate_session(session_id: str) -> EscalateResponse:
    """
    Compiles formal escalation JSON payload for field technicians.
    """
    if session_id not in SESSION_STORAGE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic session '{session_id}' not found."
        )

    session = SESSION_STORAGE[session_id]
    session.diagnostic_status = "ESCALATED"
    escalation_package = ResolutionReviewAgent.generate_escalation_package(
        session=session,
        reason="Manual operator escalation requested via API."
    )

    return EscalateResponse(
        session_id=session.session_id,
        incident_id=escalation_package["incident_id"],
        escalation_package=escalation_package
    )


@app.get("/api/codes", tags=["Diagnostics Data"])
def list_codes(model: Optional[str] = None) -> dict[str, Any]:
    """
    Returns structured list of available error codes in the appliance database.
    """
    try:
        db = _load_error_codes_db()
        if model:
            norm_m = normalize_model_id(model)
            filtered = {k: v for k, v in db.items() if (norm_m and v.get("model_id") == norm_m) or (model.lower() in v.get("model_id", "").lower())}
            return {"total": len(filtered), "codes": filtered}
        return {"total": len(db), "codes": db}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/codes/{code}", tags=["Diagnostics Data"])
def get_code_metadata(code: str) -> dict[str, Any]:
    """
    Retrieves full metadata for a specific error code.
    """
    result = lookup_error_code(code)
    if result.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail=result.get("error_message"))
    return result


@app.get("/api/evaluate", tags=["Evaluation & Benchmarking"])
def run_benchmark_endpoint() -> dict[str, Any]:
    """
    Executes automated 4-dimension quality evaluation benchmark suite (Hit Rate, Entity Extraction, Tools, Safety Invariants).
    """
    from src.evaluation import run_evaluation
    return run_evaluation()


@app.get("/api/status", tags=["System Status"])
def get_system_status() -> dict[str, Any]:
    """
    Returns comprehensive system status, indexed document tiers, and active search mode.
    """
    from src.service import system_status
    return system_status()


@app.get("/api/documents", tags=["Diagnostics Data"])
def get_document_catalog() -> dict[str, Any]:
    """
    Returns indexed document catalog categorized by authority tier with 3-factor weights.
    """
    from src.rag import get_knowledge_base
    kb = get_knowledge_base()
    return {
        "total": len(kb.raw_chunks),
        "documents": [
            {
                "id": c["id"],
                "title": c["title"],
                "doc_type": c.get("doc_type", "product_manual"),
                "product": c["product"],
                "authority_score": c.get("authority_score", 0.60),
                "disruption_level": c.get("disruption_level", "Standard"),
                "needs_technician": c.get("needs_technician", False),
            }
            for c in kb.raw_chunks
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
