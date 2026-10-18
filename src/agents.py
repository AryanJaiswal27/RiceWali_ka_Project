import os
import re
import json
import math
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

from src.config import settings, MANUALS_PATH, ERROR_CODES_PATH
from src.tools import lookup_error_code, get_component_checklist

logger = logging.getLogger("ApplianceDiagnostics.Agents")

# Supported Equipment Standard Identifiers
SUPPORTED_MODELS = {
    "BOSCH_SHEM78": "Bosch 800 Series Dishwasher (SHEM78/SHPM78)",
    "WHIRLPOOL_WASHER_ALPHA": "Whirlpool Front-Load Washer (Alpha/VMW)",
    "LG_REFRIG_LFXS": "LG Smart French-Door Refrigerator (LFXS/LRFCS)",
    "BREVILLE_BES920": "Breville Dual Boiler Espresso Machine (BES920/BES980)"
}


def normalize_model_id(input_str: Optional[str]) -> Optional[str]:
    """
    Normalizes any free-form model name, appliance description, or abbreviation
    into one of the 4 verified platform identifiers:
    - BOSCH_SHEM78
    - WHIRLPOOL_WASHER_ALPHA
    - LG_REFRIG_LFXS
    - BREVILLE_BES920
    """
    if not input_str:
        return None
    s = input_str.upper().strip()

    if "BOSCH" in s or "SHEM78" in s or "SHPM78" in s or "SHX878" in s or "DISHWASHER" in s:
        return "BOSCH_SHEM78"
    if "WHIRLPOOL" in s or "ALPHA" in s or "VMW" in s or "WASHER" in s or "W11663204" in s or "WASHING" in s:
        return "WHIRLPOOL_WASHER_ALPHA"
    if "LG" in s or "LFXS" in s or "LRFCS" in s or "REFRIG" in s or "FRIDGE" in s or "LINEAR" in s:
        return "LG_REFRIG_LFXS"
    if "BREVILLE" in s or "BES920" in s or "BES980" in s or "ORACLE" in s or "ESPRESSO" in s or "BOILER" in s:
        return "BREVILLE_BES920"

    return None


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
    firmware_version: Optional[str] = "Rev 1.0"
    operating_environment: Optional[str] = "Commercial / Residential Site"
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
# Ingestion & Vector Retrieval Engine (LangChain + MaaS Embeddings + Fallback)
# ============================================================================

class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    model_id: str  # BOSCH_SHEM78, WHIRLPOOL_WASHER_ALPHA, LG_REFRIG_LFXS, BREVILLE_BES920, COMMON
    subsystem: str  # Drainage, Optical, Hydraulic, Inverter, Thermal, Safety
    authority: str = "OEM Service Manual Standard"
    section_name: str
    source_ref: str


