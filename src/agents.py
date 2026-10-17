import os
import re
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

from src.config import (
    settings,
    MANUALS_PATH,
    VECTOR_STORE_DIR
)
from src.tools import lookup_error_code, get_component_checklist

logger = logging.getLogger("IndustrialDiagnostics.Agents")

# ============================================================================
# Pydantic Schemas for Memory & Evidence Timeline
# ============================================================================

class EvidenceStep(BaseModel):
    step_index: int
    action_executed: str
    source_doc_reference: str
    user_reported_observation: str = "Pending technician observation"
    verification_status: str = "PENDING"  # PENDING, VERIFIED_NORMAL, VERIFIED_ABNORMAL, BLOCKED
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SessionState(BaseModel):
    session_id: str
    model_id: Optional[str] = None
    firmware_version: Optional[str] = None
    operating_environment: Optional[str] = None
    error_code: Optional[str] = None
    symptom_summary: Optional[str] = None
    current_step_index: int = 0
    planned_steps: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[EvidenceStep] = Field(default_factory=list)
    resolution_confidence: int = 0  # 0 to 100%
    diagnostic_status: str = "INITIALIZING"  # INITIALIZING, PARAM_CLARIFICATION, IN_PROGRESS, RESOLVED, MANDATORY_HALT_TECHNICIAN_REQUIRED, ESCALATED
    halt_reason: Optional[str] = None
    escalation_record: Optional[dict[str, Any]] = None
    last_prompt_to_user: Optional[str] = None


# In-memory session repository
SESSION_STORAGE: dict[str, SessionState] = {}


def get_or_create_session(session_id: str) -> SessionState:
    if session_id not in SESSION_STORAGE:
        SESSION_STORAGE[session_id] = SessionState(session_id=session_id)
    return SESSION_STORAGE[session_id]


# ============================================================================
# Remote MaaS OpenAI-Compatible Embeddings Client
# ============================================================================

