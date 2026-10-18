"""
evaluation.py  -  Automated 4-Dimension Quality Benchmark & Evaluation Suite

Tests 4 key dimensions:
  1. Multi-Tier Retrieval Hit Rate (3-Factor Re-Ranking across manuals, bulletins, known issues, escalation rules)
  2. LangChain Entity Extraction (Symptoms, Model, Version, Operating Conditions)
  3. Tool Correctness (Error code database, checklists, fallbacks)
  4. Safety, Memory & Handover (Deterministic safety gates, diagnostic memory, loop prevention, escalation packages)
"""

from __future__ import annotations

import json
from typing import Any

from src.config import TEST_CASES_PATH
from src.extractor import extract_diagnostic_entities
from src.llm import set_llm_enabled
from src.rag import get_knowledge_base
from src.service import report_result, start_case
from src.tools import list_products, load_error_db, lookup_error_code


# ----------------------------------------------------------------------------
# 1. RETRIEVAL & RE-RANKING EVALUATION
# ----------------------------------------------------------------------------
def evaluate_retrieval(tests: list[dict]) -> dict:
    kb = get_knowledge_base()
    details = []
    for test in tests:
        hits = kb.search(test["query"], product=test["product"])
        found_ids = [hit["id"] for hit in hits]
        passed = bool(set(found_ids) & set(test["expected_any"]))
        details.append({
            "test": f"{test['product'][:30]}... // \"{test['query'][:40]}\"",
            "expected": test["expected_any"],
            "got": found_ids,
            "passed": passed,
        })
    return _summarise("Multi-Tier Retrieval Hit Rate", details)


# ----------------------------------------------------------------------------
# 2. ENTITY EXTRACTION EVALUATION
# ----------------------------------------------------------------------------
def evaluate_extraction(tests: list[dict]) -> dict:
    details = []
    products = list_products()
    for test in tests:
        extracted = extract_diagnostic_entities(raw_text=test["input"], supported_products=products)
        data = extracted.to_dict()

        passed = True
        if "expected_model" in test and data.get("device_model") != test["expected_model"]:
            passed = False
        if "expected_version" in test and data.get("software_version") != test["expected_version"]:
            passed = False
        if "expected_code" in test and data.get("error_code") != test["expected_code"]:
            passed = False
        if "expected_condition_key" in test and test["expected_condition_key"] not in data.get("operating_conditions", {}):
            passed = False

        details.append({
            "test": f"Entity Extraction // \"{test['input'][:45]}...\"",
            "expected": {k: v for k, v in test.items() if k.startswith("expected_")},
            "got": {
                "model": data.get("device_model"),
                "version": data.get("software_version"),
                "code": data.get("error_code"),
                "conditions": data.get("operating_conditions"),
            },
            "passed": passed,
        })
    return _summarise("LangChain Entity Extraction", details)


# ----------------------------------------------------------------------------
# 3. TOOL CORRECTNESS EVALUATION
# ----------------------------------------------------------------------------
def evaluate_tools(tests: list[dict]) -> dict:
    details = []
    for test in tests:
        result = lookup_error_code(test["code"])
        passed = result["found"] == test["expect_found"]
        if passed and test["expect_found"]:
            passed = result["product"] == test["expect_product"]
        details.append({
            "test": f"lookup_error_code({test['code']!r})",
            "expected": test["expect_found"],
            "got": result["found"],
            "passed": passed,
        })
    return _summarise("Tool Correctness", details)


# ----------------------------------------------------------------------------
# 4. SAFETY, MEMORY & ESCALATION EVALUATION
# ----------------------------------------------------------------------------
def _check_safety_for_code(code: str, record: dict) -> tuple[bool, str]:
    """Simulate user experiencing failures at every step to verify safety stop and dossier."""
    model_name = record.get("model") or record.get("model_id")
    case = start_case(product=model_name, symptom="appliance malfunction", error_code=code)
    session_id = case["session_id"]

    safety_ok, sources_ok, guard = True, True, 0
    seen_actions: set[str] = set()
    no_repeat_ok = True

    while case["status"] == "IN_PROGRESS" and guard < 20:
        step = case.get("current_step")
        if not step:
            break
        if step.get("is_stop_step"):
            safety_ok = False

        if not step.get("source"):
            sources_ok = False

        action_text = step["text"].strip().lower()
        if action_text in seen_actions:
            no_repeat_ok = False
        seen_actions.add(action_text)

        case = report_result(session_id, "not_fixed", "Tested: still failing.")
        guard += 1

    ended_escalated = case["status"] == "ESCALATED"
    has_record = bool(case.get("record")) and bool(case["record"].get("ticket_id")) and bool(case["record"].get("ticket_markdown"))
    passed = safety_ok and sources_ok and ended_escalated and has_record and no_repeat_ok
    why = "" if passed else (
        f"safe={safety_ok}, sources={sources_ok}, escalated={ended_escalated}, record={has_record}, no_repeat={no_repeat_ok}"
    )
    return passed, why


def evaluate_safety() -> dict:
    details = []
    db = load_error_db()
    for code, record in db.items():
        passed, why = _check_safety_for_code(code, record)
        details.append({
            "test": f"Safety & Memory for {code}",
            "expected": "Escalate safely + Handover Package + No Repeated Steps",
            "got": why or "Passed",
            "passed": passed,
        })

    # Happy path: Fixed at step 1 gives RESOLVED with Resolution Package
    first_code, first_record = next(iter(db.items()))
    case = start_case(first_record.get("model", first_record.get("model_id")), "appliance symptom", first_code)
    case = report_result(case["session_id"], "fixed", "Resolved by user verification.")
    happy_passed = case["status"] == "RESOLVED" and bool(case.get("record"))
    details.append({
        "test": f"Happy path ({first_code}): fixed at step 1",
        "expected": "RESOLVED with Certificate",
        "got": case["status"],
        "passed": happy_passed,
    })
    return _summarise("Safety, Memory & Handover", details)


# ----------------------------------------------------------------------------
# Helpers & Main
# ----------------------------------------------------------------------------
def _summarise(name: str, details: list[dict]) -> dict:
    passed = sum(1 for d in details if d["passed"])
    total = len(details)
    return {
        "name": name,
        "passed": passed,
        "total": total,
        "score_percent": round(100 * passed / total, 1) if total else 0.0,
        "details": details,
    }


def run_evaluation() -> dict:
    cases = json.loads(TEST_CASES_PATH.read_text(encoding="utf-8"))
    set_llm_enabled(False)
    try:
        groups = [
            evaluate_retrieval(cases["retrieval_tests"]),
            evaluate_extraction(cases.get("extraction_tests", [])),
            evaluate_tools(cases["tool_tests"]),
            evaluate_safety(),
        ]
    finally:
        set_llm_enabled(True)

    total_passed = sum(g["passed"] for g in groups)
    total = sum(g["total"] for g in groups)
    return {
        "search_mode": get_knowledge_base().mode,
        "overall_percent": round(100 * total_passed / total, 1),
        "groups": groups,
    }


if __name__ == "__main__":
    report = run_evaluation()
    print(f"\nSearch mode: {report['search_mode']}\n")
    for group in report["groups"]:
        print(f"{group['name']:<32} {group['passed']}/{group['total']}  ({group['score_percent']}%)")
        for d in group["details"]:
            if not d["passed"]:
                print(f"   FAILED: {d['test']}  expected={d['expected']}  got={d['got']}")
    print(f"\nOVERALL SCORE: {report['overall_percent']}%")
