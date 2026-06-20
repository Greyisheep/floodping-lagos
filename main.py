"""FloodPing Lagos HTTP server — see issue #1, #4.

Thin FastAPI wrapper over the ADK Runner:
- GET  /         -> a clean chat UI (one file, no build step)
- GET  /health   -> health check (CHECKLIST §11)
- POST /chat     -> talk to the agent

Session backend is swappable (CHECKLIST §7): set DATABASE_URL to go stateless
(DatabaseSessionService), else in-memory for the demo.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

try:  # graceful handling of transient model errors (CHECKLIST §6)
    from google.genai.errors import ServerError
except Exception:  # pragma: no cover
    class ServerError(Exception):
        ...

from floodping.agent import root_agent

APP_NAME = "floodping"


def _setup_tracing() -> None:
    """OpenTelemetry -> Cloud Trace (CHECKLIST §8). Activated by OTEL_TO_CLOUD=1; ADK emits
    spans on the global provider, so agent/tool steps show up in Cloud Trace. Never breaks startup."""
    if os.environ.get("OTEL_TO_CLOUD") != "1":
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": APP_NAME}))
        provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter()))
        trace.set_tracer_provider(provider)
        print("OTel -> Cloud Trace enabled")
    except Exception as exc:  # pragma: no cover - tracing must never break the service
        print("OTel tracing disabled:", exc)


_setup_tracing()


def _async_db_url(url: str) -> str:
    """ADK's DatabaseSessionService uses async SQLAlchemy — upgrade common URLs to async drivers
    so a naive `sqlite:///x.db` or `postgresql://...` just works."""
    for prefix, repl in (
        ("sqlite:///", "sqlite+aiosqlite:///"),
        ("postgresql://", "postgresql+asyncpg://"),
        ("postgres://", "postgresql+asyncpg://"),
    ):
        if url.startswith(prefix):
            return url.replace(prefix, repl, 1)
    return url


def _make_session_service():
    """InMemory for the demo; DatabaseSessionService when DATABASE_URL is set →
    stateless instances → horizontal scale on Cloud Run. The 'demo → production' one-liner."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        from google.adk.sessions import DatabaseSessionService

        return DatabaseSessionService(db_url=_async_db_url(db_url))
    return InMemorySessionService()


_session_service = _make_session_service()
_runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=_session_service)

app = FastAPI(title="FloodPing Lagos", version="0.2.0")


class ChatIn(BaseModel):
    message: str
    user_id: str = "demo"
    session_id: str = "demo"


@app.get("/health")
def health() -> dict:
    backend = type(_session_service).__name__
    return {"ok": True, "service": APP_NAME, "session_backend": backend}


@app.post("/chat")
async def chat(body: ChatIn) -> dict:
    session = await _session_service.get_session(
        app_name=APP_NAME, user_id=body.user_id, session_id=body.session_id
    )
    if session is None:
        await _session_service.create_session(
            app_name=APP_NAME, user_id=body.user_id, session_id=body.session_id
        )

    new_message = types.Content(role="user", parts=[types.Part(text=body.message)])

    final_text = None
    card = None
    try:
        async for event in _runner.run_async(
            user_id=body.user_id, session_id=body.session_id, new_message=new_message
        ):
            if event.content and event.content.parts:
                for p in event.content.parts:
                    fr = getattr(p, "function_response", None)
                    if fr is not None and getattr(fr, "name", "") == "get_flood_status":
                        resp = getattr(fr, "response", None)
                        src = resp.get("result") if isinstance(resp, dict) and "result" in resp else resp
                        if isinstance(src, dict) and "report_status" in src:
                            card = {
                                "verdict": src.get("report_status"),
                                "location": src.get("location"),
                                "age_min": src.get("newest_report_age_minutes"),
                                "rain_mm": src.get("current_rain_mm"),
                                "is_raining": src.get("is_raining"),
                                "prediction": src.get("flash_flood_prediction"),
                                "rain_expected": src.get("rain_expected"),
                            }
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(
                    p.text for p in event.content.parts if getattr(p, "text", None)
                ).strip()
    except ServerError:
        return {"response": "The model is busy right now — please try again in a few seconds.", "card": None}

    return {"response": final_text or "(no text response)", "card": card}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return _UI


