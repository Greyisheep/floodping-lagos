# FloodPing Lagos — see issue #1
# https://github.com/Greyisheep/floodping-lagos/issues/1
#
# Intentionally NOT importing `agent` here: the deterministic logic (guardrails) must be
# importable/testable without google-adk installed (CHECKLIST §2, §8). The server imports
# the agent explicitly via `from floodping.agent import root_agent`.
