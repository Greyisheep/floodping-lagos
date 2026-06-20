"""In-process notification broadcast — see issue #9.

When a citizen report comes in, every connected client on the page gets a popup.
Reports are NEVER blocked: vetting only annotates a `possibility` level (low/medium/high).

NOTE (design challenge): this is in-process — it only reaches clients on THIS instance.
Across multiple Cloud Run instances you'd need a shared bus (Redis pub/sub, Pub/Sub).
For the demo we pin to one instance.
"""
from __future__ import annotations

import asyncio
from typing import Any

_subscribers: set[asyncio.Queue] = set()


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


def broadcast(event: dict[str, Any]) -> int:
    """Push to every subscriber (best-effort). Returns how many got it."""
    n = 0
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
            n += 1
        except asyncio.QueueFull:
            pass
    return n