def get_remote_openai_embeddings(texts: list[str]) -> Optional[list[list[float]]]:
    """
    Attempts to generate embeddings via the TCS GenAI Lab OpenAI-compatible gateway.
    Uses EMBEDDING_MODEL_NAME ("azure/genailab-maas-text-embedding-3-large").
    If the call fails or no API key is set, returns None to trigger local fallback.
    """
    if not settings.maas_api_key or not settings.maas_api_base_url:
        return None

    # Strategy 1: LangChain OpenAIEmbeddings
    try:
        from langchain_openai import OpenAIEmbeddings
        embedder = OpenAIEmbeddings(
            model=settings.embedding_model_name,
            openai_api_base=settings.maas_api_base_url,
            openai_api_key=settings.maas_api_key,
            check_embedding_ctx_length=False
        )
        return embedder.embed_documents(texts)
    except Exception:
        pass

    # Strategy 2: Direct REST POST to /embeddings via httpx
    try:
        import httpx
        url = f"{settings.maas_api_base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.maas_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.embedding_model_name,
            "input": texts
        }
        with httpx.Client(timeout=12.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                body = resp.json()
                if "data" in body and isinstance(body["data"], list):
                    return [item["embedding"] for item in body["data"]]
    except Exception as exc:
        logger.warning(f"Remote MaaS embedding unavailable ({str(exc)}). Activating local fallback.")

    return None


def get_remote_query_embedding(text: str) -> Optional[list[float]]:
    res = get_remote_openai_embeddings([text])
    if res and len(res) > 0:
        return res[0]
    return None


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes standard cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


# ============================================================================
# Ingestion & Vector Retrieval Engine
# ============================================================================

class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    model_target: str  # "Apex Router Pro-X", "CoreSwitch 4000", or "COMMON"
    section_name: str
    source_ref: str


class VectorRetrievalEngine:
    """
    Ingests industrial_manuals.md using chunking and builds a searchable
    knowledge index.
    
    1. Tries initializing OpenAIEmbeddings with EMBEDDING_MODEL_NAME ("azure/genailab-maas-text-embedding-3-large"),
       MAAS_API_BASE_URL ("https://genailab.tcs.in/v1"), and MAAS_API_KEY.
    2. If remote embedding fails or MAAS_API_KEY is not set, seamlessly falls back
       to local offline embeddings engine without raising an unhandled exception.
    """
    def __init__(self):
        self.chunks: list[DocumentChunk] = []
        self.chunk_embeddings: list[list[float]] = []
        self.is_remote_embeddings_ready: bool = False
        self.is_chroma_ready: bool = False
        self.chroma_collection = None
        self._initialize_knowledge_base()

    def _split_manual(self, raw_text: str) -> list[DocumentChunk]:
        """
        Parses industrial manuals markdown by structural headers to preserve
        procedure boundaries and model targets.
        """
        chunks: list[DocumentChunk] = []
        sections = raw_text.split("\n## ")
        
        chunk_counter = 1
        for sec in sections:
            if not sec.strip():
                continue
            lines = sec.strip().split("\n")
            header = lines[0].replace("#", "").strip()
            body = "\n".join(lines[1:]).strip()

            header_lower = header.lower()
            if "apex router" in header_lower or "arpx" in header_lower:
                model_target = "Apex Router Pro-X"
            elif "coreswitch" in header_lower or "cs4k" in header_lower:
                model_target = "CoreSwitch 4000"
            else:
                model_target = "COMMON"

            subsections = re.split(r'\n###+ ', body)
            for sub in subsections:
                if not sub.strip():
                    continue
                sub_lines = sub.strip().split("\n")
                sub_header = sub_lines[0].replace("#", "").strip()
                sub_body = "\n".join(sub_lines[1:]).strip()

                full_text = f"SECTION: {header} > {sub_header}\nTARGET: {model_target}\n\n{sub_body}"
                
                proc_match = re.search(r'Procedure\s+([A-Z0-9\-]+)', sub_header, re.IGNORECASE)
                proc_ref = proc_match.group(1) if proc_match else f"SEC-{chunk_counter}"

                chunks.append(DocumentChunk(
                    chunk_id=f"chunk_{chunk_counter}",
                    content=full_text,
                    model_target=model_target,
                    section_name=f"{header} > {sub_header}",
                    source_ref=f"ESM-NET-2026-V4 / {proc_ref}"
                ))
                chunk_counter += 1

        return chunks

    def _initialize_knowledge_base(self):
        try:
            if not MANUALS_PATH.exists():
                logger.error(f"Manuals file missing at {MANUALS_PATH}")
                return

            with open(MANUALS_PATH, "r", encoding="utf-8") as f:
                raw_text = f.read()

            self.chunks = self._split_manual(raw_text)
            logger.info(f"Ingested {len(self.chunks)} structured chunks from {MANUALS_PATH.name}")

            # 1. Attempt Remote OpenAIEmbeddings Initialization
            try:
                if settings.maas_api_key:
                    chunk_texts = [c.content for c in self.chunks]
                    remote_vectors = get_remote_openai_embeddings(chunk_texts)
                    if remote_vectors and len(remote_vectors) == len(self.chunks):
                        self.chunk_embeddings = remote_vectors
                        self.is_remote_embeddings_ready = True
                        logger.info(f"Successfully indexed document chunks using remote OpenAIEmbeddings ({settings.embedding_model_name}).")
            except Exception as rem_err:
                logger.warning(f"Remote embedding initialization failed ({str(rem_err)}). Utilizing local offline engine.")
                self.is_remote_embeddings_ready = False

            # 2. Optional ChromaDB / SentenceTransformer initialization
            if not self.is_remote_embeddings_ready:
                try:
                    import chromadb
                    from sentence_transformers import SentenceTransformer

                    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
                    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
                    self.local_embedder = SentenceTransformer(settings.local_fallback_embedding_model)
                    
                    collection = client.get_or_create_collection(name="industrial_manuals")
                    
                    if collection.count() == 0:
                        ids = [c.chunk_id for c in self.chunks]
                        texts = [c.content for c in self.chunks]
                        metadatas = [{"model_target": c.model_target, "section": c.section_name, "source_ref": c.source_ref} for c in self.chunks]
                        embeddings = self.local_embedder.encode(texts).tolist()
                        collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
                    
                    self.chroma_collection = collection
                    self.is_chroma_ready = True
                    logger.info("ChromaDB vector store initialized successfully with SentenceTransformers.")
                except Exception as chroma_err:
                    logger.warning(f"ChromaDB / SentenceTransformer unavailable ({str(chroma_err)}). Utilizing deterministic fallback vector search engine.")
                    self.is_chroma_ready = False

        except Exception as e:
            logger.error(f"Failed to initialize vector retrieval engine: {str(e)}", exc_info=True)

    def search(self, query: str, model_filter: Optional[str] = None, top_k: int = 3) -> list[DocumentChunk]:
        """
        Executes vector search with strict model compatibility filtering.
        Prioritizes remote embeddings if ready, followed by ChromaDB, followed by deterministic fallback.
        """
        if not self.chunks:
            return []

        # Path A: Remote OpenAIEmbeddings vector search
        if self.is_remote_embeddings_ready and self.chunk_embeddings:
            try:
                query_vec = get_remote_query_embedding(query)
                if query_vec:
                    scored: list[tuple[float, DocumentChunk]] = []
                    for idx, chunk in enumerate(self.chunks):
                        if model_filter and model_filter != "COMMON":
                            if chunk.model_target != "COMMON" and chunk.model_target.lower() != model_filter.lower():
                                continue
                        sim = cosine_similarity(query_vec, self.chunk_embeddings[idx])
                        scored.append((sim, chunk))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    return [c for _, c in scored[:top_k]]
            except Exception as e:
                logger.warning(f"Remote vector search query failed: {str(e)}. Proceeding to local fallback.")

        # Path B: ChromaDB with SentenceTransformers
        if self.is_chroma_ready and self.chroma_collection is not None:
            try:
                query_embedding = self.local_embedder.encode([query]).tolist()
                where_filter = None
                if model_filter and model_filter != "COMMON":
                    where_filter = {"$or": [{"model_target": model_filter}, {"model_target": "COMMON"}]}
                
                results = self.chroma_collection.query(
                    query_embeddings=query_embedding,
                    n_results=min(top_k * 2, len(self.chunks)),
                    where=where_filter
                )
                
                matched_chunks: list[DocumentChunk] = []
                if results and "ids" in results and results["ids"]:
                    returned_ids = results["ids"][0]
                    id_map = {c.chunk_id: c for c in self.chunks}
                    for cid in returned_ids:
                        if cid in id_map:
                            matched_chunks.append(id_map[cid])
                
                if matched_chunks:
                    return matched_chunks[:top_k]
            except Exception as search_err:
                logger.warning(f"ChromaDB query failed: {search_err}. Resorting to fallback search.")

        # Path C: Deterministic Word-Overlap & Semantic TF Scoring Fallback
        query_terms = set(re.findall(r'\w+', query.lower()))
        scored_chunks: list[tuple[float, DocumentChunk]] = []

        for chunk in self.chunks:
            # Compatibility Filter Check
            if model_filter and model_filter != "COMMON":
                if chunk.model_target != "COMMON" and chunk.model_target.lower() != model_filter.lower():
                    continue

            content_lower = chunk.content.lower()
            score = 0.0
            for term in query_terms:
                if len(term) < 3:
                    continue
                count = content_lower.count(term)
                if count > 0:
                    score += 1.0 + min(count * 0.5, 4.0)
                    if term in chunk.section_name.lower():
                        score += 3.0

            if score > 0:
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored_chunks[:top_k]]


