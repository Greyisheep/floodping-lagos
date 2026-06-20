"""Tools for FloodPing Lagos — see issue #1, #2.

Read vs. write are separate tools, given to separate agents (CHECKLIST §4 least privilege).
`get_flood_status` fuses citizen reports + a live rain signal into a dynamic freshness
window — the FUSION is code, not the LLM.
"""
from __future__ import annotations

from google.adk.tools import ToolContext

from floodping import data, notifications
from floodping.weather import FORECAST_THRESHOLD_MM, effective_ttl_minutes, get_rain_signal

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


def _flood_prediction(rain_now: float | None, forecast_mm: float | None, prone: bool) -> str:
    """Forecast-based flash-flood risk (NOT a citizen report): likely / possible / unlikely."""
    heavy_now = rain_now is not None and rain_now >= 2.0
    heavy_soon = forecast_mm is not None and forecast_mm >= 5.0
    some = (rain_now is not None and rain_now >= 0.5) or (
        forecast_mm is not None and forecast_mm >= FORECAST_THRESHOLD_MM
    )
    if (heavy_now or heavy_soon) and prone:
        return "likely"
    if heavy_now or heavy_soon or (some and prone):
        return "possible"
    return "unlikely"


def get_flood_status(location: str, tool_context: ToolContext) -> dict:
    """Read-only: latest citizen flood reports for a Lagos location/route, fused with rain.

    Pass a NORMALIZED location (e.g. "Orchid Road, Lekki"). Freshness is dynamic: a report
    is only "fresh" within a window that SHRINKS when it's raining. Stashes the verdict into
    session state so the freshness guardrail can enforce safety even if the model disobeys
    (CHECKLIST §5 guardrails-as-code).
    """
    reports = data.get_reports(location)
    w = get_rain_signal(location)
    ttl = effective_ttl_minutes(w["rain_mm"])

    newest = min(reports, key=lambda r: r["minutes_ago"]) if reports else None
    newest_age = newest["minutes_ago"] if newest else None
    is_fresh = newest is not None and newest_age <= ttl
    verdict = _verdict(newest, is_fresh)

    prone = data.is_flood_prone(location)
    prediction = _flood_prediction(w["rain_mm"], w["forecast_6h_mm"], prone)
    at_risk = prediction in ("likely", "possible") or w["is_raining"] or w["rain_expected"]
    advisory = data.OFFICIAL_WARNING if at_risk else None

    tool_context.state["temp:flood_location"] = location
    tool_context.state["temp:flood_newest_age_min"] = newest_age
    tool_context.state["temp:flood_has_fresh"] = is_fresh
    tool_context.state["temp:flood_verdict"] = verdict
    tool_context.state["temp:flood_rain_mm"] = w["rain_mm"]
    tool_context.state["temp:flood_is_raining"] = w["is_raining"]
    tool_context.state["temp:flood_prediction"] = prediction

    return {
        "location": location,
        # --- citizen REPORTS (ground truth) ---
        "citizen_reports": reports,
        "newest_report_age_minutes": newest_age,
        "report_status": verdict,
        "is_fresh": is_fresh,
        # --- weather signal ---
        "current_rain_mm": w["rain_mm"],
        "is_raining": w["is_raining"],
        "forecast_rain_6h_mm": w["forecast_6h_mm"],
        "rain_expected": w["rain_expected"],
        "weather_source": w["source"],
        # --- model PREDICTION (forecast-based, NOT a report) ---
        "flash_flood_prediction": prediction,
        "flood_prone_area": prone,
        # surfaced ONLY when there is real risk (keeps replies natural)
        "advisory": advisory,
    }


def submit_report(location: str, severity: str, tool_context: ToolContext) -> dict:
    """Write + broadcast a citizen flood report.

    Reports are NEVER blocked. Vetting only annotates a `possibility` level (low/medium/high)
    from the weather/forecast — a low-possibility report is still recorded and still broadcast
    to everyone on the page, just labelled low. An unclear severity is coerced, not rejected.
    """
    sev = (severity or "").strip().lower()
    if sev not in data.SEVERITY_LEVELS:
        sev = "car-risk"  # coerce rather than reject — never block a citizen report
    report = data.add_report(location, sev)

    # Vetting (plausibility), NOT a gate: does current/forecast weather support this report?
    w = get_rain_signal(location)
    prediction = _flood_prediction(w["rain_mm"], w["forecast_6h_mm"], data.is_flood_prone(location))
    possibility = {"likely": "high", "possible": "medium", "unlikely": "low"}[prediction]

    notifications.broadcast(
        {"type": "report", "location": location, "severity": sev, "possibility": possibility}
    )
    tool_context.state["temp:last_report_location"] = location
    return {"ok": True, "location": location, "recorded": report, "possibility": possibility}
