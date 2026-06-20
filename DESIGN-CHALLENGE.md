# Design Challenge — A Real-Time Flood-Intelligence Agent for Lagos
### Systems Design in Agentic Systems · GDG Cloud / Build with AI

> **In groups (~20 min): design the system, don't code it.** Sketch boxes and arrows, argue the
> trade-offs, and score your design against the gates. A reference build exists
> ([floodping-lagos](https://github.com/Greyisheep/floodping-lagos)) — but design *yours* first.

---

## The brief
During Lagos rains, residents don't know if a *specific* street is flooded **right now**. Official
forecasts are LGA-level; real street signal is scattered across X, WhatsApp, and estate chats.

Design an assistant that:
1. **Checks** a route — "can I pass Admiralty Road right now?"
2. **Predicts** flash-flood risk from current + forecast rain.
3. **Accepts reports** — residents report flooding (in chat, or by email to the agent).
4. **Broadcasts** — every report pops a notification to **everyone** using the page.

**Scope discipline:** one city (Lagos), chat + email channels, the four jobs above. Out of scope:
map UI, photo ML, route-multi-segment optimization — name them and drop them.

---

## Required capabilities (functional)

| # | Requirement | The hard part to design |
|---|---|---|
| R1 | **Check** a location | Routing: is "check vs report" a keyword (code) or a model call? Messy location text → real place |
| R2 | **Flash-flood prediction** | Fuse current rain + 6h forecast + flood-prone areas. **Label it a prediction, never a report** |
| R3 | **Report (vet, don't block)** | Vetting annotates a *possibility* (low/med/high). A low-possibility report is **still recorded and still broadcast** — never suppress a user's signal |
| R4 | **Live notifications** ⭐ | Every report → a popup for **every** connected client. How? (see below) |
| R5 | **Email ingestion** (stretch) | Resident emails the agent → agent vets → broadcasts / replies. Treat email as **untrusted input** |

### R4 deep-dive — the notification sub-challenge
This is the meatiest distributed-systems problem in the set:
- **In-process broadcast** (one server) is easy — an SSE/WebSocket fan-out (the reference does this).
- **Across many instances** it breaks: a report on instance A never reaches clients on instance B.
  How do you fan out across a horizontally-scaled, stateless service? *(Redis pub/sub? Cloud Pub/Sub?
  a message bus? sticky sessions?)* — name the trade-offs (latency, ordering, delivery guarantees, cost).
- **Provenance in the popup:** the notification must say whether it's a confirmed **report** or a
  **prediction**, and show the vetting possibility — without implying false certainty.

---

## The gates your design must clear (architect-level)
Score each ✅/⚠️/❌ against [`CHECKLIST.md`](CHECKLIST.md). The non-negotiables for *this* challenge:

1. **Agentic justification** — where is the LLM actually needed vs. plain code? (Hint: only the fuzzy bits.)
2. **Decomposition & least privilege** — who can *write*? Who can only *read*? Is this even multi-agent, or one agent + tools? (Justify it.)
3. **Guardrails as code** — never call a road "passable" without a fresh report; never present a prediction as a report.
4. **State, freshness & source of truth** — a 3-hour-old "clear" in heavy rain is worse than no data.
5. **Reliability** — what happens when the weather API times out, or a report is submitted twice?
6. **Notifications at scale** — R4 above.
7. **Security** — email/chat input is untrusted; could a malicious "report" or email manipulate the agent? (OWASP: prompt injection, excessive agency.)
8. **Observability & eval** — how do you know a "passable" call was right? How do you trace a bad broadcast?

---

## Deliverable (per group)
- A **diagram**: agents/services, tools (read vs write), data stores, the notification fan-out, where the LLM sits.
- **3 decisions + their trade-offs** (e.g., "deterministic router because…", "Redis pub/sub over sticky sessions because…").
- **One ❌** you'd accept for a demo but must fix for production — and why.

> Then prompt your favourite AI to build your design, and deploy it to Cloud Run the same way the
> reference does ([`FOLLOW-ALONG.md`](FOLLOW-ALONG.md)). **AI builds what you can specify — systems
> design is knowing what to specify.**
