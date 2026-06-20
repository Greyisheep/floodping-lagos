"""Live rain signal — see issue #2.

Weather is a SIGNAL, not ground truth: it tells us it's raining, not that a street is
flooded. It feeds the *dynamic freshness window* — it never declares a road flooded by itself.

Provider-agnostic with failover (CHECKLIST §6): Google Weather API (key present) ->
Open-Meteo (no key) -> graceful "unknown". Never raises.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from floodping import data

RAIN_THRESHOLD_MM = 0.2          # qpf/rain at or above this counts as "raining now"
RAIN_TTL_MINUTES = 20            # a report goes stale fast in rain
DRY_TTL_MINUTES = 90             # ...and stays valid longer when dry
UNKNOWN_TTL_MINUTES = data.FRESHNESS_TTL_MINUTES  # weather unavailable -> 45 default
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


def _google_weather(lat: float, lon: float, key: str) -> float:
    url = "https://weather.googleapis.com/v1/currentConditions:lookup?" + urllib.parse.urlencode(
        {"key": key, "location.latitude": lat, "location.longitude": lon}
    )
    payload = _get_json(url)
    return float(payload.get("precipitation", {}).get("qpf", {}).get("quantity", 0.0) or 0.0)


def _open_meteo(lat: float, lon: float) -> float:
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
        {"latitude": lat, "longitude": lon, "current": "rain,precipitation"}
    )
    cur = _get_json(url).get("current", {})
    return float(cur.get("rain", cur.get("precipitation", 0.0)) or 0.0)


def get_rain_signal(location: str) -> dict:
    """Return {rain_mm, is_raining, source}. Never raises (CHECKLIST §6)."""
    # Stage knob: deterministic rain for the live demo, regardless of real weather.
    override = os.environ.get("FLOODPING_DEMO_RAIN_MM")
    if override is not None:
        try:
            mm = float(override)
        except ValueError:
            mm = 0.0
        return {"rain_mm": mm, "is_raining": mm >= RAIN_THRESHOLD_MM, "source": "demo-override"}

    lat, lon = data.get_coords(location)
    key = os.environ.get("GOOGLE_WEATHER_API_KEY")

    providers = []
    if key:
        providers.append(("google-weather", lambda: _google_weather(lat, lon, key)))
    providers.append(("open-meteo", lambda: _open_meteo(lat, lon)))  # failover, no key

    for source, fetch in providers:
        try:
            mm = fetch()
            return {"rain_mm": mm, "is_raining": mm >= RAIN_THRESHOLD_MM, "source": source}
        except Exception:
            continue  # try the next provider
    return {"rain_mm": None, "is_raining": False, "source": "unavailable"}
