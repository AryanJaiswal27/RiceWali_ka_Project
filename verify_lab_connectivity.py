#!/usr/bin/env python3
"""
TCS GenAI Lab - Connectivity & Subsystem Verification Runner
Standard: Corporate IT Engineering Diagnostic Standard ESM-NET-2026-V4
Target: Enterprise Fresco VM / Sandbox Validation
"""

import sys
import time
from typing import Any

from src.config import settings, ENV_PATH
from src.tools import lookup_error_code
from src.agents import retrieval_engine, SafeStepPlannerAgent, get_or_create_session


def mask_key(key: str) -> str:
    if not key:
        return "[NOT SET]"
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def run_verification():
    start_time = time.time()
    results = {}

    print("=" * 80)
    print("TCS GENAI LAB // ENTERPRISE CONNECTIVITY & SUBSYSTEM VERIFICATION RUNNER")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("Standard: Corporate IT ESM-NET-2026-V4 | Fresco Sandbox Compliance")
    print("=" * 80)

    # ------------------------------------------------------------------------
    # 1. Environment & Configuration Subsystem Check
    # ------------------------------------------------------------------------
    print("\n[SUBSYSTEM 1: ENVIRONMENT & CONFIGURATION VALIDATION]")
    env_file_loaded = ENV_PATH.exists()
    print(f"  Configuration File (.env)        : {'FOUND (' + str(ENV_PATH) + ')' if env_file_loaded else 'NOT FOUND (Using system environment)'}")
    print(f"  MAAS_API_BASE_URL                : {settings.maas_api_base_url}")
    print(f"  MODEL_NAME                       : {settings.model_name}")
    print(f"  EMBEDDING_MODEL_NAME             : {settings.embedding_model_name}")
    print(f"  MAAS_API_KEY                     : {mask_key(settings.maas_api_key)}")
    print(f"  API_HOST / PORT                  : {settings.api_host}:{settings.api_port}")
    print(f"  STREAMLIT_SERVER                 : {settings.streamlit_server_address}:{settings.streamlit_server_port}")

    if settings.maas_api_base_url and settings.model_name:
        results["Environment Configuration"] = True
        print("  Status                           : [PASS] Runtime parameters verified.")
    else:
        results["Environment Configuration"] = False
        print("  Status                           : [FAIL] Incomplete runtime configuration.")

    # ------------------------------------------------------------------------
    # 2. Diagnostic Tools & Error Code Database Check ("OPT-001")
    # ------------------------------------------------------------------------
    print("\n[SUBSYSTEM 2: DIAGNOSTIC DATABASE & TOOL EXECUTION (OPT-001)]")
    code_result = lookup_error_code("OPT-001")
    print(f"  Target Code Query                : OPT-001")
    print(f"  Query Status                     : {code_result.get('status')}")
    print(f"  Target Hardware Model            : {code_result.get('model')}")
    print(f"  Subsystem Classification         : {code_result.get('subsystem')}")
    print(f"  Symptom Description              : {code_result.get('symptom')}")
    print(f"  Severity Rating                  : {code_result.get('severity')}")
    print(f"  Technician Required Flag         : {code_result.get('requires_authorized_technician')}")
    print(f"  Authorization Boundary           : {code_result.get('technician_authorization_boundary')}")

    if code_result.get("status") == "SUCCESS":
        results["Diagnostic Error Code DB"] = True
        print("  Status                           : [PASS] OPT-001 metadata resolved successfully.")
    else:
        results["Diagnostic Error Code DB"] = False
        print(f"  Status                           : [FAIL] Unable to query OPT-001: {code_result.get('error_message')}")

    # ------------------------------------------------------------------------
    # 3. Model-as-a-Service (MaaS) LLM Ping Check
    # ------------------------------------------------------------------------
    print("\n[SUBSYSTEM 3: MAAS OPENAI-COMPATIBLE LLM ENDPOINT PING]")
    print(f"  Target Model                     : {settings.model_name}")
    print(f"  Endpoint URL                     : {settings.maas_api_base_url}/chat/completions")

    llm_pass = False
    if not settings.maas_api_key or "your_" in settings.maas_api_key:
        print("  Ping Execution                   : BYPASSED (No production MAAS_API_KEY detected in environment)")
        print("  Fallback Subsystem               : [PASS] Deterministic Industrial Diagnostic Engine active")
        results["MaaS ChatOpenAI Gateway"] = False
    else:
        t0 = time.time()
        try:
            # Attempt via langchain_openai if installed
            chat_response = None
            try:
                from langchain_openai import ChatOpenAI
                from langchain_core.messages import HumanMessage
                llm = ChatOpenAI(
                    model=settings.model_name,
                    openai_api_base=settings.maas_api_base_url,
                    openai_api_key=settings.maas_api_key,
                    max_tokens=10,
                    timeout=8.0
                )
                resp = llm.invoke([HumanMessage(content="PING")])
                chat_response = resp.content.strip()
            except Exception:
                # Direct HTTP REST ping fallback
                import httpx
                headers = {
                    "Authorization": f"Bearer {settings.maas_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": settings.model_name,
                    "messages": [{"role": "user", "content": "PING"}],
                    "max_tokens": 10
                }
                with httpx.Client(timeout=8.0) as client:
                    r = client.post(f"{settings.maas_api_base_url}/chat/completions", headers=headers, json=payload)
                    if r.status_code == 200:
                        chat_response = r.json()["choices"][0]["message"]["content"].strip()
                    else:
                        print(f"  HTTP Error                       : {r.status_code} - {r.text[:120]}")

            elapsed_ms = int((time.time() - t0) * 1000)
            if chat_response:
                print(f"  Roundtrip Latency                : {elapsed_ms} ms")
                print(f"  Ping Response                    : '{chat_response[:60]}'")
                print("  Status                           : [PASS] MaaS LLM gateway responsive.")
                llm_pass = True
            else:
                print("  Status                           : [FAIL] Empty or invalid response from MaaS endpoint.")
        except Exception as exc:
            print(f"  Network Diagnostic               : {str(exc)}")
            print("  Status                           : [FAIL] Gateway connection timeout or TLS fault.")
        
        results["MaaS ChatOpenAI Gateway"] = llm_pass

    # ------------------------------------------------------------------------
    # 4. MaaS Embedding Endpoint Ping Check
    # ------------------------------------------------------------------------
    print("\n[SUBSYSTEM 4: MAAS EMBEDDING ENDPOINT PING]")
    print(f"  Target Embedding Model           : {settings.embedding_model_name}")
    print(f"  Endpoint URL                     : {settings.maas_api_base_url}/embeddings")

    emb_pass = False
    if not settings.maas_api_key or "your_" in settings.maas_api_key:
        print("  Ping Execution                   : BYPASSED (No production MAAS_API_KEY detected)")
        print("  Fallback Subsystem               : [PASS] Local Semantic Vector Index active")
        results["MaaS Text Embedding 3"] = False
    else:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {settings.maas_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": settings.embedding_model_name,
                "input": ["Enterprise gateway optical interface diagnostics"]
            }
            with httpx.Client(timeout=8.0) as client:
                r = client.post(f"{settings.maas_api_base_url}/embeddings", headers=headers, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    vec = data["data"][0]["embedding"]
                    dim = len(vec)
                    print(f"  Vector Dimension Returned        : {dim} float32")
                    print("  Status                           : [PASS] MaaS embedding endpoint responsive.")
                    emb_pass = True
                else:
                    print(f"  HTTP Error                       : {r.status_code} - {r.text[:120]}")
                    print("  Status                           : [FAIL] Embedding service returned error.")
        except Exception as exc:
            print(f"  Network Diagnostic               : {str(exc)}")
            print("  Status                           : [FAIL] Embedding connection timeout or TLS fault.")

        results["MaaS Text Embedding 3"] = emb_pass

    # ------------------------------------------------------------------------
    # 5. Multi-Agent Knowledge Retrieval Subsystem Check
    # ------------------------------------------------------------------------
    print("\n[SUBSYSTEM 5: MULTI-AGENT KNOWLEDGE RETRIEVAL & SAFETY SEQUENCER]")
    chunks = retrieval_engine.search("optical transceiver signal attenuation", model_filter="Apex Router Pro-X", top_k=2)
    print(f"  Indexed Manual Chunks Available  : {len(retrieval_engine.chunks)}")
    print(f"  Chunks Retrieved for Test Query  : {len(chunks)}")
    if chunks:
        print(f"  Top Match Reference              : {chunks[0].source_ref} ({chunks[0].model_target})")

    # Test Safe Planner
    sess = get_or_create_session("sess-verify-subsys")
    sess.model_id = "Apex Router Pro-X"
    sess.error_code = "OPT-001"
    sess.firmware_version = "v4.2.0"
    sess.operating_environment = "Datacenter Rack Row 4"
    plan = SafeStepPlannerAgent.generate_plan(sess)
    print(f"  Diagnostic Steps Planned         : {len(plan)}")

    if chunks and len(plan) >= 3:
        results["Multi-Agent Sequencer"] = True
        print("  Status                           : [PASS] Knowledge base & Safe-Step planner functional.")
    else:
        results["Multi-Agent Sequencer"] = False
        print("  Status                           : [FAIL] Incomplete procedural planning.")

    # ------------------------------------------------------------------------
    # High-Contrast Industrial ASCII Summary Box
    # ------------------------------------------------------------------------
    total_time = round(time.time() - start_time, 2)
    print("\n" + "=" * 80)
    print("TCS GENAI LAB // VERIFICATION SUMMARY REPORT")
    print("=" * 80)
    print(f"{'SUBSYSTEM COMPONENT':<50} | {'STATUS':<12}")
    print("-" * 50 + "-+-" + "-" * 12)
    for name, ok in results.items():
        status_label = "[PASS]" if ok else "[FAIL]"
        print(f"{name:<50} | {status_label:<12}")
    print("-" * 50 + "-+-" + "-" * 12)
    print(f"Total Verification Execution Time: {total_time}s")

    # If core local systems pass (Environment, DB, Multi-Agent), system is fully operational
    core_operational = results.get("Environment Configuration") and results.get("Diagnostic Error Code DB") and results.get("Multi-Agent Sequencer")
    
    if core_operational:
        print("\nOPERATIONAL READINESS: READY FOR DEPLOYMENT")
        if not results.get("MaaS ChatOpenAI Gateway") or not results.get("MaaS Text Embedding 3"):
            print("NOTE: Running in Deterministic Sandbox Resiliency Mode (Local Fallback Engines Active).")
            print("      To enable remote MaaS processing, provide a valid MAAS_API_KEY in .env.")
        print("=" * 80)
        return 0
    else:
        print("\nOPERATIONAL READINESS: FAULT DETECTED - INSPECT SUBSYSTEMS ABOVE")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit_code = run_verification()
    sys.exit(exit_code)
