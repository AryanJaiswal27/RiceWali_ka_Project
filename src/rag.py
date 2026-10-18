"""
rag.py  -  Multi-Tier Retrieval-Augmented Generation & Multi-Criteria Re-Ranking

Multi-document repository loader:
  1. Product Manuals (baseline procedural guides, authority=0.60)
  2. Service Bulletins (manufacturer technical advisories, authority=0.92)
  3. Known-Issue Documents (field symptoms & fast workarounds, authority=0.76)
  4. Approved Escalation Rules (safety, compliance & regulatory limits, authority=1.00)
  5. User-Uploaded Documents (saved in data/uploads)

Multi-Criteria Re-Ranking formula:
  CompositeScore = (0.45 * IssueSimilarity) + (0.35 * ModelCompatibility) + (0.20 * DocumentAuthority)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from langchain_core.documents import Document

from src.config import (
    DOCUMENT_AUTHORITY_WEIGHTS,
    ESCALATION_RULES_PATH,
    KNOWN_ISSUES_PATH,
    MANUALS_PATH,
    SERVICE_BULLETINS_PATH,
    TOP_K,
    UPLOADS_DIR,
    VECTOR_STORE_DIR,
    WEIGHT_AUTHORITY,
    WEIGHT_MODEL,
    WEIGHT_SEMANTIC,
)

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "not", "are", "was",
    "has", "have", "but", "can", "does", "its", "when", "while", "after",
    "into", "out", "all", "any", "you", "your", "get", "got", "won", "will",
    "please", "help", "device", "unit",
}


def _stem(word: str) -> str:
    """Stemming so 'cooling', 'cooled', and 'cool' align."""
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[:-len(suffix)]
    return word


def _words(text: str) -> list[str]:
    """Tokenize and stem keywords for lexical similarity scoring."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [_stem(w) for w in words if len(w) > 2 and w not in STOP_WORDS]


# ----------------------------------------------------------------------------
# DOCUMENT REPOSITORY LOADERS
# ----------------------------------------------------------------------------

def load_manual_chunks() -> list[dict]:
    """Load standard product manual markdown procedures."""
    if not MANUALS_PATH.exists():
        return []
    text = MANUALS_PATH.read_text(encoding="utf-8")
    chunks: list[dict] = []
    product = None
    current: Optional[dict] = None

    for line in text.splitlines():
        # Match section headers for equipment
        if line.startswith("# [MANUAL:"):
            m = re.search(r"#\s*\[MANUAL:\s*([^\]]+)\]", line)
            if m:
                product = m.group(1).strip()
            current = None
        elif line.startswith("## Equipment Specification:"):
            product = line.split(":", 1)[1].strip()
            current = None
        elif line.startswith("## ") and not line.startswith("## Equipment Specification:"):
            product = line[3:].strip()
            current = None
        elif re.match(r"#+\s*Procedure\s+[A-Z0-9\-]+:", line):
            header = re.sub(r"^#+\s*", "", line).strip()
            match = re.match(r"Procedure\s+([A-Z0-9\-]+):\s*(.*)", header)
            procedure_id = match.group(1) if match else header
            title = match.group(2) if match else header
            current = {
                "id": procedure_id,
                "doc_type": "product_manual",
                "product": product,
                "title": title,
                "text": header + "\n",
                "authority_score": DOCUMENT_AUTHORITY_WEIGHTS["product_manual"],
                "software_version_min": None,
                "software_version_max": None,
                "ordered_checks": [],
                "hazard_tags": [],
            }
            chunks.append(current)
        elif current is not None:
            current["text"] += line + "\n"

    for chunk in chunks:
        m = re.search(r"\*\*Disruption Level:\*\*\s*(.*)", chunk["text"])
        chunk["disruption_level"] = m.group(1).strip() if m else "Standard Operator Level"
        chunk["needs_technician"] = bool(
            re.search(r"critical invasive|technician required|authorized .*technician|mandatory halt", chunk["text"], re.I)
        )
        if "flammable" in chunk["text"].lower() or "r32" in chunk["text"].lower():
            chunk["hazard_tags"].append("FLAMMABLE_REFRIGERANT")
        if "voltage" in chunk["text"].lower() or "multimeter" in chunk["text"].lower() or "capacitor" in chunk["text"].lower():
            chunk["hazard_tags"].append("ELECTRICAL_SAFETY")

    return chunks