# Global Vector Engine Instance
retrieval_engine = VectorRetrievalEngine()


# ============================================================================
# MaaS / OpenAI-Compatible REST Client
# ============================================================================

def call_maas_llm(system_prompt: str, user_prompt: str) -> Optional[str]:
    """
    Communicates with OpenAI-compatible Model-as-a-Service endpoint.
    Explicitly uses settings.model_name ("azure/genailab-maas-gpt-4o-mini").
    If no API key or unreachable, returns None to trigger deterministic fallback.
    """
    if not settings.maas_api_key or not settings.maas_api_base_url:
        return None

    # Strategy 1: LangChain ChatOpenAI if available
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = ChatOpenAI(
            model=settings.model_name,
            openai_api_base=settings.maas_api_base_url,
            openai_api_key=settings.maas_api_key,
            temperature=0.1,
            max_tokens=1024,
            timeout=10.0
        )
        resp = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        return resp.content.strip()
    except Exception:
        pass

    # Strategy 2: Direct REST POST to /chat/completions via httpx
    try:
        import httpx
        headers = {
            "Authorization": f"Bearer {settings.maas_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1024
        }
        url = f"{settings.maas_api_base_url}/chat/completions"
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.warning(f"MaaS API responded with HTTP {resp.status_code}: {resp.text}")
                return None
    except Exception as e:
        logger.warning(f"MaaS API call bypass due to: {str(e)}")
        return None


