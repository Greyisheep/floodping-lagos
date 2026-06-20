"""FloodPing Lagos HTTP server — see issue #1.

A thin FastAPI wrapper over the ADK Runner so the agent is one `curl` away — locally
in Docker and on Cloud Run. Health check at /healthz (CHECKLIST §11).
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from floodping.agent import root_agent

APP_NAME = "floodping"

# InMemorySessionService is per-instance — fine for the demo, NOT for horizontal scale.
# Swap for a DatabaseSessionService to make instances stateless (CHECKLIST §7).
_session_service = InMemorySessionService()
_runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=_session_service)

app = FastAPI(title="FloodPing Lagos", version="0.1.0")


class ChatIn(BaseModel):
    message: str
    user_id: str = "demo"
    session_id: str = "demo"


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "service": APP_NAME}


@app.post("/chat")
async def chat(body: ChatIn) -> dict:
    # get-or-create the session
    session = await _session_service.get_session(
        app_name=APP_NAME, user_id=body.user_id, session_id=body.session_id
    )
    if session is None:
        await _session_service.create_session(
            app_name=APP_NAME, user_id=body.user_id, session_id=body.session_id
        )

    new_message = types.Content(role="user", parts=[types.Part(text=body.message)])

    final_text = None
    async for event in _runner.run_async(
        user_id=body.user_id, session_id=body.session_id, new_message=new_message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(
                p.text for p in event.content.parts if getattr(p, "text", None)
            ).strip()

    return {"response": final_text or "(no text response)"}
