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
    EvidenceStep
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise Network Gateway Diagnostic Assistant - Corporate IT Field Operations Standard"
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
    message: str = Field(..., description="Operator observation, symptom statement, or telemetry snippet.")
    model_id: Optional[str] = Field(default=None, description="Hardware model identifier (e.g. Apex Router Pro-X)")
    firmware_version: Optional[str] = Field(default=None, description="Firmware version (e.g. v4.2.0)")
    operating_environment: Optional[str] = Field(default=None, description="Operating environment (e.g. Datacenter Rack 4)")
    error_code: Optional[str] = Field(default=None, description="Hardware error code (e.g. ERR-ARPX-101)")


class DiagnoseResponse(BaseModel):
    session_id: str
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


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System Health"])
def health_check() -> HealthResponse:
    """
    Standard enterprise health and readiness check.
    """
    return HealthResponse(
        status="OPERATIONAL",
        app=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        supported_hardware=settings.supported_hardware
    )


@app.post("/api/diagnose", response_model=DiagnoseResponse, tags=["Diagnostics"])
def diagnose(payload: DiagnoseRequest) -> DiagnoseResponse:
    """
    Main conversational and procedural diagnostic loop.
    Manages session state, agent reasoning, safe-step planning, and evidence logging.
    """
    session_id = payload.session_id or f"sess-{uuid.uuid4().hex[:8]}"
    session = get_or_create_session(session_id)

    # Pre-populate session state if explicit parameters are provided in request
    if payload.model_id:
        session.model_id = payload.model_id
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
    Returns the complete chronological evidence audit log for a given diagnostic session.
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
    Forces generation and compilation of the formal incident escalation record.
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
    Returns structured list of available error codes in the corporate database.
    """
    try:
        db = _load_error_codes_db()
        if model:
            filtered = {k: v for k, v in db.items() if model.lower() in v.get("model", "").lower()}
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
