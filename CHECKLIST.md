# System Design Checklist (Agentic Systems)

> A reusable, framework-agnostic design review. **Every build starts with an issue**, and the
> design must clear these gates *before* "it works on my machine" counts as done.
>
> Use it two ways: (1) as the acceptance bar for a new agent/service, (2) as the running
> scorecard in a design review. Mark each ✅ / ⚠️ / ❌ and link the evidence (file, issue, dashboard).

---

## 0. Traceability (the standard)
- [ ] **Work starts from an issue.** No issue, no branch. Scope + acceptance criteria live there.
- [ ] **Code references the issue** in comments / commit messages (e.g. `# see issue #1`).
- [ ] The design is reviewed against *this checklist* and gaps are recorded as follow-up issues.
> *Why:* traceability turns "why is this here?" into a one-click answer, forever.

## 1. Decomposition & boundaries
- [ ] Responsibilities are split by **job**, not by neatness. Each agent has one clear remit.
- [ ] No god-agent reasoning over a huge tool surface (trim tools to what each agent needs).
- [ ] Boundaries are explicit: who owns what state, who may call whom.
> *Why:* same reason we don't build monoliths. Focus = better prompts, isolation, testability.

## 2. Orchestration — determinism where you can
- [ ] Routing/control flow that **doesn't need intelligence is code, not an LLM call.**
- [ ] The LLM is reserved for the genuinely fuzzy part (e.g. parsing messy human text).
- [ ] ⚠️ Don't assume `sub_agents` description-based delegation is deterministic — it's
      LLM-driven/probabilistic. Roll an explicit router for guaranteed routing.
> *Why:* every avoidable LLM hop is seconds of latency and cents of cost. (FloodPing routes
> check-vs-report in code; the model never sees a routing decision.)

## 3. State & memory — and freshness
- [ ] Session state vs. long-term memory vs. **source of truth** are clearly separated.
- [ ] The model's memory/context is treated as a **lossy cache**, never authoritative for
      money/safety/state.
- [ ] **Freshness/TTL is part of the data.** Stale data is flagged or refused, not silently trusted.
> *Why:* a 3-hour-old "road clear" during active rain is worse than no data. (FloodPing: a
> 45-min TTL; Dockie: 6h sailing-cache TTL + re-fetch.)

## 4. Tools & least privilege
- [ ] Tools are typed contracts (clear inputs/outputs), like internal APIs.
- [ ] **Read vs. write is segregated.** Write/money/destructive tools live behind the agent that
      owns that responsibility — not on the general-purpose one.
- [ ] Write tools validate inputs (enum severities, bounds) before acting.
> *Why:* authz scopes for agents. The checker can't write; only the reporter can.

## 5. Guardrails as code (not prompt)
- [ ] Safety / money / PII rules are enforced in **callbacks or code**, not just instructions.
- [ ] The guardrail is the *last line* and assumes the model will sometimes disobey the prompt.
- [ ] Each guardrail has a deterministic, safe fallback output.
> *Why:* "the prompt is a suggestion; code is law." (FloodPing: freshness guard overrides any
> "passable" without a fresh report. Dockie: price guard overrides invented prices at 2% tolerance.)

## 6. Reliability & failover
- [ ] **Timeouts** on every external call; **retries** with backoff where safe.
- [ ] **Idempotency** on state-changing actions (the agent *will* retry).
- [ ] A **fallback path** for model/tool errors (degrade gracefully, never 500 the user).
- [ ] Failure is a first-class state (e.g. escalate / "unknown"), not an exception that leaks.
> *Why:* APIs hang, models rate-limit. Design the unhappy path on purpose.

## 7. Scalability
- [ ] The service is **stateless** per request (session state externalized) → horizontally scalable.
- [ ] Hot paths are **cached**; expensive work is **parallelized** where independent.
- [ ] No unbounded growth (context size, fan-out, memory) without a cap.
> *Why:* Cloud Run scales to N instances only if no instance holds local truth.

## 8. Observability & eval
- [ ] Every request is **traceable** (which agent, which tool, args, latency, verdict).
- [ ] An **eval set** of real cases with expected outcomes runs on every change.
- [ ] Key decisions (routing, guardrail fires) are logged.
> *Why:* you can't improve — or trust — what you can't trace.

## 9. Cost & latency budget
- [ ] There is a stated p95 latency + per-request cost target (a non-functional requirement).
- [ ] Model tier matches the task (cheap/stable model for routine work).
- [ ] No hop is added unless it earns its latency.
> *Why:* cost/latency is a design input, not a postmortem surprise.

## 10. Security
- [ ] **Secrets are never committed.** Injected at runtime (env/Secret Manager), gitignored.
- [ ] AuthN/AuthZ on write actions; PII minimized and not logged.
- [ ] Inputs from users/tools are untrusted until validated.
> *Why:* one leaked key or one trusted-prompt injection undoes everything above.

## 11. Deployability
- [ ] **One-command deploy** from a clean checkout; reproducible build (Docker).
- [ ] Health check endpoint; **rollback** is a known, fast operation.
- [ ] Config via env, not code; same image across environments.
> *Why:* if deploy/rollback is scary, you ship less and recover slower.

---

### How to use in a review
For each section: **score it, name the gap, file the follow-up issue.** A design that's all ✅
ships. A design with ❌ on §5 (guardrails) or §6 (reliability) does not — those are the
demo-to-production line.
