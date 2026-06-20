"""Stub data layer for FloodPing Lagos — see issue #1.

In production this is a Postgres/PostGIS query over citizen reports + a NiMet/NEMA
bulletin feed (CHECKLIST §3 State/freshness, §7 Scalability). For the workshop demo the
data is stubbed so the *guardrail* is the star, not a live feed.

Report ages are stored as explicit `minutes_ago` so behaviour is deterministic and
testable without a wall clock.
"""
from __future__ import annotations

# Controlled vocabulary for severity (CHECKLIST §4 — write tools validate inputs).
SEVERITY_LEVELS = ("passable", "ankle-level", "car-risk", "road-blocked")

# A report is only trustworthy if it is recent. This is the freshness TTL (CHECKLIST §3).
FRESHNESS_TTL_MINUTES = 45

# Official, citable warning (NiMet, June 2026). Always shown alongside citizen data.
OFFICIAL_WARNING = (
    "NiMet (June 2026): Lagos is among 19 states flagged for flash-flood risk; "
    "motorists are advised not to drive through flooded roads."
)

# Seed reports keyed by normalized location.
#   - "orchid road, lekki": FRESH + passable        -> check returns passable
#   - "admiralty road, lekki": FRESH + car-risk      -> check returns car-risk
#   - "lekki-epe expressway": FRESH + road-blocked   -> check returns blocked
#   - "ikorodu road": ONLY a STALE passable report   -> guardrail must refuse "passable"
_SEED_REPORTS: dict[str, list[dict]] = {
    "orchid road, lekki": [{"severity": "passable", "minutes_ago": 8, "source": "citizen"}],
    "admiralty road, lekki": [{"severity": "car-risk", "minutes_ago": 12, "source": "citizen"}],
    "lekki-epe expressway": [{"severity": "road-blocked", "minutes_ago": 30, "source": "citizen"}],
    "ikorodu road": [{"severity": "passable", "minutes_ago": 190, "source": "citizen"}],
}

# Mutable in-memory store seeded from the constants above (submit_report appends here).
# NOTE: per-instance memory is fine for the demo but is NOT the source of truth — see
# CHECKLIST §7 (stateless instances) before scaling this beyond one container.
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


def add_report(location: str, severity: str) -> dict:
    report = {"severity": severity, "minutes_ago": 0, "source": "citizen"}
    _REPORTS.setdefault(normalize_location(location), []).insert(0, report)
    return report