def load_service_bulletins() -> list[dict]:
    """Load manufacturer technical service bulletins."""
    if not SERVICE_BULLETINS_PATH.exists():
        return []
    data = json.loads(SERVICE_BULLETINS_PATH.read_text(encoding="utf-8"))
    chunks: list[dict] = []
    for item in data:
        full_text = f"Service Bulletin {item['id']}: {item['title']}\n"
        full_text += f"Product: {item['model']}\nSubsystem: {item.get('subsystem', '')}\n"
        full_text += f"Summary: {item['summary']}\nOperating Conditions: {item.get('operating_conditions', '')}\nOrdered Checks:\n"
        for check in item.get("ordered_checks", []):
            full_text += f"  {check['step']}. {check['action']} [{check['hazard_notice']}]\n"

        chunks.append({
            "id": item["id"],
            "doc_type": "service_bulletin",
            "product": item["model"],
            "title": item["title"],
            "text": full_text,
            "authority_score": item.get("authority_score", DOCUMENT_AUTHORITY_WEIGHTS["service_bulletin"]),
            "software_version_min": item.get("software_version_min"),
            "software_version_max": item.get("software_version_max"),
            "disruption_level": "Manufacturer Service Bulletin",
            "needs_technician": any(c.get("requires_technician") for c in item.get("ordered_checks", [])),
            "ordered_checks": item.get("ordered_checks", []),
            "hazard_tags": ["CRITICAL_BULLETIN", "FIELD_SERVICE_ADVISORY"],
        })
    return chunks


def load_known_issues() -> list[dict]:
    """Load known issue field workarounds."""
    if not KNOWN_ISSUES_PATH.exists():
        return []
    data = json.loads(KNOWN_ISSUES_PATH.read_text(encoding="utf-8"))
    chunks: list[dict] = []
    for item in data:
        full_text = f"Known Issue {item['id']}: {item['title']}\n"
        full_text += f"Product: {item['model']}\nSubsystem: {item.get('subsystem', '')}\n"
        full_text += f"Summary: {item['summary']}\nSymptoms: {', '.join(item.get('symptoms', []))}\n"
        full_text += f"Operating Conditions: {item.get('operating_conditions', '')}\nOrdered Checks:\n"
        for check in item.get("ordered_checks", []):
            full_text += f"  {check['step']}. {check['action']}\n"

        chunks.append({
            "id": item["id"],
            "doc_type": "known_issue",
            "product": item["model"],
            "title": item["title"],
            "text": full_text,
            "authority_score": item.get("authority_score", DOCUMENT_AUTHORITY_WEIGHTS["known_issue"]),
            "software_version_min": item.get("software_version_min"),
            "software_version_max": item.get("software_version_max"),
            "disruption_level": "Known-Issue Field Workaround",
            "needs_technician": any(c.get("requires_technician") for c in item.get("ordered_checks", [])),
            "ordered_checks": item.get("ordered_checks", []),
            "hazard_tags": ["FIELD_OBSERVATION", "KNOWN_WORKAROUND"],
        })
    return chunks


