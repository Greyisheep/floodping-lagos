"""Tools for FloodPing Lagos — see issue #1, #2.

Read vs. write are separate tools, given to separate agents (CHECKLIST §4 least privilege).
`get_flood_status` fuses citizen reports + a live rain signal into a dynamic freshness
window — the FUSION is code, not the LLM.
"""
from __future__ import annotations

from google.adk.tools import ToolContext

from floodping import data
from floodping.weather import effective_ttl_minutes, get_rain_signal

# Code-computed authoritative verdict (issue #4). The guard checks THIS field, not the
# model's prose — the safety call never depends on what the LLM happened to write.
_SEV_TO_VERDICT = {
    "passable": "passable",
    "ankle-level": "caution",
    "car-risk": "caution",
    "road-blocked": "blocked",
}


def _verdict(newest_report: dict | None, is_fresh: bool) -> str:
    if newest_report is None or not is_fresh:
        return "unknown"
    return _SEV_TO_VERDICT.get(newest_report["severity"], "unknown")


def get_flood_status(location: str, tool_context: ToolContext) -> dict:
    """Read-only: latest citizen flood reports for a Lagos location/route, fused with rain.

    Pass a NORMALIZED location (e.g. "Orchid Road, Lekki"). Freshness is dynamic: a report
    is only "fresh" within a window that SHRINKS when it's raining. Stashes the verdict into
    session state so the freshness guardrail can enforce safety even if the model disobeys
    (CHECKLIST §5 guardrails-as-code).
    """
    reports = data.get_reports(location)
    rain = get_rain_signal(location)
    ttl = effective_ttl_minutes(rain["rain_mm"])

    newest = min(reports, key=lambda r: r["minutes_ago"]) if reports else None
    newest_age = newest["minutes_ago"] if newest else None
    is_fresh = newest is not None and newest_age <= ttl
    verdict = _verdict(newest, is_fresh)

    tool_context.state["temp:flood_location"] = location
    tool_context.state["temp:flood_newest_age_min"] = newest_age
    tool_context.state["temp:flood_has_fresh"] = is_fresh
    tool_context.state["temp:flood_verdict"] = verdict
    tool_context.state["temp:flood_rain_mm"] = rain["rain_mm"]
    tool_context.state["temp:flood_is_raining"] = rain["is_raining"]

    return {
        "location": location,
        "reports": reports,
        "newest_report_age_minutes": newest_age,
        "is_fresh": is_fresh,
        "verdict": verdict,  # authoritative, code-computed (the guard checks this)
        "effective_ttl_minutes": ttl,
        "rain_mm": rain["rain_mm"],
        "is_raining": rain["is_raining"],
        "weather_source": rain["source"],
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
