"""Dynamic-freshness logic — see issue #2. Pure, no network/key (CHECKLIST §3, §8)."""
from floodping.weather import (
    DRY_TTL_MINUTES,
    RAIN_TTL_MINUTES,
    UNKNOWN_TTL_MINUTES,
    effective_ttl_minutes,
)


def test_ttl_shrinks_in_rain():
    assert effective_ttl_minutes(1.0) == RAIN_TTL_MINUTES


def test_ttl_long_when_dry():
    assert effective_ttl_minutes(0.0) == DRY_TTL_MINUTES


def test_ttl_default_when_weather_unknown():
    assert effective_ttl_minutes(None) == UNKNOWN_TTL_MINUTES


def test_a_35min_report_flips_with_rain():
    # The "rain flip" the demo hinges on: fresh when dry, stale in rain.
    age = 35
    assert age <= effective_ttl_minutes(0.0)   # dry  -> fresh
    assert age > effective_ttl_minutes(1.0)    # rain -> stale