# ============================================================================
# 1. Symptom Clarifier Agent
# ============================================================================

class SymptomClarifierAgent:
    """
    Inspects user inputs to verify whether:
    - Model ID ('Apex Router Pro-X' or 'CoreSwitch 4000')
    - Firmware Version (e.g. 'v4.2.0')
    - Operating Environment (e.g. 'Production Datacenter Cold Aisle')
    are fully established.
    If ambiguous or deficient, generates precise technical clarification queries.
    """
    @staticmethod
    def inspect_and_update(session: SessionState, user_input: str) -> tuple[bool, Optional[str]]:
        input_norm = user_input.lower()

        # 1. Model ID Extraction
        if not session.model_id:
            if "apex" in input_norm or "arpx" in input_norm or "router" in input_norm:
                session.model_id = "Apex Router Pro-X"
            elif "coreswitch" in input_norm or "cs4k" in input_norm or "switch" in input_norm or "4000" in input_norm:
                session.model_id = "CoreSwitch 4000"

        # 2. Error Code Extraction (matches ERR-XXX-XXX, OPT-XXX, etc.)
        code_match = re.search(r'\b(ERR-[A-Z0-9]+-\d+|OPT-\d+)\b', user_input, re.IGNORECASE)
        if code_match and not session.error_code:
            session.error_code = code_match.group(1).upper()

        # 3. Firmware Version Extraction
        if not session.firmware_version:
            fw_match = re.search(r'\b(v?\d+\.\d+(?:\.\d+)?)\b', user_input, re.IGNORECASE)
            if fw_match:
                fw_val = fw_match.group(1)
                session.firmware_version = fw_val if fw_val.startswith("v") else f"v{fw_val}"

        # 4. Operating Environment Extraction
        if not session.operating_environment:
            env_keywords = [
                "datacenter", "data center", "rack", "cold aisle", "hot aisle",
                "lab", "edge pop", "facility", "poe closet", "substation", "production"
            ]
            for ek in env_keywords:
                if ek in input_norm:
                    session.operating_environment = ek.title()
                    break

        # Check for Deficits
        missing: list[str] = []
        if not session.model_id:
            missing.append("HARDWARE MODEL ID (Supported: 'Apex Router Pro-X' or 'CoreSwitch 4000')")
        if not session.firmware_version:
            missing.append("FIRMWARE REVISION (e.g., 'v4.2.0' or 'v5.1.0')")
        if not session.operating_environment:
            missing.append("OPERATING ENVIRONMENT (e.g., 'Datacenter Rack Row 4', 'Edge POP', 'Lab Bench')")

        if missing:
            session.diagnostic_status = "PARAM_CLARIFICATION"
            clarification_notice = (
                "[PARAMETER DEFICIT - DIAGNOSTIC GATE HALT]\n"
                "System requires verified telemetry parameters to isolate hardware fault domain.\n"
                "Missing required parameters:\n" +
                "\n".join([f"  - {m}" for m in missing]) + "\n\n"
                "Provide the missing parameter values before procedural execution can commence."
            )
            session.last_prompt_to_user = clarification_notice
            return False, clarification_notice

        # All established
        if session.diagnostic_status in ("PARAM_CLARIFICATION", "INITIALIZING"):
            session.diagnostic_status = "IN_PROGRESS"
        return True, None