def load_escalation_rules() -> list[dict]:
    """Load approved safety and regulatory escalation boundaries."""
    if not ESCALATION_RULES_PATH.exists():
        return []
    data = json.loads(ESCALATION_RULES_PATH.read_text(encoding="utf-8"))
    chunks: list[dict] = []
    for item in data:
        full_text = f"Approved Escalation Rule {item['id']}: {item['title']}\n"
        full_text += f"Product: {item['model']}\nSubsystem: {item.get('subsystem', '')}\n"
        full_text += f"Boundary Policy: {item.get('boundary_policy', '')}\n"
        full_text += f"Mandated Qualification: {item.get('mandated_qualification', '')}\n"
        full_text += f"Mandated Tools: {', '.join(item.get('mandated_tools', []))}\n"
        full_text += f"SLA Tier: {item.get('sla_tier', '')}\nOrdered Checks:\n"
        for check in item.get("ordered_checks", []):
            full_text += f"  {check['step']}. {check['action']} [{check['hazard_notice']}]\n"

        chunks.append({
            "id": item["id"],
            "doc_type": "escalation_rule",
            "product": item["model"],
            "title": item["title"],
            "text": full_text,
            "authority_score": item.get("authority_score", DOCUMENT_AUTHORITY_WEIGHTS["escalation_rule"]),
            "software_version_min": item.get("software_version_min"),
            "software_version_max": item.get("software_version_max"),
            "disruption_level": "Mandatory Regulatory / Safety Boundary",
            "needs_technician": True,
            "mandated_qualification": item.get("mandated_qualification"),
            "mandated_tools": item.get("mandated_tools", []),
            "sla_tier": item.get("sla_tier"),
            "ordered_checks": item.get("ordered_checks", []),
            "hazard_tags": ["LIFE_SAFETY_CRITICAL", "REGULATORY_COMPLIANCE"],
        })
    return chunks


def load_user_uploads() -> list[dict]:
    """Load user-uploaded documents from data/uploads."""
    if not UPLOADS_DIR.exists():
        return []
    chunks: list[dict] = []
    for path in UPLOADS_DIR.glob("*.*"):
        if path.suffix.lower() not in (".md", ".txt", ".json"):
            continue
        try:
            content = path.read_text(encoding="utf-8")
            chunks.append({
                "id": f"UPLOAD-{path.stem.upper()}",
                "doc_type": "user_upload",
                "product": "ALL_MODELS",
                "title": f"Uploaded Doc: {path.name}",
                "text": content,
                "authority_score": 0.50,
                "software_version_min": None,
                "software_version_max": None,
                "disruption_level": "Runtime Uploaded Reference",
                "needs_technician": False,
                "ordered_checks": [],
                "hazard_tags": ["USER_CONTRIBUTED"],
            })
        except Exception:
            continue
    return chunks


def load_all_repository_chunks() -> list[dict]:
    """Load all 5 document tiers."""
    all_chunks: list[dict] = []
    all_chunks.extend(load_manual_chunks())
    all_chunks.extend(load_service_bulletins())
    all_chunks.extend(load_known_issues())
    all_chunks.extend(load_escalation_rules())
    all_chunks.extend(load_user_uploads())
    return all_chunks


# ----------------------------------------------------------------------------
# MULTI-DOC KNOWLEDGE BASE & 3-FACTOR RE-RANKER
# ----------------------------------------------------------------------------