def get_remote_openai_embeddings(texts: list[str]) -> Optional[list[list[float]]]:
    """
    Generates embeddings via TCS GenAI Lab OpenAI-compatible gateway if configured.
    Uses EMBEDDING_MODEL_NAME ("azure/genailab-maas-text-embedding-3-large").
    Falls back gracefully if offline or unauthenticated.
    """
    if not settings.maas_api_key or "your_" in settings.maas_api_key:
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

    # Strategy 2: Direct REST POST via httpx
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
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                body = resp.json()
                if "data" in body and isinstance(body["data"], list):
                    return [item["embedding"] for item in body["data"]]
    except Exception as exc:
        logger.warning(f"Remote MaaS embedding unavailable ({str(exc)}). Using offline fallback.")

    # Strategy 3: Direct Google Gemini REST API (if GEMINI_API_KEY is active)
    if settings.is_gemini_active:
        try:
            import httpx
            g_model = settings.embedding_model_name.split("/")[-1]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:batchEmbedContents?key={settings.maas_api_key}"
            requests_payload = [
                {"model": f"models/{g_model}", "content": {"parts": [{"text": t}]}}
                for t in texts
            ]
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, json={"requests": requests_payload})
                if resp.status_code == 200:
                    data = resp.json()
                    if "embeddings" in data:
                        return [e["values"] for e in data["embeddings"]]
        except Exception:
            pass

    return None


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class InMemoryTfidfVectorStore:
    """
    Zero-dependency, pure-Python in-memory TF-IDF vector store and cosine similarity engine.
    Ensures autonomous vector retrieval operations even if ChromaDB, SciPy, or compiled
    C-extensions fail to install in restricted environments like Python 3.13 / Fresco Linux.
    """
    def __init__(self, chunks: list[DocumentChunk]):
        self.chunks = chunks
        self.doc_count = len(chunks)
        self.idf: dict[str, float] = {}
        self.doc_vectors: list[dict[str, float]] = []
        self._build_index()

    def _tokenize(self, text: str) -> list[str]:
        return [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_\-\.]{2,}\b', text)]

    def _build_index(self):
        if not self.chunks:
            return
        doc_tokens = [
            self._tokenize(c.content + " " + c.section_name + " " + c.subsystem)
            for c in self.chunks
        ]
        df_counts: dict[str, int] = Counter()
        for tokens in doc_tokens:
            unique_terms = set(tokens)
            for term in unique_terms:
                df_counts[term] += 1

        for term, df in df_counts.items():
            self.idf[term] = math.log((1.0 + self.doc_count) / (1.0 + df)) + 1.0

        for idx, tokens in enumerate(doc_tokens):
            chunk = self.chunks[idx]
            tf = Counter(tokens)
            total = len(tokens) or 1
            vec: dict[str, float] = {}
            for term, count in tf.items():
                w = (count / total) * self.idf.get(term, 1.0)
                if term in chunk.section_name.lower():
                    w *= 2.0
                if term in chunk.subsystem.lower():
                    w *= 1.5
                vec[term] = w
            norm = math.sqrt(sum(v * v for v in vec.values()))
            if norm > 0:
                vec = {k: v / norm for k, v in vec.items()}
            self.doc_vectors.append(vec)

    def search(self, query: str, valid_indices: list[int], top_k: int = 3) -> list[tuple[float, DocumentChunk]]:
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []
        q_tf = Counter(q_tokens)
        q_total = len(q_tokens)
        q_vec: dict[str, float] = {}
        for term, count in q_tf.items():
            if term in self.idf:
                q_vec[term] = (count / q_total) * self.idf[term]
        q_norm = math.sqrt(sum(v * v for v in q_vec.values()))
        if q_norm == 0:
            return []
        q_vec = {k: v / q_norm for k, v in q_vec.items()}

        scored: list[tuple[float, DocumentChunk]] = []
        for idx in valid_indices:
            if idx >= len(self.doc_vectors):
                continue
            doc_vec = self.doc_vectors[idx]
            sim = sum(doc_vec.get(term, 0.0) * val for term, val in q_vec.items())
            if sim > 0:
                scored.append((sim, self.chunks[idx]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]


class VectorRetrievalEngine:
    """
    Ingests data/industrial_manuals.md using LangChain Markdown / Header chunking.
    Tags each chunk with metadata (model_id, subsystem, authority).
    Supports OpenAIEmbeddings with azure/genailab-maas-text-embedding-3-large when MAAS_API_KEY is present.
    Automatically falls back to a zero-dependency in-memory TF-IDF cosine similarity store and keyword matcher.
    """
    def __init__(self):
        self.chunks: list[DocumentChunk] = []
        self.chunk_embeddings: list[list[float]] = []
        self.is_remote_embeddings_ready: bool = False
        self.tfidf_store: Optional[InMemoryTfidfVectorStore] = None
        self._initialize_knowledge_base()

    def _split_with_langchain(self, raw_text: str) -> list[DocumentChunk]:
        """
        Splits data/industrial_manuals.md into chunks tagged with metadata
        (model_id, subsystem, authority, section_name, source_ref).
        Uses LangChain MarkdownHeaderTextSplitter or RecursiveCharacterTextSplitter.
        """
        chunks: list[DocumentChunk] = []
        chunk_counter = 1

        try:
            from langchain_text_splitters import MarkdownHeaderTextSplitter
            headers_to_split_on = [
                ("#", "manual_header"),
                ("##", "section_header"),
                ("###", "subsection_header"),
                ("####", "procedure_header"),
            ]
            markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, strip_headers=False)
            split_docs = markdown_splitter.split_text(raw_text)

            for doc in split_docs:
                content = doc.page_content.strip()
                meta = doc.metadata

                # Determine model_id
                model_tag = "COMMON"
                header_context = " ".join(meta.values()).upper()
                if "BOSCH_SHEM78" in header_context or "BOSCH" in header_context:
                    model_tag = "BOSCH_SHEM78"
                elif "WHIRLPOOL_WASHER_ALPHA" in header_context or "WHIRLPOOL" in header_context:
                    model_tag = "WHIRLPOOL_WASHER_ALPHA"
                elif "LG_REFRIG_LFXS" in header_context or "LG" in header_context:
                    model_tag = "LG_REFRIG_LFXS"
                elif "BREVILLE_BES920" in header_context or "BREVILLE" in header_context:
                    model_tag = "BREVILLE_BES920"

                # Determine subsystem
                content_lower = content.lower()
                subsystem = "GENERAL"
                if any(w in content_lower for w in ["drain", "pump", "sump", "impeller", "flapper", "filter"]):
                    subsystem = "Drainage"
                elif any(w in content_lower for w in ["optic", "turbidity", "phototransistor", "prism", "aquasensor"]):
                    subsystem = "Optical"
                elif any(w in content_lower for w in ["hydraul", "water", "pressure", "valve", "solenoid", "aps", "flood"]):
                    subsystem = "Hydraulic"
                elif any(w in content_lower for w in ["inverter", "compressor", "motor", "stator", "drive", "ipm", "tach"]):
                    subsystem = "Inverter"
                elif any(w in content_lower for w in ["thermal", "heater", "ntc", "thermistor", "temperature", "defrost"]):
                    subsystem = "Thermal"
                elif "hazard" in content_lower or "safety" in content_lower:
                    subsystem = "Safety"

                # Authority
                authority = "OEM Authorized Engineering Standard"
                sec_name = meta.get("procedure_header") or meta.get("subsection_header") or meta.get("section_header") or "General Manual"
                source_ref = f"{model_tag} / {sec_name}"

                chunks.append(DocumentChunk(
                    chunk_id=f"chunk_{chunk_counter}",
                    content=content,
                    model_id=model_tag,
                    subsystem=subsystem,
                    authority=authority,
                    section_name=sec_name,
                    source_ref=source_ref
                ))
                chunk_counter += 1

        except Exception as split_err:
            logger.warning(f"LangChain splitter fallback: {str(split_err)}. Utilizing structural regex splitter.")
            # Structural regex fallback
            manual_blocks = raw_text.split("# [MANUAL: ")
            for block in manual_blocks:
                if not block.strip():
                    continue
                lines = block.strip().split("\n")
                first_line = lines[0].replace("]", "").strip()
                model_tag = normalize_model_id(first_line) or "COMMON"

                body = "\n".join(lines[1:])
                procs = re.split(r'\n####+\s+', body)
                for p in procs:
                    if not p.strip():
                        continue
                    p_lines = p.strip().split("\n")
                    proc_title = p_lines[0].strip()
                    proc_body = "\n".join(p_lines[1:]).strip()

                    subsystem = "GENERAL"
                    pl = p.lower()
                    if "drain" in pl or "pump" in pl:
                        subsystem = "Drainage"
                    elif "optic" in pl or "turbidity" in pl:
                        subsystem = "Optical"
                    elif "hydraul" in pl or "water" in pl or "pressure" in pl:
                        subsystem = "Hydraulic"
                    elif "inverter" in pl or "compressor" in pl or "motor" in pl:
                        subsystem = "Inverter"
                    elif "thermal" in pl or "heater" in pl or "ntc" in pl or "defrost" in pl:
                        subsystem = "Thermal"

                    chunks.append(DocumentChunk(
                        chunk_id=f"chunk_{chunk_counter}",
                        content=f"MANUAL: {model_tag}\nPROCEDURE: {proc_title}\n\n{proc_body}",
                        model_id=model_tag,
                        subsystem=subsystem,
                        authority="OEM Authorized Engineering Standard",
                        section_name=proc_title,
                        source_ref=f"{model_tag} / {proc_title}"
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

            self.chunks = self._split_with_langchain(raw_text)
            self.tfidf_store = InMemoryTfidfVectorStore(self.chunks)
            logger.info(f"Ingested {len(self.chunks)} structured chunks tagged with metadata from {MANUALS_PATH.name} into in-memory vector store")

            # Attempt Remote OpenAIEmbeddings
            if settings.maas_api_key and "your_" not in settings.maas_api_key:
                try:
                    chunk_texts = [c.content for c in self.chunks]
                    vectors = get_remote_openai_embeddings(chunk_texts)
                    if vectors and len(vectors) == len(self.chunks):
                        self.chunk_embeddings = vectors
                        self.is_remote_embeddings_ready = True
                        logger.info(f"Successfully embedded {len(vectors)} chunks via MaaS OpenAIEmbeddings ({settings.embedding_model_name}).")
                except Exception as rem_err:
                    logger.warning(f"Remote embedding initialization bypassed: {str(rem_err)}")
                    self.is_remote_embeddings_ready = False

        except Exception as exc:
            logger.error(f"Failed to initialize knowledge base: {str(exc)}", exc_info=True)

    def search(self, query: str, model_filter: Optional[str] = None, top_k: int = 3) -> list[DocumentChunk]:
        """
        Retrieves relevant manual chunks.
        Strictly applies Compatibility Gate to filter by verified model_id.
        Prioritizes remote embeddings if online, otherwise zero-dependency in-memory TF-IDF vector cosine similarity.
        """
        if not self.chunks:
            return []

        # Enforce strict model filtering via Compatibility Gate
        valid_indices = []
        valid_chunks = []
        for idx, c in enumerate(self.chunks):
            if model_filter and model_filter != "COMMON":
                if c.model_id != "COMMON" and c.model_id != model_filter:
                    continue
            valid_indices.append(idx)
            valid_chunks.append(c)

        if not valid_chunks:
            valid_indices = list(range(len(self.chunks)))
            valid_chunks = self.chunks

        # Path 1: Remote Vector Cosine Similarity
        if self.is_remote_embeddings_ready and self.chunk_embeddings:
            try:
                import httpx
                headers = {"Authorization": f"Bearer {settings.maas_api_key}", "Content-Type": "application/json"}
                payload = {"model": settings.embedding_model_name, "input": [query]}
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(f"{settings.maas_api_base_url}/embeddings", headers=headers, json=payload)
                    if resp.status_code == 200:
                        q_vec = resp.json()["data"][0]["embedding"]
                        scored = []
                        for idx, chunk in enumerate(self.chunks):
                            if chunk in valid_chunks:
                                sim = cosine_similarity(q_vec, self.chunk_embeddings[idx])
                                scored.append((sim, chunk))
                        scored.sort(key=lambda x: x[0], reverse=True)
                        return [c for _, c in scored[:top_k]]
            except Exception:
                pass

        # Path 2: In-Memory Zero-Dependency TF-IDF Vector Cosine Similarity
        if self.tfidf_store:
            tfidf_results = self.tfidf_store.search(query, valid_indices, top_k=top_k)
            if tfidf_results:
                return [c for _, c in tfidf_results]

        # Path 3: Deterministic Keyword & Subsystem Matcher Fallback
        query_words = set(re.findall(r'\w+', query.lower()))
        scored_chunks: list[tuple[float, DocumentChunk]] = []

        for chunk in valid_chunks:
            c_text = (chunk.content + " " + chunk.section_name + " " + chunk.subsystem).lower()
            score = 0.0
            for w in query_words:
                if len(w) < 2:
                    continue
                cnt = c_text.count(w)
                if cnt > 0:
                    score += 1.0 + min(cnt * 0.5, 5.0)
                    if w in chunk.section_name.lower():
                        score += 3.0
                    if w in chunk.subsystem.lower():
                        score += 2.0

            if score > 0:
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored_chunks[:top_k]]


# Global Vector Engine Instance
retrieval_engine = VectorRetrievalEngine()


# ============================================================================
# MaaS LLM Client (Dual-Mode: Cloud Gateway vs Deterministic Offline Engine)
# ============================================================================

def call_maas_llm(system_prompt: str, user_prompt: str) -> Optional[str]:
    """
    Communicates with TCS GenAI Lab Model-as-a-Service endpoint when credentials exist.
    Uses settings.model_name ("azure/genailab-maas-gpt-4o-mini").
    Returns None if airgapped, offline, or invalid credentials.
    """
    if not settings.maas_api_key or "your_" in settings.maas_api_key:
        return None

    # Strategy 1: LangChain ChatOpenAI
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = ChatOpenAI(
            model=settings.model_name,
            openai_api_base=settings.maas_api_base_url,
            openai_api_key=settings.maas_api_key,
            temperature=0.0,
            max_tokens=800,
            timeout=8.0
        )
        resp = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        return resp.content.strip()
    except Exception:
        pass

    # Strategy 2: Direct REST POST via httpx
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
            "temperature": 0.0,
            "max_tokens": 800
        }
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(f"{settings.maas_api_base_url}/chat/completions", headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
    except Exception:
        pass

    # Strategy 3: Direct Google Gemini REST API (if GEMINI_API_KEY is active)
    if settings.is_gemini_active:
        try:
            import httpx
            # Ensure model name doesn't contain azure/ prefix for Google endpoint
            g_model = settings.model_name.split("/")[-1]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={settings.maas_api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"SYSTEM DIRECTIVES:\n{system_prompt}\n\nUSER PROMPT:\n{user_prompt}"}
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 800}
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
        except Exception:
            pass

    return None