# ============================================================================
# 2. Compatibility Gate & Safe-Step Planner Agent
# ============================================================================

class SafeStepPlannerAgent:
    """
    Sequences approved diagnostic checks from least disruptive to advanced.
    Enforces strict model compatibility and implements a deterministic halt
    if a procedure crosses into 'Authorized Field Technician' boundaries.
    """
    @staticmethod
    def generate_plan(session: SessionState) -> list[dict[str, Any]]:
        plan: list[dict[str, Any]] = []

        # 1. If Error Code is available, query structured error code database
        error_metadata = {}
        if session.error_code:
            error_metadata = lookup_error_code(session.error_code)

        step_idx = 1

        # Check initial checks from error_codes.json
        if error_metadata.get("status") == "SUCCESS" and error_metadata.get("initial_isolation_checks"):
            for check in error_metadata["initial_isolation_checks"]:
                check_lower = check.lower()
                requires_tech = False
                is_halt_step = False
                
                if any(kw in check_lower for kw in [
                    "halt", "technician", "dispatch", "replace optical",
                    "reseat", "power cycle or restart chassis to prevent", "jtag", "tamper"
                ]):
                    requires_tech = True
                    is_halt_step = True

                plan.append({
                    "step_index": step_idx,
                    "action": check,
                    "disruption_level": "CRITICAL_INVASIVE" if requires_tech else "NON_DISRUPTIVE",
                    "requires_authorized_technician": requires_tech,
                    "is_halt_boundary": is_halt_step,
                    "source_ref": f"ERROR-DB / {error_metadata['code']}",
                    "boundary_directive": error_metadata.get("technician_authorization_boundary", "Standard boundary rules.")
                })
                step_idx += 1

        # If no error code or additional steps required, use component checklist
        if len(plan) < 3:
            comp_name = "general"
            symp = (session.symptom_summary or "").lower()
            if any(k in symp for k in ["optic", "wan", "fiber", "sfp", "signal"]):
                comp_name = "optical"
            elif any(k in symp for k in ["thermal", "fan", "cooling", "temp", "rpm"]):
                comp_name = "thermal"
            elif any(k in symp for k in ["power", "psu", "voltage", "feed", "breaker"]):
                comp_name = "power"
            elif any(k in symp for k in ["backplane", "crc", "fabric", "serdes"]):
                comp_name = "backplane"
            elif any(k in symp for k in ["buffer", "drop", "queue", "asic"]):
                comp_name = "buffer"
            elif any(k in symp for k in ["bgp", "route", "routing", "peer"]):
                comp_name = "routing"
            elif any(k in symp for k in ["poe", "inline", "wattage"]):
                comp_name = "poe"
            elif any(k in symp for k in ["nvram", "flash", "crypto", "tamper"]):
                comp_name = "nvram"

            checklist = get_component_checklist(comp_name, session.model_id or "Apex Router Pro-X")
            for item in checklist:
                if not any(item["action"] in p["action"] for p in plan):
                    plan.append({
                        "step_index": step_idx,
                        "action": item["action"],
                        "disruption_level": item["disruption_level"],
                        "requires_authorized_technician": item["requires_authorized_technician"],
                        "is_halt_boundary": item["requires_authorized_technician"],
                        "source_ref": item.get("reference_standard", "Corporate IT Standard v4"),
                        "boundary_directive": item["boundary_condition"]
                    })
                    step_idx += 1

        session.planned_steps = plan
        return plan

    @staticmethod
    def get_next_step(session: SessionState) -> Optional[dict[str, Any]]:
        """
        Returns the next executable diagnostic step while enforcing technician halts.
        """
        if not session.planned_steps:
            SafeStepPlannerAgent.generate_plan(session)

        current_idx = session.current_step_index
        if current_idx >= len(session.planned_steps):
            return None

        candidate_step = session.planned_steps[current_idx]
        
        # Enforce deterministic halt if step requires Authorized Field Technician
        if candidate_step.get("requires_authorized_technician") or candidate_step.get("is_halt_boundary"):
            session.diagnostic_status = "MANDATORY_HALT_TECHNICIAN_REQUIRED"
            session.halt_reason = (
                f"[MANDATORY SAFETY BOUNDARY INTERLOCK]\n"
                f"Step {candidate_step['step_index']} requires 'Authorized Field Technician' credential.\n"
                f"Action: {candidate_step['action']}\n"
                f"Boundary Directive: {candidate_step.get('boundary_directive')}\n"
                f"Corporate Safety Policy: Physical manipulation of energized chassis or unseating modules "
                f"is strictly prohibited for L1/L2 operators."
            )
            return candidate_step

        return candidate_step