_UI = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>FloodPing Lagos</title>
<style>
  :root { --blue:#1a73e8; --ink:#202124; --bg:#f6f8fc; --bot:#eef3fe; --warn:#b3261e; }
  * { box-sizing:border-box; } body { margin:0; font:16px/1.5 system-ui,Segoe UI,Roboto,sans-serif;
    color:var(--ink); background:var(--bg); display:flex; justify-content:center; }
  .wrap { width:100%; max-width:640px; min-height:100dvh; display:flex; flex-direction:column; }
  header { padding:16px 18px; background:#fff; border-bottom:1px solid #e3e6ea; }
  header h1 { margin:0; font-size:18px; } header p { margin:2px 0 0; color:#5f6368; font-size:13px; }
  #log { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:10px; }
  .msg { padding:10px 13px; border-radius:14px; max-width:86%; white-space:pre-wrap; }
  .me { align-self:flex-end; background:var(--blue); color:#fff; border-bottom-right-radius:4px; }
  .bot { align-self:flex-start; background:var(--bot); border-bottom-left-radius:4px; }
  .bot.warn { background:#fce8e6; }
  .bot p { margin:.35em 0; } .bot p:first-child { margin-top:0; } .bot p:last-child { margin-bottom:0; }
  .bot ul, .bot ol { margin:.35em 0; padding-left:1.2em; } .bot li { margin:.15em 0; }
  .bot strong { font-weight:600; } .bot em { font-style:italic; }
  .bot code { background:#0000000d; padding:1px 5px; border-radius:5px; font-size:.92em; }
  .card { background:#fff; border-radius:10px; padding:8px 11px; margin-bottom:8px; box-shadow:0 1px 3px #0000001f; }
  .card .cv { font-weight:700; font-size:14px; letter-spacing:.02em; }
  .card .cm { color:#5f6368; font-size:12.5px; margin-top:3px; }
  .chips { display:flex; gap:8px; flex-wrap:wrap; padding:0 16px 8px; }
  .chip { font-size:13px; padding:6px 10px; border:1px solid #d2d6db; border-radius:999px;
    background:#fff; cursor:pointer; } .chip:hover { border-color:var(--blue); color:var(--blue); }
  form { display:flex; gap:8px; padding:12px 16px; background:#fff; border-top:1px solid #e3e6ea; }
  input { flex:1; padding:11px 13px; border:1px solid #d2d6db; border-radius:999px; font-size:15px; }
  button { padding:11px 18px; border:0; border-radius:999px; background:var(--blue); color:#fff;
    font-size:15px; cursor:pointer; } button:disabled { opacity:.5; }
</style></head><body><div class="wrap">
  <header><h1>🌧️ FloodPing Lagos</h1><p>Ask if a route is flooded — or report flooding. Demo on Google ADK 2.2.</p></header>
  <div id="log"></div>
  <div class="chips">
    <span class="chip" onclick="ask(this.textContent)">Is Orchid Road flooded?</span>
    <span class="chip" onclick="ask(this.textContent)">Can I pass Ikorodu Road?</span>
    <span class="chip" onclick="ask(this.textContent)">Report flooding at Admiralty Road, car-risk</span>
  </div>
  <form id="f" onsubmit="return send(event)">
    <input id="m" autocomplete="off" placeholder="e.g. can I pass chevron to VGC?" />
    <button id="b">Send</button>
  </form>
</div>
<script>
  const log = document.getElementById('log'), inp = document.getElementById('m'), btn = document.getElementById('b');
  const sid = 'web-' + Math.random().toString(36).slice(2);
  // Self-contained, XSS-safe markdown -> HTML (no CDN, no build step).
  const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const inl = s => esc(s)
    .replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>')
    .replace(/(^|[^*])\\*([^*]+?)\\*/g,'$1<em>$2</em>')
    .replace(/`([^`]+)`/g,'<code>$1</code>');
  function md(text){
    let out='', list=null;
    for (const raw of text.split(/\\r?\\n/)) {
      const line = raw.trim();
      const b = line.match(/^[*\\-•]\\s+(.*)/), n = line.match(/^\\d+\\.\\s+(.*)/);
      if (b || n) { const t = n?'ol':'ul';
        if (list!==t){ if(list) out+='</'+list+'>'; out+='<'+t+'>'; list=t; }
        out += '<li>'+inl((b||n)[1])+'</li>';
      } else { if(list){ out+='</'+list+'>'; list=null; } if(line) out+='<p>'+inl(line)+'</p>'; }
    }
    if (list) out+='</'+list+'>';
    return out;
  }
  function add(text, who) {
    const d = document.createElement('div');
    d.className = 'msg ' + who + (who==='bot' && /unknown|do not assume/i.test(text) ? ' warn' : '');
    if (who==='bot' && text!=='…') d.innerHTML = md(text); else d.textContent = text;
    log.appendChild(d); log.scrollTop = log.scrollHeight; return d;
  }
  const VCOLORS = { passable:['🟢','#1e8e3e'], caution:['🟠','#e8710a'], blocked:['🔴','#d93025'], unknown:['⚪','#5f6368'] };
  const PRED = { likely:'⛈ likely', possible:'🌧 possible', unlikely:'🌤 unlikely' };
  function card(c) {
    if (!c || !c.verdict) return '';
    const [icon, col] = VCOLORS[c.verdict] || VCOLORS.unknown;
    const age = (c.age_min!=null) ? (c.age_min + ' min ago') : 'no citizen reports';
    const rain = c.is_raining ? ('🌧️ raining' + (c.rain_mm!=null ? ' ('+c.rain_mm+' mm)' : '')) : '☀️ no rain now';
    const loc = c.location ? esc(c.location) : '';
    const pred = c.prediction ? ('<div class="cm">flash-flood forecast: <b>'+esc(PRED[c.prediction]||c.prediction)
      +'</b> · <i>prediction, not a report</i></div>') : '';
    return '<div class="card" style="border-left:4px solid '+col+'">'
      + '<div class="cv" style="color:'+col+'">'+icon+' '+esc(c.verdict.toUpperCase())
      + ' <span style="font-weight:400;color:#5f6368;font-size:12px">(citizen report)</span></div>'
      + '<div class="cm">'+loc+' · '+age+' · '+rain+'</div>' + pred + '</div>';
  }
  function ask(t){ inp.value = t; send(new Event('x')); }
  async function send(e){ e.preventDefault(); const text = inp.value.trim(); if(!text) return false;
    add(text,'me'); inp.value=''; btn.disabled=true; const wait = add('…','bot');
    try {
      const r = await fetch('/chat',{method:'POST',headers:{'content-type':'application/json'},
        body: JSON.stringify({message:text, session_id:sid})});
      const j = await r.json(); wait.remove();
      const resp = j.response || '(no response)';
      const d = document.createElement('div');
      d.className = 'msg bot' + (/unknown|do not assume/i.test(resp) ? ' warn' : '');
      d.innerHTML = card(j.card) + md(resp);
      log.appendChild(d); log.scrollTop = log.scrollHeight;
    } catch(err){ wait.remove(); add('Network error — try again.','bot'); }
    btn.disabled=false; inp.focus(); return false;
  }
</script></body></html>"""