# ============================================================================
# 1. Symptom Clarifier Agent
# ============================================================================

class SymptomClarifierAgent:
    """
    Ensures the user has specified the appliance Model and Symptom/Code.
    Prompts for clarification if inputs are vague (e.g. 'washing machine is not spinning').
    """
    @staticmethod
    def inspect_and_update(session: SessionState, user_input: str) -> tuple[bool, Optional[str]]:
        input_raw = user_input.strip()
        input_norm = input_raw.lower()

        # 1. Extract Model if not already established
        detected_model = normalize_model_id(user_input)
        if detected_model:
            session.model_id = detected_model

        # 2. Extract Error Codes across all 4 platforms:
        # Bosch: E15, E24, E25, E27
        # Whirlpool: F06 E01, F03 E01, F08 E01 (or F06E01, etc.)
        # LG: BLNK-5, BLNK-6, DH-ERR
        # Breville: Er01, Er02, Er03
        code_patterns = [
            r'\b(E15|E24|E25|E27)\b',
            r'\b(F\d{2}\s*E\d{2})\b',
            r'\b(BLNK[- ]?[56])\b',
            r'\b(DH[- ]?ERR)\b',
            r'\b(Er\d{2}|ER\d{2})\b'
        ]
        for pat in code_patterns:
            m = re.search(pat, user_input, re.IGNORECASE)
            if m:
                code_matched = m.group(1).upper()
                # Standardize spacing for Whirlpool
                code_matched = re.sub(r'(F\d{2})(E\d{2})', r'\1 \2', code_matched)
                code_matched = code_matched.replace("BLNK ", "BLNK-").replace("BLNK5", "BLNK-5").replace("BLNK6", "BLNK-6")
                code_matched = code_matched.replace("DHERR", "DH-ERR")
                session.error_code = code_matched
                break

        # Check if user input is vague or missing required parameters
        is_vague_symptom = False
        vague_terms = ["not working", "broken", "issue", "help", "hello", "hi", "test", "problem", "inspect"]
        if input_norm in vague_terms or len(input_norm.split()) <= 1:
            if not session.error_code:
                is_vague_symptom = True

        missing_requirements: list[str] = []
        if not session.model_id:
            missing_requirements.append(
                "APPLIANCE PLATFORM: Specify target equipment (Bosch Dishwasher, Whirlpool Washer, LG Refrigerator, or Breville Espresso)."
            )

        if not session.error_code and (is_vague_symptom or not session.symptom_summary):
            missing_requirements.append(
                "DIAGNOSTIC SYMPTOM OR ERROR CODE: Provide the active alphanumeric error code (e.g., E15, F06 E01, BLNK-5, Er01) or a specific operational symptom."
            )

        if missing_requirements:
            session.diagnostic_status = "PARAM_CLARIFICATION"
            clarification_notice = (
                "[PARAMETER DEFICIT // SYMPTOM CLARIFICATION REQUIRED]\n"
                "System requires verified telemetry parameters to isolate hardware fault domain.\n"
                "Missing requirements:\n" +
                "\n".join([f"  - {req}" for req in missing_requirements]) + "\n\n"
                "Provide the missing parameter values before procedural execution can commence."
            )
            session.last_prompt_to_user = clarification_notice
            return False, clarification_notice

        # Model and Symptom are established
        if session.diagnostic_status in ("PARAM_CLARIFICATION", "INITIALIZING"):
            session.diagnostic_status = "IN_PROGRESS"
        return True, None


