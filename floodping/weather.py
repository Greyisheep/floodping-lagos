"""Live weather signal — see issue #2, #8.

Weather is a SIGNAL, not ground truth. It feeds two things, both kept distinct from
citizen REPORTS:
  (a) the dynamic freshness window, and
  (b) the flash-flood PREDICTION (current + forecast rain).

Provider-agnostic with failover (CHECKLIST §6): Google Weather (key) -> Open-Meteo (no key)
-> graceful 'unknown'. The 6h forecast comes from Open-Meteo hourly. Never raises.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from floodping import data

RAIN_THRESHOLD_MM = 0.2            # current rain at/above this = "raining now"
FORECAST_THRESHOLD_MM = 2.0       # >= this total over the next 6h = "rain expected"
RAIN_TTL_MINUTES = 20
DRY_TTL_MINUTES = 90
UNKNOWN_TTL_MINUTES = data.FRESHNESS_TTL_MINUTES
_TIMEOUT_S = 4


def effective_ttl_minutes(rain_mm: float | None) -> int:
    """Freshness is a FUNCTION of weather, not a constant (CHECKLIST §3). Pure + testable."""
    if rain_mm is None:
        return UNKNOWN_TTL_MINUTES
    return RAIN_TTL_MINUTES if rain_mm >= RAIN_THRESHOLD_MM else DRY_TTL_MINUTES


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "floodping/0.1"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
        return json.load(resp)


def _google_current(lat: float, lon: float, key: str) -> float:
    url = "https://weather.googleapis.com/v1/currentConditions:lookup?" + urllib.parse.urlencode(
        {"key": key, "location.latitude": lat, "location.longitude": lon}
    )
    p = _get_json(url)
    return float(p.get("precipitation", {}).get("qpf", {}).get("quantity", 0.0) or 0.0)


def _open_meteo_current(lat: float, lon: float) -> float:
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
        {"latitude": lat, "longitude": lon, "current": "rain,precipitation"}
    )
    cur = _get_json(url).get("current", {})
    return float(cur.get("rain", cur.get("precipitation", 0.0)) or 0.0)


def _forecast_6h(lat: float, lon: float) -> float:
    """Total forecast precipitation over the next 6 hours (Open-Meteo, no key)."""
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
        {"latitude": lat, "longitude": lon, "hourly": "precipitation", "forecast_hours": 6}
    )
    precip = _get_json(url).get("hourly", {}).get("precipitation", []) or []
    return float(sum(x for x in precip[:6] if x is not None))


def get_rain_signal(location: str) -> dict:
    """Return {rain_mm, is_raining, forecast_6h_mm, rain_expected, source}. Never raises (CHECKLIST §6)."""
    from floodping.geocode import resolve_coords

    # Stage knob: deterministic rain (current + forecast) for the live demo.
    override = os.environ.get("FLOODPING_DEMO_RAIN_MM")
    if override is not None:
        try:
            mm = float(override)
        except ValueError:
            mm = 0.0
        return {
            "rain_mm": mm,
            "is_raining": mm >= RAIN_THRESHOLD_MM,
            "forecast_6h_mm": mm * 6,
            "rain_expected": mm >= RAIN_THRESHOLD_MM,
            "source": "demo-override",
        }

    lat, lon = resolve_coords(location)
    key = os.environ.get("GOOGLE_WEATHER_API_KEY")

    rain_mm, source = None, "unavailable"
    providers = ([("google-weather", lambda: _google_current(lat, lon, key))] if key else [])
    providers.append(("open-meteo", lambda: _open_meteo_current(lat, lon)))
    for src, fetch in providers:
        try:
            rain_mm = fetch()
            source = src
            break
        except Exception:
            continue

    forecast = None
    try:
        forecast = _forecast_6h(lat, lon)
    except Exception:
        pass

    return {
        "rain_mm": rain_mm,
        "is_raining": rain_mm is not None and rain_mm >= RAIN_THRESHOLD_MM,
        "forecast_6h_mm": forecast,
        "rain_expected": forecast is not None and forecast >= FORECAST_THRESHOLD_MM,
        "source": source,
    }