# ============================================================================
# 3. Resolution Review Agent & Evidence Auditor
# ============================================================================

class ResolutionReviewAgent:
    """
    Evaluates the Evidence Timeline after every step.
    Computes quantitative Resolution Confidence metric (0-100%).
    Yields: Next Approved Step, Resolution Summary, or Incident Escalation Package.
    """
    @staticmethod
    def evaluate_step(session: SessionState, user_observation: str) -> dict[str, Any]:
        current_idx = session.current_step_index
        if not session.planned_steps:
            SafeStepPlannerAgent.generate_plan(session)

        if current_idx >= len(session.planned_steps):
            current_step = {
                "step_index": current_idx + 1,
                "action": "Complete Diagnostic Review",
                "source_ref": "ESM-NET-2026-V4",
                "requires_authorized_technician": False
            }
        else:
            current_step = session.planned_steps[current_idx]

        obs_lower = user_observation.lower()
        is_normal = bool(re.search(
            r'\b(normal|resolved|restored|nominal|cleared|operational|stabilized|pass|passed|ok|zero drops)\b',
            obs_lower
        ))
        is_abnormal = bool(re.search(
            r'\b(abnormal|fail|failed|failure|error|fault|loss|dropped|drops|high|stalled|lock|locked|amber|mismatch|persist|persists|down|below|tamper)\b',
            obs_lower
        ))

        if re.search(r'\b(red)\b', obs_lower):
            is_abnormal = True

        if is_normal and not is_abnormal:
            status = "VERIFIED_NORMAL"
        elif is_abnormal:
            status = "VERIFIED_ABNORMAL"
        else:
            status = "PENDING"

        # Record Evidence Step (Immutable Chronological Log)
        evidence = EvidenceStep(
            step_index=current_step["step_index"],
            action_executed=current_step["action"],
            source_doc_reference=current_step.get("source_ref", "Corporate IT ESM-NET-2026-V4"),
            user_reported_observation=user_observation.strip(),
            verification_status=status
        )
        session.timeline.append(evidence)

        # Immediate Check: If current step required technician halt
        if session.diagnostic_status == "MANDATORY_HALT_TECHNICIAN_REQUIRED" or current_step.get("requires_authorized_technician"):
            session.resolution_confidence = 94
            session.diagnostic_status = "MANDATORY_HALT_TECHNICIAN_REQUIRED"
            escalation_pkg = ResolutionReviewAgent.generate_escalation_package(session, reason="Authorized Technician Interlock Enforced")
            return {
                "type": "MANDATORY_HALT",
                "confidence": session.resolution_confidence,
                "message": session.halt_reason or "Mandatory safety interlock engaged.",
                "escalation_package": escalation_pkg
            }

        # Resolution Confirmation Check
        if status == "VERIFIED_NORMAL":
            session.resolution_confidence = 98
            session.diagnostic_status = "RESOLVED"
            resolution_summary = (
                f"[RESOLUTION CONFIRMED]\n"
                f"Fault eliminated following Step {current_step['step_index']}: '{current_step['action']}'.\n"
                f"Observed condition: '{user_observation}'.\n"
                f"Verification: Nominal operating parameters restored. Incident ticket eligible for formal closure."
            )
            return {
                "type": "RESOLUTION_SUMMARY",
                "confidence": session.resolution_confidence,
                "message": resolution_summary,
                "escalation_package": None
            }

        # Advance step index
        session.current_step_index += 1
        
        # Calculate dynamic confidence
        completed_steps = len(session.timeline)
        total_steps = max(len(session.planned_steps), 1)
        base_confidence = min(75, int((completed_steps / total_steps) * 70) + 15)
        session.resolution_confidence = base_confidence

        # Check if more steps remain
        next_step = SafeStepPlannerAgent.get_next_step(session)
        if next_step is None or session.current_step_index >= len(session.planned_steps):
            session.resolution_confidence = 88
            session.diagnostic_status = "ESCALATED"
            escalation_pkg = ResolutionReviewAgent.generate_escalation_package(session, reason="All procedural software isolation checks exhausted without fault remediation.")
            return {
                "type": "ESCALATION_PACKAGE",
                "confidence": session.resolution_confidence,
                "message": "[PROCEDURAL EXHAUSTION] All non-invasive diagnostic routines completed without fault resolution. Incident escalation package prepared.",
                "escalation_package": escalation_pkg
            }

        if session.diagnostic_status == "MANDATORY_HALT_TECHNICIAN_REQUIRED":
            session.resolution_confidence = 92
            escalation_pkg = ResolutionReviewAgent.generate_escalation_package(session, reason="Next step crosses technician authorization boundary.")
            return {
                "type": "MANDATORY_HALT",
                "confidence": session.resolution_confidence,
                "message": session.halt_reason,
                "escalation_package": escalation_pkg
            }

        step_prompt = (
            f"[NEXT APPROVED STEP {next_step['step_index']} / {len(session.planned_steps)}]\n"
            f"Subsystem Action: {next_step['action']}\n"
            f"Disruption Level: {next_step['disruption_level']}\n"
            f"Source Reference: {next_step.get('source_ref')}\n"
            f"Instructions: Execute the above inspection or telemetry command and record the observed outcome."
        )
        session.last_prompt_to_user = step_prompt

        return {
            "type": "NEXT_STEP",
            "confidence": session.resolution_confidence,
            "next_step": next_step,
            "message": step_prompt,
            "escalation_package": None
        }

    @staticmethod
    def generate_escalation_package(session: SessionState, reason: str) -> dict[str, Any]:
        """
        Compiles an immutable enterprise incident escalation package.
        """
        package = {
            "incident_id": f"INC-{session.session_id[-8:].upper()}",
            "generated_timestamp": datetime.now(timezone.utc).isoformat(),
            "device_metadata": {
                "model_id": session.model_id or "UNSPECIFIED",
                "firmware_version": session.firmware_version or "UNSPECIFIED",
                "operating_environment": session.operating_environment or "UNSPECIFIED",
                "error_code": session.error_code or "NONE_RECORDED"
            },
            "escalation_classification": "TIER-3 CERTIFIED FIELD ENGINEERING DISPATCH",
            "escalation_reason": reason,
            "resolution_confidence_at_escalation": f"{session.resolution_confidence}%",
            "diagnostic_status": session.diagnostic_status,
            "immutable_evidence_log": [
                {
                    "step": s.step_index,
                    "action": s.action_executed,
                    "source": s.source_doc_reference,
                    "observation": s.user_reported_observation,
                    "status": s.verification_status,
                    "timestamp": s.timestamp
                }
                for s in session.timeline
            ],
            "required_field_spares": [
                "FRU Replacement Module (matching active Model ID)",
                "Calibrated Optical Power Meter (OPM)",
                "ESD Grounding Kit (1 Megohm compliance)",
                "Calibrated Torque Screwdriver (6.2 in-lbs)"
            ],
            "mandatory_safety_directives": [
                "Verify zero optical laser emission before handling exposed fiber bores.",
                "Maintain chassis interlock boundaries during live equipment operation.",
                "Ensure dual-custody crypto authorization tokens are present if servicing secure enclaves."
            ]
        }
        session.escalation_record = package
        return package