# ============================================================================
# 2. Compatibility Gate & Safe-Step Planner Agent
# ============================================================================

class SafeStepPlannerAgent:
    """
    Compatibility Gate: Filters vector chunks strictly matching the verified model_id.
    Prevents cross-model confusion (e.g., never recommend Breville steam boiler procedures for a Bosch dishwasher).
    Safe-Step Planner: Ranks diagnostic steps from least disruptive (cleaning filters, resetting panels) to advanced.
    Halts with a deterministic safety interlock if a step requires an 'Authorized Field Technician'.
    """
    @staticmethod
    def generate_plan(session: SessionState) -> list[dict[str, Any]]:
        plan: list[dict[str, Any]] = []
        model_id = session.model_id or "BOSCH_SHEM78"

        # 1. Error Code Lookup with Compatibility Gate
        error_record = {}
        if session.error_code:
            error_record = lookup_error_code(session.error_code)
            # Compatibility Gate Verification:
            rec_model = error_record.get("model_id")
            if rec_model and rec_model != "UNKNOWN" and rec_model != model_id:
                logger.warning(f"Compatibility Gate: Error code {session.error_code} belongs to {rec_model}, but active session is {model_id}.")
                # Adjust or warn, but do not cross-pollinate procedures!
                if not session.model_id or session.model_id == "BOSCH_SHEM78" and not session.symptom_summary:
                    session.model_id = rec_model
                    model_id = rec_model

        step_idx = 1

        # Add steps from error code database
        if error_record.get("status") == "SUCCESS" and error_record.get("initial_steps"):
            # Enforce Compatibility Gate: Only use if model matches
            if error_record.get("model_id") == model_id:
                for step_text in error_record["initial_steps"]:
                    is_tech_halt = False
                    st_lower = step_text.lower()
                    if any(term in st_lower for term in [
                        "mandatory halt", "authorized field technician", "epa universal",
                        "certified technician", "replace linear compressor", "brazing", "flameless lokring",
                        "r600a", "replace failed wash heating element", "ssr triac breakdown"
                    ]):
                        is_tech_halt = True

                    disruption = "NON_DISRUPTIVE"
                    if is_tech_halt:
                        disruption = "CRITICAL_INVASIVE"
                    elif any(w in st_lower for w in ["measure", "multimeter", "disconnect", "remove", "unplug"]):
                        disruption = "LOW_DISRUPTION"

                    plan.append({
                        "step_index": step_idx,
                        "action": step_text,
                        "subsystem": error_record.get("subsystem", "GENERAL"),
                        "disruption_level": disruption,
                        "requires_technician": is_tech_halt or error_record.get("requires_technician", False),
                        "is_halt_boundary": is_tech_halt,
                        "source_ref": f"ERROR-DB // {error_record['code']} ({error_record.get('citation', 'MANUAL-REF')})",
                        "boundary_directive": error_record.get("technician_authorization_boundary", "Standard maintenance procedure.")
                    })
                    step_idx += 1

        # 2. Add Component Checklist steps if plan is short or no error code
        if len(plan) < 3:
            # Infer subsystem from symptom or error
            symp = (session.symptom_summary or "").lower()
            subsystem_name = "Drainage"
            if any(w in symp for w in ["drain", "pump", "water standing", "e24", "e25", "coin"]):
                subsystem_name = "Drainage"
            elif any(w in symp for w in ["turbidity", "cloudy", "optic", "aquasensor", "light"]):
                subsystem_name = "Optical"
            elif any(w in symp for w in ["water", "flood", "leak", "fill", "pressure", "aps", "solenoid", "e15", "er01", "f03"]):
                subsystem_name = "Hydraulic"
            elif any(w in symp for w in ["compressor", "motor", "spin", "tach", "blnk", "inverter", "rpm", "f06"]):
                subsystem_name = "Inverter"
            elif any(w in symp for w in ["heat", "temp", "cold", "defrost", "runaway", "ntc", "er02", "er03", "f08", "dh-err"]):
                subsystem_name = "Thermal"

            checklist_steps = get_component_checklist(subsystem_name, model_id)
            for item in checklist_steps:
                # Deduplicate
                if not any(item["action"][:35] in p["action"] for p in plan):
                    plan.append({
                        "step_index": step_idx,
                        "action": item["action"],
                        "subsystem": item.get("subsystem", subsystem_name),
                        "disruption_level": item["disruption_level"],
                        "requires_technician": item["requires_technician"],
                        "is_halt_boundary": item["requires_technician"],
                        "source_ref": f"CHECKLIST // {item.get('citation', 'STD-PROC')}",
                        "boundary_directive": item.get("boundary_condition", "Adhere to safety boundaries.")
                    })
                    step_idx += 1

        # 3. Sort / Rank Plan:
        # Curated OEM procedures in error_codes.json are already authored in strict safety-first & physical access order.
        # Preserve OEM curated sequence, ensuring any critical technician halts are positioned at the final boundary.
        if error_record.get("status") == "SUCCESS" and error_record.get("initial_steps"):
            plan.sort(key=lambda s: (1 if s.get("is_halt_boundary") else 0, s.get("step_index", 0)))
        else:
            disruption_weights = {
                "NON_DISRUPTIVE": 1,
                "LOW_DISRUPTION": 2,
                "CRITICAL_INVASIVE": 3
            }
            plan.sort(key=lambda s: disruption_weights.get(s["disruption_level"], 2))

        # Re-index sequentially after ranking
        for i, p in enumerate(plan, 1):
            p["step_index"] = i

        session.planned_steps = plan
        return plan

    @staticmethod
    def get_next_step(session: SessionState) -> Optional[dict[str, Any]]:
        if not session.planned_steps:
            SafeStepPlannerAgent.generate_plan(session)

        current_idx = session.current_step_index
        if current_idx >= len(session.planned_steps):
            return None

        candidate = session.planned_steps[current_idx]

        # Enforce deterministic halt if step requires Authorized Field Technician
        if candidate.get("requires_technician") or candidate.get("is_halt_boundary"):
            session.diagnostic_status = "MANDATORY_HALT_TECHNICIAN_REQUIRED"
            model_id = session.model_id or "APPLIANCE"

            safety_warning = "ELECTRICAL / MECHANICAL SAFETY INTERLOCK ENGAGED"
            if model_id == "BOSCH_SHEM78":
                safety_warning = "240V BASE PAN ELECTRICAL HAZARD // CIRCULATION HEAT PUMP INTERLOCK"
            elif model_id == "WHIRLPOOL_WASHER_ALPHA":
                safety_warning = "DIRECT-DRIVE CAPACITOR DISCHARGE (400V DC) // 1200 RPM SPIN BASKET INTERLOCK"
            elif model_id == "LG_REFRIG_LFXS":
                safety_warning = "FLAMMABLE R600a ISOBUTANE REFRIGERANT // 3-MINUTE PCB BLEED-DOWN INTERLOCK"
            elif model_id == "BREVILLE_BES920":
                safety_warning = "15-BAR PRESSURIZED STEAM BOILER SCALDING // BRASS SOLENOID TEARDOWN BOUNDARY"

            session.halt_reason = (
                f"[MANDATORY SAFETY BOUNDARY INTERLOCK // {safety_warning}]\n"
                f"Step {candidate['step_index']} requires 'Authorized Field Technician' credential.\n"
                f"Subsystem: {candidate.get('subsystem', 'CRITICAL')}\n"
                f"Action: {candidate['action']}\n"
                f"Boundary Directive: {candidate.get('boundary_directive')}\n"
                f"Safety Policy: Uncertified disassembly, brazing, high-voltage capacitor handling, or pressurized steam boiler teardown is strictly prohibited."
            )
            return candidate

        return candidate


