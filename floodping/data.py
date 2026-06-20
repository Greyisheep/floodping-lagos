"""Stub data layer for FloodPing Lagos — see issue #1, #2.

In production this is a Postgres/PostGIS query over citizen reports + geocoding
(CHECKLIST §3 freshness, §7 scalability). For the workshop the data is stubbed so the
*guardrail* and the *fusion logic* are the stars, not a live feed.

Report ages are explicit `minutes_ago` so behaviour is deterministic and testable.
"""
from __future__ import annotations

# Controlled vocabulary for severity (CHECKLIST §4 — write tools validate inputs).
SEVERITY_LEVELS = ("passable", "ankle-level", "car-risk", "road-blocked")

# Default freshness TTL used only when weather is unknown. The live TTL is dynamic and
# computed from the rain signal (see floodping/weather.py: effective_ttl_minutes).
FRESHNESS_TTL_MINUTES = 45

# Official, citable warning (NiMet, June 2026). Always shown alongside citizen data.
OFFICIAL_WARNING = (
    "NiMet (June 2026): Lagos is among 19 states flagged for flash-flood risk; "
    "motorists are advised not to drive through flooded roads."
)

# Seed reports keyed by normalized location.
#   - "orchid road, lekki":      FRESH passable (8m)
#   - "admiralty road, lekki":   FRESH car-risk (12m)
#   - "lekki-epe expressway":    FRESH road-blocked (30m)
#   - "ozumba mbadiwe, ...":     passable @ 35m  -> FRESH when dry (TTL 90), STALE in rain (TTL 20)
#                                 => the "rain flip" demo: guard fires only when raining
#   - "ikorodu road":            passable @ 190m -> always stale -> guard refuses "passable"
_SEED_REPORTS: dict[str, list[dict]] = {
    "orchid road, lekki": [{"severity": "passable", "minutes_ago": 8, "source": "citizen"}],
    "admiralty road, lekki": [{"severity": "car-risk", "minutes_ago": 12, "source": "citizen"}],
    "lekki-epe expressway": [{"severity": "road-blocked", "minutes_ago": 30, "source": "citizen"}],
    "ozumba mbadiwe, victoria island": [
        {"severity": "passable", "minutes_ago": 35, "source": "citizen"}
    ],
    "ikorodu road": [{"severity": "passable", "minutes_ago": 190, "source": "citizen"}],
}

# Approx lat/lon per seeded area (prod: Google Geocoding, like Dockie). Default = Lagos.
LOCATION_COORDS: dict[str, tuple[float, float]] = {
    "orchid road, lekki": (6.4419, 3.5430),
    "admiralty road, lekki": (6.4431, 3.4780),
    "lekki-epe expressway": (6.4660, 3.5680),
    "ozumba mbadiwe, victoria island": (6.4281, 3.4219),
    "ikorodu road": (6.5790, 3.3680),
}
DEFAULT_COORDS = (6.4541, 3.3947)  # Lagos

# Mutable in-memory store seeded from the constants (submit_report appends here).
# NOTE: per-instance memory is fine for the demo but is NOT the source of truth —
# see CHECKLIST §7 (stateless instances) before scaling beyond one container.
_REPORTS: dict[str, list[dict]] = {k: list(v) for k, v in _SEED_REPORTS.items()}


def normalize_location(location: str) -> str:
    """Cheap normalization. The fuzzy parse ('chevron roundabout side after orchid'
    -> 'Orchid Road, Lekki') is the LLM's job; this just canonicalizes the key."""
    return " ".join((location or "").strip().lower().split())


def _resolve_key(location: str) -> str | None:
    """Forgiving location match — real-world location text is fuzzy.
    Exact, then substring either way ('orchid road' ~ 'orchid road, lekki'),
    then token-subset."""
    key = normalize_location(location)
    if not key:
        return None
    if key in _REPORTS:
        return key
    for k in _REPORTS:
        if key in k or k in key:
            return k
    qtokens = set(key.split())
    for k in _REPORTS:
        if qtokens and qtokens.issubset(set(k.split())):
            return k
    return None


def get_reports(location: str) -> list[dict]:
    key = _resolve_key(location)
    return _REPORTS.get(key, []) if key else []


def get_coords(location: str) -> tuple[float, float]:
    key = _resolve_key(location)
    if key and key in LOCATION_COORDS:
        return LOCATION_COORDS[key]
    return DEFAULT_COORDS


def add_report(location: str, severity: str) -> dict:
    report = {"severity": severity, "minutes_ago": 0, "source": "citizen"}
    _REPORTS.setdefault(normalize_location(location), []).insert(0, report)
    return report