# ============================================================================
# 4. Diagnostic Coordinator (Main Agent Pipeline Orchestrator)
# ============================================================================

class DiagnosticCoordinator:
    """
    Coordinates Symptom Clarification, Compatibility Gating, Safe-Step Planning,
    Evidence Auditing, and MaaS LLM Integration.
    """
    @staticmethod
    def process_turn(session_id: str, user_input: str) -> dict[str, Any]:
        session = get_or_create_session(session_id)

        if not session.symptom_summary:
            session.symptom_summary = user_input.strip()

        # Step 1: Run Symptom Clarifier Agent
        params_ready, clarification_msg = SymptomClarifierAgent.inspect_and_update(session, user_input)
        if not params_ready:
            return {
                "session_id": session.session_id,
                "status": session.diagnostic_status,
                "response_type": "CLARIFICATION_REQUIRED",
                "message": clarification_msg,
                "confidence": session.resolution_confidence,
                "timeline": [t.model_dump() for t in session.timeline],
                "escalation_record": None
            }

        # If user is answering or proceeding through planned steps
        if session.planned_steps and session.current_step_index < len(session.planned_steps):
            eval_result = ResolutionReviewAgent.evaluate_step(session, user_input)
            
            base_msg = eval_result["message"]
            maas_enhanced = call_maas_llm(
                system_prompt="You are an enterprise industrial network diagnostics engine. Respond strictly in formal engineering style without emojis, without conversational pleasantries, and with high-density technical clarity.",
                user_prompt=f"Given this verified diagnostic step result: {json.dumps(eval_result, default=str)}, output the formal response."
            )
            final_message = maas_enhanced if maas_enhanced else base_msg

            return {
                "session_id": session.session_id,
                "status": session.diagnostic_status,
                "response_type": eval_result["type"],
                "message": final_message,
                "confidence": eval_result["confidence"],
                "timeline": [t.model_dump() for t in session.timeline],
                "escalation_record": session.escalation_record
            }

        # Step 2: Initialize Planning Pipeline
        SafeStepPlannerAgent.generate_plan(session)
        first_step = SafeStepPlannerAgent.get_next_step(session)

        if not first_step:
            return {
                "session_id": session.session_id,
                "status": "COMPLETED",
                "response_type": "NO_STEPS",
                "message": "No procedural diagnostic routines identified for specified criteria.",
                "confidence": 100,
                "timeline": [t.model_dump() for t in session.timeline],
                "escalation_record": None
            }

        if session.diagnostic_status == "MANDATORY_HALT_TECHNICIAN_REQUIRED":
            escalation_pkg = ResolutionReviewAgent.generate_escalation_package(session, reason="Initial plan immediately encountered Authorized Technician boundary.")
            return {
                "session_id": session.session_id,
                "status": session.diagnostic_status,
                "response_type": "MANDATORY_HALT",
                "message": session.halt_reason,
                "confidence": 92,
                "timeline": [t.model_dump() for t in session.timeline],
                "escalation_record": escalation_pkg
            }

        session.diagnostic_status = "IN_PROGRESS"
        init_prompt = (
            f"[DIAGNOSTIC SESSION INITIALIZED: {session.model_id} | FW: {session.firmware_version}]\n"
            f"Active Environment: {session.operating_environment}\n"
            f"Associated Error Code: {session.error_code or 'NONE DETECTED'}\n\n"
            f"[FIRST APPROVED STEP 1 / {len(session.planned_steps)}]\n"
            f"Subsystem Action: {first_step['action']}\n"
            f"Disruption Level: {first_step['disruption_level']}\n"
            f"Source Reference: {first_step.get('source_ref')}\n"
            f"Boundary Directive: {first_step.get('boundary_directive')}\n\n"
            f"Execute the above instruction on the hardware console and submit the observed telemetry result."
        )
        session.last_prompt_to_user = init_prompt

        return {
            "session_id": session.session_id,
            "status": session.diagnostic_status,
            "response_type": "NEXT_STEP",
            "message": init_prompt,
            "confidence": session.resolution_confidence,
            "timeline": [t.model_dump() for t in session.timeline],
            "escalation_record": None
        }