# ============================================================================
# 3. Resolution Review Agent & Evidence Auditor
# ============================================================================

class ResolutionReviewAgent:
    """
    Evaluates operator observation against the current diagnostic step.
    Appends observation to immutable Evidence Timeline.
    Recalculates Resolution Confidence (0-100%).
    Emits:
      - Next approved procedural step.
      - 'FAULT RESOLVED' when observation confirms normal telemetry.
      - Escalation package if a safety boundary is hit or confidence stagnates.
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
                "subsystem": "GENERAL",
                "source_ref": "OEM-STANDARD",
                "requires_technician": False
            }
        else:
            current_step = session.planned_steps[current_idx]

        obs_lower = user_observation.lower()
        is_normal = bool(re.search(
            r'\b(normal|resolved|cleared|operating|passes|passed|ok|nominal|clean|free|unblocked|restored|0 ohms|ready)\b',
            obs_lower
        ))
        is_abnormal = bool(re.search(
            r'\b(abnormal|fail|failed|failure|error|stuck|blocked|blown|jammed|leaking|shorted|open|infinite|high|burn|sparks|blinking|buzzing|5-blink|6-blink)\b',
            obs_lower
        ))

        if is_normal and not is_abnormal:
            status = "VERIFIED_NORMAL"
        elif is_abnormal:
            status = "VERIFIED_ABNORMAL"
        else:
            status = "BLOCKED" if "cannot" in obs_lower or "blocked" in obs_lower else "PENDING"

        # Record Evidence Step (Immutable Chronological Log)
        evidence = EvidenceStep(
            step_index=current_step["step_index"],
            action_executed=current_step["action"],
            source_doc_reference=current_step.get("source_ref", "OEM Service Standard"),
            user_reported_observation=user_observation.strip(),
            verification_status=status
        )
        session.timeline.append(evidence)

        # Check 1: Mandatory Technician Halt
        if session.diagnostic_status == "MANDATORY_HALT_TECHNICIAN_REQUIRED" or current_step.get("requires_technician"):
            session.resolution_confidence = 94
            session.diagnostic_status = "MANDATORY_HALT_TECHNICIAN_REQUIRED"
            escalation_pkg = ResolutionReviewAgent.generate_escalation_package(session, reason="Authorized Technician Interlock Enforced")
            session.escalation_record = escalation_pkg
            return {
                "type": "MANDATORY_HALT",
                "confidence": session.resolution_confidence,
                "message": session.halt_reason or "Mandatory safety interlock engaged.",
                "escalation_package": escalation_pkg
            }

        # Check 2: Resolution Confirmed ("FAULT RESOLVED")
        if status == "VERIFIED_NORMAL":
            session.resolution_confidence = 98
            session.diagnostic_status = "RESOLVED"
            session.current_step_index = min(session.current_step_index + 1, len(session.planned_steps))
            resolution_summary = (
                f"[FAULT RESOLVED // OPERATIONAL TELEMETRY RESTORED]\n"
                f"Platform: {SUPPORTED_MODELS.get(session.model_id, session.model_id)}\n"
                f"Remediated at Step {current_step['step_index']}: '{current_step['action']}'.\n"
                f"Operator Telemetry: '{user_observation}'.\n"
                f"Status: Normal operational parameters verified. Equipment returned to active service."
            )
            session.last_prompt_to_user = resolution_summary
            return {
                "type": "RESOLUTION_SUMMARY",
                "confidence": session.resolution_confidence,
                "message": resolution_summary,
                "escalation_package": None
            }

        # Advance step counter
        session.current_step_index += 1

        # Dynamic Confidence Recalculation
        completed_steps = len(session.timeline)
        total_steps = max(len(session.planned_steps), 1)
        base_confidence = min(75, int((completed_steps / total_steps) * 70) + 15)
        session.resolution_confidence = base_confidence

        # Check 3: Check next step
        next_step = SafeStepPlannerAgent.get_next_step(session)

        # If exhausted all planned steps without resolution
        if next_step is None or session.current_step_index >= len(session.planned_steps):
            session.resolution_confidence = 88
            session.diagnostic_status = "ESCALATED"
            escalation_pkg = ResolutionReviewAgent.generate_escalation_package(
                session,
                reason="All non-invasive procedural checks exhausted without fault remediation. Field dispatch required."
            )
            session.escalation_record = escalation_pkg
            msg = (
                "[PROCEDURAL EXHAUSTION // DISPATCH ESCALATION]\n"
                "All non-invasive operational procedures executed without restoring nominal telemetry.\n"
                "Formal incident escalation package generated for certified field service."
            )
            session.last_prompt_to_user = msg
            return {
                "type": "ESCALATION_PACKAGE",
                "confidence": session.resolution_confidence,
                "message": msg,
                "escalation_package": escalation_pkg
            }

        # If next step is technician halt
        if session.diagnostic_status == "MANDATORY_HALT_TECHNICIAN_REQUIRED":
            session.resolution_confidence = 92
            escalation_pkg = ResolutionReviewAgent.generate_escalation_package(session, reason="Next step crosses technician authorization boundary.")
            session.escalation_record = escalation_pkg
            return {
                "type": "MANDATORY_HALT",
                "confidence": session.resolution_confidence,
                "message": session.halt_reason,
                "escalation_package": escalation_pkg
            }

        step_prompt = (
            f"[NEXT APPROVED STEP {next_step['step_index']} / {len(session.planned_steps)}]\n"
            f"Subsystem: {next_step.get('subsystem', 'GENERAL')}\n"
            f"Action: {next_step['action']}\n"
            f"Disruption Level: {next_step['disruption_level']}\n"
            f"Citation: {next_step.get('source_ref')}\n"
            f"Directive: Execute inspection or measurement and input the observed result."
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
        Compiles formal incident escalation JSON payload for field technicians.
        """
        model_id = session.model_id or "UNKNOWN"

        spares_map = {
            "BOSCH_SHEM78": [
                "BLDC Drain Pump Motor (Part # 00631200)",
                "Sump Perimeter Silicone Gasket Kit",
                "Float Microswitch Safety Assembly"
            ],
            "WHIRLPOOL_WASHER_ALPHA": [
                "Direct Drive Motor Tachometer Harness (Part # W10278941)",
                "Analog Pressure Sensor APS Transducer (Part # W11417088)",
                "Wash Tubular Heating Element 1200W (Part # W10842825)"
            ],
            "LG_REFRIG_LFXS": [
                "Linear Inverter Compressor FLB075LANA (R600a)",
                "Main Micom Inverter PCB Assembly (EBR822304*)",
                "Evaporator Defrost Sheath Heater & Bimetal Fuse Harness"
            ],
            "BREVILLE_BES920": [
                "2-Way Brass Boiler Fill Solenoid Valve 120V",
                "Grouphead Solid State Relay (SSR) 25A",
                "Steam Boiler Threaded NTC Thermistor Probe & PTFE Seal"
            ]
        }

        safety_directives_map = {
            "BOSCH_SHEM78": [
                "De-energize 120V/240V mains breaker before removing lower toe-kick access pan.",
                "Verify EPS float chamber is dry before applying test cycle power.",
                "Torque circulation clamp screws to 1.8 Nm."
            ],
            "WHIRLPOOL_WASHER_ALPHA": [
                "Observe mandatory 3-minute MCU capacitor bleed-down delay before touching drive terminals.",
                "Ensure door lock solenoid interlock is fully engaged during high-speed spin test.",
                "Verify drum rotation clearance before securing rear access panel."
            ],
            "LG_REFRIG_LFXS": [
                "Flammable R600a Isobutane refrigerant isolation: No open flames or brazing torches permitted.",
                "Maintain continuous exhaust ventilation and utilize certified Lokring mechanical couplings.",
                "Wait 180 seconds for Main Inverter PCB filter capacitors to discharge below 50V DC."
            ],
            "BREVILLE_BES920": [
                "Scalding Hazard: Boiler operates under 15-bar hydraulic / 3-bar steam pressure at 140 C.",
                "Allow 45-minute cool-down and vent steam via rear manual drain petcocks before opening fittings.",
                "Apply high-temperature food-grade thread sealant to brass solenoid threads."
            ]
        }

        package = {
            "incident_id": f"ESC-{session.session_id[-8:].upper()}",
            "generated_timestamp": datetime.now(timezone.utc).isoformat(),
            "equipment_telemetry": {
                "model_id": model_id,
                "model_name": SUPPORTED_MODELS.get(model_id, model_id),
                "firmware_version": session.firmware_version,
                "operating_environment": session.operating_environment,
                "error_code": session.error_code or "NONE_RECORDED",
                "symptom_summary": session.symptom_summary or "Unspecified mechanical failure"
            },
            "escalation_classification": "AUTHORIZED OEM FIELD SERVICE TECHNICIAN REQUIRED",
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
                    "verification_status": s.verification_status,
                    "timestamp": s.timestamp
                }
                for s in session.timeline
            ],
            "recommended_oem_spares": spares_map.get(model_id, ["OEM Replacement Part Kit"]),
            "mandatory_safety_directives": safety_directives_map.get(model_id, ["Adhere to OEM safety guidelines."])
        }
        session.escalation_record = package
        return package


