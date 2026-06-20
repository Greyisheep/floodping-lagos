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

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from floodping.guardrails import flood_router_guard, freshness_guard
from floodping.tools import get_flood_status, submit_report

# gemini-2.5-flash: stable, cheap, consistent latency — same rationale as Dockie's
# orchestrator (production rate limits, no preview deprecations, temperature flexibility).
MODEL = "gemini-2.5-flash"


check_agent = LlmAgent(
    model=MODEL,
    name="CheckAgent",
    description="Tells a user whether a Lagos street/route is flooded right now.",
    instruction=(
        "The user wants to know if a Lagos location or route is flooded right now.\n"
        "1. Extract and NORMALIZE the location from their (often messy) text, e.g. "
        "'chevron roundabout side after orchid' -> 'Orchid Road, Lekki'.\n"
        "2. Call get_flood_status with the normalized location.\n"
        "3. Relay ONLY what the tool returns: latest severity, how many minutes old the "
        "newest report is, and the official warning.\n"
        "Never claim a road is passable or clear on your own — only relay tool data. "
        "If there is no recent report, say it is unknown and advise caution."
    ),
    tools=[FunctionTool(func=get_flood_status)],
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
