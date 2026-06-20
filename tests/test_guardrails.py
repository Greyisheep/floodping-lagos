"""Pure-logic tests — see issue #1. No API key / network needed: the deterministic
parts (routing + safety) are exactly the parts that don't need an LLM (CHECKLIST §2, §5)."""
from floodping.guardrails import classify_intent, should_block_passable


def test_router_check_intent():
    assert classify_intent("Is Admiralty Road flooded right now?") == "check"
    assert classify_intent("can I pass Lekki-Epe expressway?") == "check"


def test_router_report_intent():
    assert classify_intent("Reporting flooding at Orchid Road, it's car-risk") == "report"
    assert classify_intent("I want to submit a flood report") == "report"


def test_router_defers_when_ambiguous():
    assert classify_intent("hello") is None
    assert classify_intent("") is None


def test_guard_blocks_passable_when_verdict_not_passable():
    # Model says clear, but the code verdict is not 'passable' -> must block.
    assert should_block_passable("Orchid Road looks passable, you can pass.", "unknown")
    assert should_block_passable("The road is clear and safe to drive.", "caution")


def test_guard_allows_passable_when_verdict_passable():
    assert not should_block_passable("Orchid Road is passable.", "passable")


def test_guard_ignores_non_passable_text():
    # A 'blocked' answer never trips the guard.
    assert not should_block_passable("Lekki-Epe is road-blocked, avoid it.", "blocked")