# ============================================================================
# 4. Diagnostic Coordinator (Main Pipeline Orchestrator)
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
                "model_id": session.model_id,
                "status": session.diagnostic_status,
                "response_type": "CLARIFICATION_REQUIRED",
                "message": clarification_msg,
                "confidence": session.resolution_confidence,
                "timeline": [t.model_dump() for t in session.timeline],
                "escalation_record": None
            }

        # Step 2: If session already has a plan and user is reporting an observation
        if session.planned_steps and session.current_step_index < len(session.planned_steps):
            eval_result = ResolutionReviewAgent.evaluate_step(session, user_input)

            base_msg = eval_result["message"]
            maas_response = call_maas_llm(
                system_prompt="You are an industrial appliance service diagnostic coordinator. Format technical responses strictly in monospace engineering style without conversational fluff, and zero emojis.",
                user_prompt=f"Given this verified diagnostic step result: {json.dumps(eval_result, default=str)}, output the formal technical directive."
            )
            final_message = maas_response if maas_response else base_msg

            return {
                "session_id": session.session_id,
                "model_id": session.model_id,
                "status": session.diagnostic_status,
                "response_type": eval_result["type"],
                "message": final_message,
                "confidence": eval_result["confidence"],
                "timeline": [t.model_dump() for t in session.timeline],
                "escalation_record": eval_result.get("escalation_package") or session.escalation_record
            }

        # Step 3: Initialize Planning Pipeline
        SafeStepPlannerAgent.generate_plan(session)
        first_step = SafeStepPlannerAgent.get_next_step(session)

        if not first_step:
            return {
                "session_id": session.session_id,
                "model_id": session.model_id,
                "status": "COMPLETED",
                "response_type": "NO_STEPS",
                "message": "No procedural diagnostic routines identified for specified appliance model and symptom.",
                "confidence": 100,
                "timeline": [t.model_dump() for t in session.timeline],
                "escalation_record": None
            }

        if session.diagnostic_status == "MANDATORY_HALT_TECHNICIAN_REQUIRED":
            escalation_pkg = ResolutionReviewAgent.generate_escalation_package(
                session, reason="Initial diagnostic plan encountered Authorized Technician boundary."
            )
            return {
                "session_id": session.session_id,
                "model_id": session.model_id,
                "status": session.diagnostic_status,
                "response_type": "MANDATORY_HALT",
                "message": session.halt_reason,
                "confidence": 92,
                "timeline": [t.model_dump() for t in session.timeline],
                "escalation_record": escalation_pkg
            }

        session.diagnostic_status = "IN_PROGRESS"
        init_prompt = (
            f"[DIAGNOSTIC SESSION INITIALIZED // {SUPPORTED_MODELS.get(session.model_id, session.model_id)}]\n"
            f"Firmware Revision: {session.firmware_version}\n"
            f"Associated Error Code: {session.error_code or 'NONE DETECTED'}\n\n"
            f"[FIRST APPROVED STEP 1 / {len(session.planned_steps)}]\n"
            f"Subsystem: {first_step.get('subsystem', 'GENERAL')}\n"
            f"Directive: {first_step['action']}\n"
            f"Disruption Level: {first_step['disruption_level']}\n"
            f"Citation: {first_step.get('source_ref')}\n"
            f"Safety Boundary: {first_step.get('boundary_directive')}\n\n"
            f"Execute the above procedure and record the observed result."
        )
        session.last_prompt_to_user = init_prompt

        return {
            "session_id": session.session_id,
            "model_id": session.model_id,
            "status": session.diagnostic_status,
            "response_type": "NEXT_STEP",
            "message": init_prompt,
            "confidence": session.resolution_confidence,
            "timeline": [t.model_dump() for t in session.timeline],
            "escalation_record": None
        }
