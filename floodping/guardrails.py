"""Deterministic routing + the freshness safety guardrail — see issue #1.

This file is the heart of the talk:
  * `classify_intent` / `flood_router_guard` — routing is CODE, not an LLM call
    (CHECKLIST §2). Modeled on Dockie's `orchestrator_before_model_guard`.
  * `should_block_passable` / `freshness_guard` — safety is CODE, not the prompt
    (CHECKLIST §5). Modeled on Dockie's `advisory_price_guard` (after_model).

Pure helpers (no ADK/genai objects) are separated so they unit-test with no API key.
"""
from __future__ import annotations

import re
from typing import Any, Optional

try:  # real ADK at runtime; fallbacks let pure helpers be tested without google libs
    from google.adk.models import LlmResponse
    from google.genai import types as genai_types
except Exception:  # pragma: no cover
    genai_types = None

    class LlmResponse:  # type: ignore[no-redef]
        def __init__(self, content: Any = None):
            self.content = content


# --------------------------------------------------------------------------- #
# 1. Deterministic router (CHECKLIST §2)
# --------------------------------------------------------------------------- #

REPORT_SIGNALS = (
    "report",
    "reporting",
    "i'm reporting",
    "flooding at",
    "flooded at",
    "there is flood",
    "there's flood",
    "submit",
    "log a flood",
)

CHECK_SIGNALS = (
    "is ",
    "can i pass",
    "can i go",
    "passable",
    "flooded",
    "flooding",
    "is there flood",
    "any flood",
    "route",
    "road clear",
    "is the road",
    "how is",
    "how's",
)


def classify_intent(text: str) -> Optional[str]:
    """Return 'report', 'check', or None (defer to the LLM). Pure + testable."""
    lower = (text or "").lower().strip()
    if not lower:
        return None
    # Report wins when an explicit reporting verb is present.
    if any(sig in lower for sig in REPORT_SIGNALS):
        return "report"
    if any(sig in lower for sig in CHECK_SIGNALS):
        return "check"
    return None


def _last_user_text(llm_request: Any) -> str:
    try:
        for content in reversed(getattr(llm_request, "contents", None) or []):
            if getattr(content, "role", None) != "user":
                continue
            for part in reversed(getattr(content, "parts", []) or []):
                if getattr(part, "text", None):
                    return part.text
    except Exception:
        pass
    return ""


def _transfer(agent_name: str) -> Any:
    """Synthetic transfer_to_agent response — skips the routing LLM call entirely."""
    if genai_types is None:  # pragma: no cover
        return LlmResponse(content={"transfer_to_agent": agent_name})
    return LlmResponse(
        content=genai_types.Content(
            role="model",
            parts=[
                genai_types.Part(
                    function_call=genai_types.FunctionCall(
                        name="transfer_to_agent", args={"agent_name": agent_name}
                    )
                )
            ],
        )
    )


def flood_router_guard(callback_context: Any, llm_request: Any) -> Optional[Any]:
    """before_model_callback on the root agent: route in code, skip the LLM for ~all traffic."""
    intent = classify_intent(_last_user_text(llm_request))
    if intent == "report":
        return _transfer("ReportAgent")
    if intent == "check":
        return _transfer("CheckAgent")
    return None  # genuinely ambiguous -> let the LLM decide (the rare tail)


# --------------------------------------------------------------------------- #
# 2. Freshness safety guardrail (CHECKLIST §5) — the star
# --------------------------------------------------------------------------- #

# Phrases where the model is asserting the road is fine.
_PASSABLE_RE = re.compile(
    r"\b(passable|clear|you can pass|safe to (?:pass|drive|go)|good to go|no flood(?:ing)?|"
    r"not flooded|free to drive)\b",
    re.IGNORECASE,
)


def should_block_passable(response_text: str, has_fresh_report: bool) -> bool:
    """True if the model claims 'passable/clear' but there is NO fresh report. Pure + testable."""
    if has_fresh_report:
        return False
    return bool(_PASSABLE_RE.search(response_text or ""))


def _extract_text(llm_response: Any) -> str:
    content = getattr(llm_response, "content", None)
    if not content:
        return ""
    parts = getattr(content, "parts", None) or []
    return "".join(p.text for p in parts if getattr(p, "text", None)).strip()


def _text_response(text: str) -> Any:
    if genai_types is None:  # pragma: no cover
        return LlmResponse(content={"text": text})
    return LlmResponse(
        content=genai_types.Content(role="model", parts=[genai_types.Part(text=text)])
    )


def freshness_guard(callback_context: Any, llm_response: Any) -> Optional[Any]:
    """after_model_callback on CheckAgent: override any 'passable' claim that lacks a fresh report.

    The model is *not allowed* to tell someone a road is clear unless a recent verified
    report backs it. This is enforced here in code, regardless of what the model wrote.
    """
    try:
        state = callback_context.state
        has_fresh = bool(state.get("temp:flood_has_fresh", False))
        text = _extract_text(llm_response)
        if not text or not should_block_passable(text, has_fresh):
            return None

        location = state.get("temp:flood_location") or "that route"
        age = state.get("temp:flood_newest_age_min")
        age_str = f"the newest report is {age} min old" if age is not None else "there are no reports"
        raining = bool(state.get("temp:flood_is_raining"))
        rain_note = "it's raining and " if raining else ""
        from floodping import data

        safe = (
            f"⚠️ Unknown for {location} — {rain_note}{age_str}, so I can't confirm it's passable. "
            f"Do not assume it's clear. {data.OFFICIAL_WARNING}"
        )
        return _text_response(safe)
    except Exception:  # never fail the turn because a guard failed (CHECKLIST §6)
        return None
