"""Tools for FloodPing Lagos — see issue #1.

Read vs. write are deliberately separate tools, given to separate agents
(CHECKLIST §4 least privilege): the checker can only read; only the reporter can write.
"""
from __future__ import annotations

from google.adk.tools import ToolContext

from floodping import data


def get_flood_status(location: str, tool_context: ToolContext) -> dict:
    """Read-only: latest citizen flood reports for a Lagos location/route.

    Pass a NORMALIZED location (e.g. "Orchid Road, Lekki"). Returns recent reports,
    the age of the newest one, whether it is fresh, and the official warning.

    Also stashes freshness into session state so the freshness guardrail can enforce
    safety even if the model ignores instructions (CHECKLIST §5 guardrails-as-code).
    """
    reports = data.get_reports(location)
    newest_age = min((r["minutes_ago"] for r in reports), default=None)
    is_fresh = newest_age is not None and newest_age <= data.FRESHNESS_TTL_MINUTES

    # Stash for the after_model freshness guard (mirrors Dockie's price_guard reading state).
    tool_context.state["temp:flood_location"] = location
    tool_context.state["temp:flood_newest_age_min"] = newest_age
    tool_context.state["temp:flood_has_fresh"] = is_fresh

    return {
        "location": location,
        "reports": reports,
        "newest_report_age_minutes": newest_age,
        "is_fresh": is_fresh,
        "freshness_ttl_minutes": data.FRESHNESS_TTL_MINUTES,
        "official_warning": data.OFFICIAL_WARNING,
    }


def submit_report(location: str, severity: str, tool_context: ToolContext) -> dict:
    """Write: record a citizen flood report.

    `severity` must be one of: passable, ankle-level, car-risk, road-blocked.
    Invalid severities are rejected (CHECKLIST §4 — validate writes).
    """
    sev = (severity or "").strip().lower()
    if sev not in data.SEVERITY_LEVELS:
        return {
            "ok": False,
            "error": f"invalid severity '{severity}'",
            "allowed": list(data.SEVERITY_LEVELS),
        }
    report = data.add_report(location, sev)
    tool_context.state["temp:last_report_location"] = location
    return {"ok": True, "location": location, "recorded": report}
