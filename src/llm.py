"""
llm.py  -  Unified LLM Gateway (TCS GenAI Lab MaaS & OpenAI-Compatible REST API)

Provides:
  - set_llm_enabled(enabled: bool)
  - llm_available() -> bool
  - ask_llm(system_prompt, user_prompt)
  - run_agent(system_prompt, user_prompt, max_rounds=5)
"""

from __future__ import annotations

import json
from typing import Any, Optional
import requests

from src.config import settings

_llm_enabled = True


def set_llm_enabled(enabled: bool) -> None:
    """Turn the LLM on/off for the whole program (used by evaluation.py)."""
    global _llm_enabled
    _llm_enabled = enabled


def llm_is_configured() -> bool:
    """Check if API key is present and not dummy placeholder."""
    key = settings.maas_api_key.strip()
    return bool(key and key != "your_tcs_genai_lab_api_key_here")


def llm_available() -> bool:
    """True when we have an active API key AND nobody switched the LLM off."""
    return _llm_enabled and llm_is_configured()


def _call_llm(messages: list[dict], tools: Optional[list[dict]] = None) -> dict[str, Any]:
    """Make ONE request to the chat completions API and return the assistant's message."""
    payload: dict[str, Any] = {
        "model": settings.model_name,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 800,
    }
    if tools:
        payload["tools"] = tools

    headers = {
        "Authorization": f"Bearer {settings.maas_api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        f"{settings.maas_api_base_url}/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
        verify=False if "genailab.tcs.in" in settings.maas_api_base_url else True,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]


def ask_llm(system_prompt: str, user_prompt: str) -> Optional[str]:
    """Simple question -> answer with offline fallback."""
    if not llm_available():
        return None
    try:
        message = _call_llm(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        )
        return (message.get("content") or "").strip() or None
    except Exception as error:
        return None


def run_agent(system_prompt: str, user_prompt: str, max_rounds: int = 5) -> tuple[Optional[str], list[dict]]:
    """Tool-calling agent loop with offline fallback."""
    if not llm_available():
        return None, []

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    tool_log: list[dict] = []

    try:
        from src.tools import lookup_error_code, search_manual

        for _ in range(max_rounds):
            message = _call_llm(messages)
            tool_calls = message.get("tool_calls")
            if not tool_calls:
                return (message.get("content") or "").strip() or None, tool_log

            messages.append(message)
            for call in tool_calls:
                name = call["function"]["name"]
                try:
                    args = json.loads(call["function"]["arguments"] or "{}")
                except Exception:
                    args = {}

                if name == "lookup_error_code":
                    res = lookup_error_code(args.get("code", ""))
                elif name == "search_manual":
                    res = search_manual(args.get("query", ""), args.get("product"))
                else:
                    res = {"status": "TOOL_NOT_FOUND"}

                tool_log.append({"tool": name, "arguments": args, "result": res})
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(res)[:4000],
                })
        return None, tool_log
    except Exception:
        return None, tool_log