class MultiDocKnowledgeBase:
    """Holds LangChain documents, ChromaDB vector store, and 3-factor re-ranker."""

    def __init__(self):
        self.raw_chunks = load_all_repository_chunks()
        self.documents = [
            Document(
                page_content=c["text"],
                metadata={
                    "id": c["id"],
                    "doc_type": c["doc_type"],
                    "product": c["product"],
                    "title": c["title"],
                    "authority_score": c["authority_score"],
                    "disruption_level": c.get("disruption_level", ""),
                    "needs_technician": c.get("needs_technician", False),
                },
            )
            for c in self.raw_chunks
        ]
        self.collection = None
        self.mode = "keyword"
        self._try_start_vector_db()

    def _try_start_vector_db(self) -> None:
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
            collection = client.get_or_create_collection("multi_doc_troubleshooter")

            if collection.count() != len(self.raw_chunks):
                try:
                    client.delete_collection("multi_doc_troubleshooter")
                except Exception:
                    pass
                collection = client.create_collection("multi_doc_troubleshooter")
                collection.add(
                    ids=[c["id"] for c in self.raw_chunks],
                    documents=[c["text"] for c in self.raw_chunks],
                    metadatas=[
                        {
                            "product": str(c["product"]),
                            "title": str(c["title"]),
                            "doc_type": str(c["doc_type"]),
                        }
                        for c in self.raw_chunks
                    ],
                )
            self.collection = collection
            self.mode = "vector"
        except Exception as error:
            self.collection = None
            self.mode = "keyword"

    # -- Multi-Criteria Re-Ranking Algorithm ----------------------------------
    def compute_model_score(self, chunk: dict, target_product: Optional[str], software_version: Optional[str]) -> float:
        """Calculate model compatibility score [0.0 - 1.0] with version bonuses."""
        chunk_model = chunk.get("product") or ""
        if not target_product or chunk_model == "ALL_MODELS":
            base = 0.85
        elif chunk_model == target_product:
            base = 1.00
        elif target_product.lower() in chunk_model.lower() or chunk_model.lower() in target_product.lower():
            base = 0.95
        else:
            # Cross-model penalty
            base = 0.05

        # Software version compatibility adjustment
        v_min = chunk.get("software_version_min")
        v_max = chunk.get("software_version_max")
        if software_version and software_version != "UNKNOWN" and (v_min or v_max):
            if v_min and software_version < v_min:
                base *= 0.4
            elif v_max and software_version > v_max:
                base *= 0.6
            else:
                base = min(1.0, base + 0.05)

        return round(base, 3)

    def compute_similarity(self, query_words: list[str], chunk_text: str) -> float:
        """Calculate keyword/token overlap similarity [0.0 - 1.0]."""
        if not query_words:
            return 0.3
        target_words = set(_words(chunk_text))
        if not target_words:
            return 0.0
        hits = sum(1 for w in query_words if w in target_words)
        ratio = hits / len(query_words)
        return round(min(1.0, ratio * 1.5), 3)

    def search(
        self,
        query: str,
        product: Optional[str] = None,
        software_version: Optional[str] = None,
        top_k: int = TOP_K,
    ) -> list[dict]:
        """
        Executes multi-tier retrieval + multi-criteria 3-factor re-ranking:
        CompositeScore = (0.45 * S_semantic) + (0.35 * S_model) + (0.20 * S_authority)
        """
        query_tokens = _words(query)
        candidates = list(self.raw_chunks)
        scored_candidates = []

        for chunk in candidates:
            sim_score = self.compute_similarity(query_tokens, chunk["text"])
            model_score = self.compute_model_score(chunk, product, software_version)
            auth_score = chunk.get("authority_score", 0.60)

            # 3-factor composite formula
            composite = (
                (WEIGHT_SEMANTIC * sim_score)
                + (WEIGHT_MODEL * model_score)
                + (WEIGHT_AUTHORITY * auth_score)
            )

            # Preserve full transparency of ranking breakdown
            scored_candidates.append({
                **chunk,
                "similarity_score": round(sim_score, 3),
                "model_score": round(model_score, 3),
                "authority_score": round(auth_score, 3),
                "composite_score": round(composite, 4),
            })

        # Rank descending by composite score
        scored_candidates.sort(key=lambda c: c["composite_score"], reverse=True)
        return scored_candidates[:top_k]


# Singleton instance
_KB: Optional[MultiDocKnowledgeBase] = None


def get_knowledge_base() -> MultiDocKnowledgeBase:
    global _KB
    if _KB is None:
        _KB = MultiDocKnowledgeBase()
    return _KB


def reload_knowledge_base() -> MultiDocKnowledgeBase:
    global _KB
    _KB = MultiDocKnowledgeBase()
    return _KB
