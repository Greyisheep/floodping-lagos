"""Geocoding — see issue #5.

Resolve a messy Lagos place name to lat/lon via Google Geocoding (the Maps-enabled key),
so the weather signal is accurate for ANY location, not just the seeded ones. This is what
actually uses the Maps API key. Cached in-process; never raises (CHECKLIST §6).
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from floodping import data

_TIMEOUT_S = 4
_cache: dict[str, tuple[float, float]] = {}


def resolve_coords(location: str) -> tuple[float, float]:
    """Seeded known areas → Google Geocoding (Maps key) → Lagos centroid fallback."""
    key = data._resolve_key(location)
    if key and key in data.LOCATION_COORDS:
        return data.LOCATION_COORDS[key]

    norm = data.normalize_location(location)
    if not norm:
        return data.DEFAULT_COORDS
    if norm in _cache:
        return _cache[norm]

    maps_key = os.environ.get("GOOGLE_WEATHER_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY")
    if maps_key:
        try:
            q = urllib.parse.quote(f"{location}, Lagos, Nigeria")
            url = f"https://maps.googleapis.com/maps/api/geocode/json?address={q}&key={maps_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "floodping/0.1"})
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
                payload = json.load(resp)
            if payload.get("status") == "OK" and payload.get("results"):
                loc = payload["results"][0]["geometry"]["location"]
                coords = (float(loc["lat"]), float(loc["lng"]))
                _cache[norm] = coords
                return coords
        except Exception:
            pass  # fall through to default

    return data.DEFAULT_COORDS
