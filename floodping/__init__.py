# FloodPing Lagos — see issue #1
# https://github.com/Greyisheep/floodping-lagos/issues/1
#
# Guarded import: lets `adk run` / `adk web` discover `root_agent`, while the pure
# deterministic logic (guardrails/weather) stays importable/testable WITHOUT google-adk
# installed (CHECKLIST §2, §8). The server also imports the agent explicitly.
try:
    from . import agent  # noqa: F401
except ModuleNotFoundError:
    pass
