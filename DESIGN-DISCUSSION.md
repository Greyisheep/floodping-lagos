# Design Discussion — Agentic Systems (attendee handout)
### GDG Cloud / Build with AI · Lagos · June 2026

> **How to use this (in groups of 3–5, ~18 min):** you're going to *design* a small agent before
> anyone writes code. Don't open an IDE. Sketch boxes and arrows. Argue about the trade-offs. The
> goal isn't a "right answer" — it's to feel that **an agent is a distributed system**, and your
> systems-design instincts already apply.

---

## The problem

**"Help a Lagos resident: check if a route is flooded, predict flash-flood risk, let them report it,
and notify everyone."** One city, chat, four jobs: check · predict · report · broadcast.

> Fuller brief with requirements + the notification fan-out sub-challenge: [`DESIGN-CHALLENGE.md`](DESIGN-CHALLENGE.md).
>
> *(Or bring your own: a market-price checker, an NYSC/JAMB helper, a delivery tracker — same dimensions.)*

**Scope discipline:** you are NOT building a national flood platform. Map UI, photo uploads, ML
trust-scores, WhatsApp ingestion = out of scope today. Design the *one slice*.

---

## Design across these 7 dimensions

Sketch your answer to each. The hard questions are starred ★.

1. **Decompose** — one agent, or a few? Where's the seam? *(hint: is "check" the same job as "report"?)*
2. **Route ★** — a message arrives. How do you decide which part handles it? *Does deciding that
   need a language model… or is "report" just a keyword? What does an LLM call cost you (seconds, ₦)?*
3. **State & freshness ★** — someone reported this street "passable" 3 hours ago, in heavy rain.
   Do you trust it? Where does "the user's location" live across turns?
4. **Boundaries** — list your tools. Which **read**, which **write**? Should the same agent do both?
5. **Guardrail ★** — there's no recent report (or only a stale one). What does the bot say? Who
   *enforces* that it never wrongly says "passable" — the prompt, or code?
6. **Provenance ★** — a citizen *report* is ground truth; a *forecast* is a prediction. How do you
   say which is which, and never present a prediction as a confirmed report?
7. **Notifications ★** — a report comes in. How does *every* person on the page see it instantly?
   Now make it work across many server instances. (Never block a report — **vet, then broadcast**.)
8. **Observe & eval** — it answered 500 routes during the storm. Were the "passable" calls correct?
9. **Cost & latency** — where do the seconds go? Where does the LLM *actually* earn its place?

> **The one to nail (§5):** if the model guesses "the road is clear" and someone drives a school bus
> into a flood, that's a safety incident. So the safety rule lives in **code**, not the prompt.

---

## The ADK 2 toolkit (what you can reach for)

You don't have to invent orchestration — Google ADK 2.x gives you a primitive for each decision:

| Decision | ADK 2 building block |
|---|---|
| Agents & delegation | `LlmAgent`, `sub_agents`, `transfer_to_agent` |
| Deterministic routing | a `before_model_callback` (skip the LLM) |
| Guardrails in code | `before_/after_model_callback`, `before_tool_callback` |
| Tools (read/write) | `FunctionTool`, `ToolContext.state`; external via **`McpToolset`** / `OpenAPIToolset` |
| Typed output | `output_schema` (structured JSON) |
| Sessions/state | `InMemorySessionService` → `DatabaseSessionService` (stateless scale) |
| Long-term memory | `MemoryService` |
| Human-in-the-loop | tool `require_confirmation` |
| Run / talk to it | `adk run` (CLI), `adk web` (UI), `Runner` |
| Deploy | `adk deploy cloud_run` / `gcloud run deploy` |

## ⭐ Latest from Google I/O '26 (full map: [`ADK-AT-IO-2026.md`](https://github.com/Greyisheep/floodping-lagos/blob/main/ADK-AT-IO-2026.md))

ADK 2.0 is **graph-based** (`BaseAgent` is a node). Three workflow flavours:
- **Graph workflows** — `Workflow` + route-labelled `Edge`s + `FunctionNode`/`JoinNode` + per-node retries.
  *"A slider from model-led reasoning to strict deterministic workflows"* — that slider is today's whole point.
- **Dynamic workflows** — decorator/`async`-based (loops, conditionals, `asyncio.gather`, checkpoint/resume) —
  the most approachable way in.
- **Collaborative workflows** — coordinator + specialists (chat/task/single-turn).

Plus **Skills** (`SkillToolset`), **MCP/A2A**, **5 SDKs** + **ADK for Android / Gemini Nano**, **Agent Engine**,
and the **integrations ecosystem** (HuggingFace, Pinecone, AgentOps/Phoenix/MLflow, StackOne via `McpToolset`).
*Reach for one only if it earns its place — don't bolt on dependencies for show.*

---

## Before you'd call it "done" — the scorecard

A design that's all ✅ ships; ❌ on guardrails or reliability does not.

- [ ] Routing that needs no intelligence is **code**, not an LLM call
- [ ] Safety/money rules enforced in **code** (a callback), with a safe fallback
- [ ] Freshness/TTL treated as part of the data (no trusting stale "all clear")
- [ ] Read vs write tools split; writes validated
- [ ] Stateless instances (externalized sessions) → scalable
- [ ] Every request traceable; a few frozen eval cases
- [ ] No secrets in git/images; keys injected at runtime
- [ ] One-command deploy + a health check

> Full version: [`CHECKLIST.md`](https://github.com/Greyisheep/floodping-lagos/blob/main/CHECKLIST.md)

---

## After you design — see one that's real

A working reference of exactly this — ADK 2.2, `gemini-3.5-flash`, live rain + 6h forecast, flash-flood
prediction, the freshness guard, live report broadcast, Cloud SQL sessions, OTel → Cloud Trace, on Cloud
Run — is at **[github.com/Greyisheep/floodping-lagos](https://github.com/Greyisheep/floodping-lagos)**
(live: `https://floodping-130785602363.us-central1.run.app`). Then prompt your favourite AI to build
*your* design, and deploy it the same way.
