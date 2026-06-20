"""FloodPing Lagos agent graph — see issue #1.

Shape (mirrors Dockie's hierarchical pattern):

    FloodPingRouter (root)               before_model_callback = flood_router_guard  (routing in CODE)
    ├── CheckAgent   read-only           after_model_callback  = freshness_guard     (safety in CODE)
    │     tool: get_flood_status
    └── ReportAgent  write
          tool: submit_report

The LLM is used ONLY for the fuzzy part: turning messy human text
("chevron roundabout side after orchid") into a normalized location. Routing and the
safety verdict are deterministic code.
"""
from __future__ import annotations

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from floodping.guardrails import flood_router_guard, freshness_guard
from floodping.tools import check_route, get_flood_status, lagos_flood_overview, submit_report

# gemini-3.5-flash (GA). Env-overridable so we can A/B against 2.5-flash live.
# Gemini 3.x notes (from Dockie's migration checklist):
#   - mandates temperature=1.0 (we set no temperature override -> fine)
#   - thought signatures on function-calling turns -> handled by google-adk 2.2
#   - tool params must have NO defaults (ours have none)
#   - catch google.genai.errors.ServerError for resilience (ADK catches ClientError)
MODEL = os.environ.get("FLOODPING_MODEL", "gemini-3.5-flash")


check_agent = LlmAgent(
    model=MODEL,
    name="CheckAgent",
    description="Tells a user whether a Lagos place, route, or the whole city is flooded.",
    instruction=(
        "You help Lagos residents with flooding, in a warm, natural, concise tone (a few sentences, "
        "not a form). First, normalize messy location text (e.g. 'chevron roundabout side after "
        "orchid' -> 'Orchid Road, Lekki'). Then pick the RIGHT tool:\n"
        "- A single place ('is Orchid Road flooded?') -> get_flood_status.\n"
        "- A journey ('from Yaba to Lekki', 'can I get to VGC from Ikeja?') -> check_route.\n"
        "- A city-wide question ('where is flooded in Lagos?', 'which areas are at risk?') -> "
        "lagos_flood_overview.\n"
        "Always keep two things SEPARATE: citizen REPORTS (ground truth — report_status / points / "
        "reported_flooding) and forecast PREDICTIONS (flash_flood_prediction / citywide risk — say "
        "explicitly these are forecasts, NOT confirmed reports). Mention rain only when relevant. "
        "Include any `advisory` only when the tool returns one. Never say a road is passable unless a "
        "fresh citizen report says so. Always end with a short, helpful reply."
    ),
    tools=[
        FunctionTool(func=get_flood_status),
        FunctionTool(func=check_route),
        FunctionTool(func=lagos_flood_overview),
    ],
    after_model_callback=freshness_guard,
)

report_agent = LlmAgent(
    model=MODEL,
    name="ReportAgent",
    description="Records a citizen flood report for a Lagos location.",
    instruction=(
        "The user is reporting flooding. Extract the location and a severity, one of: "
        "passable, ankle-level, car-risk, road-blocked. If severity is unclear, ask a short "
        "clarifying question. Then call submit_report and confirm with a brief thank-you."
    ),
    tools=[FunctionTool(func=submit_report)],
)

root_agent = LlmAgent(
    model=MODEL,
    name="FloodPingRouter",
    description="Routes Lagos flood queries to the check or report specialist.",
    instruction=(
        "You coordinate a flood assistant for Lagos. A deterministic guard handles routing "
        "before you are normally invoked. If you must decide: a question about whether a "
        "road/route is flooded or passable -> transfer to CheckAgent; a statement reporting "
        "flooding -> transfer to ReportAgent."
    ),
    sub_agents=[check_agent, report_agent],
    before_model_callback=flood_router_guard,
)
