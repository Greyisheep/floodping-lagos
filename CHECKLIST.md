# Architect-Level System Design Checklist for Agentic Systems

> A production-readiness and architecture review checklist for agentic systems.
>
> Use it **before implementation**, **during design review**, **before launch**, and **after major
> prompt/tool/model changes**. Score each item:
>
> - ✅ Clear and evidenced
> - ⚠️ Partially addressed
> - ❌ Missing or unsafe
>
> Every ✅ should link to evidence: issue, design doc, code, eval run, dashboard, runbook, trace, or test.
>
> **Upfront principle:** *do not build an agent when a normal workflow, classifier, RAG call, or
> deterministic service is enough.* Anthropic distinguishes **workflows** (code owns the control path)
> from **agents** (the model dynamically controls tool use) and recommends starting simple
> ([Building Effective Agents][1]). OWASP treats prompt injection, excessive agency, sensitive-data
> disclosure, tool abuse, and unbounded consumption as first-class risks ([OWASP GenAI][2]). NIST's AI
> RMF frames architecture as governance + map + measure + manage, not just implementation quality
> ([NIST AI RMF][3]).

---

## 0. Traceability and ownership
- [ ] Work starts from an issue, RFC, or design doc.
- [ ] The issue defines scope, acceptance criteria, non-goals, and failure conditions.
- [ ] The design links to this checklist and records every gap as a follow-up issue.
- [ ] Every agent, tool, prompt, guardrail, and data source has an owner.
- [ ] Code, prompt files, evals, dashboards, and runbooks reference the issue or design doc.
- [ ] There is a named **operational** owner for production behavior, not just a builder.

**Architect question:** When this system behaves badly in production, who owns the fix?

## 1. Agentic justification
- [ ] The design explains why this needs an agentic system.
- [ ] Simpler alternatives were considered: deterministic code, workflow, rules engine, classifier, RAG, form, search, or human queue.
- [ ] The agent is used only where flexibility, messy input, planning, or judgment is actually needed.
- [ ] Non-fuzzy decisions are handled in code.
- [ ] The design states the complexity the agent adds: latency, cost, reliability risk, security risk, debugging difficulty.
- [ ] There is a clear "do not use an agent here" boundary.

**Architect question:** Is the agent solving real uncertainty, or hiding missing product/design work?

## 2. User, business, and risk context
- [ ] Target users defined; business goal clear; user journey mapped input → outcome.
- [ ] Decisions classified by risk: informational · recommendation · user-visible action · financial · legal/compliance · safety-critical · destructive/irreversible.
- [ ] "Wrong" is defined in business terms; the cost of a wrong action is understood; an acceptable error rate is stated.

**Architect question:** What is the worst credible harm this agent can cause?

## 3. Autonomy level
- [ ] Autonomy is explicit: read-only assistant · drafting assistant · recommendation engine · supervised actor · autonomous actor.
- [ ] Allowed actions match the autonomy level; some actions require human approval; some the agent can never perform.
- [ ] The agent knows when to stop and escalate.
- [ ] Max-iteration, max-cost, and max-tool-call limits exist.

**Architect question:** Can the agent act beyond what the user or business explicitly authorized?

## 4. Decomposition and boundaries
- [ ] Responsibilities split by job, not framework neatness; each agent has one remit; no god-agent.
- [ ] Each agent has the minimum tools it needs; agent-to-agent calls are explicit.
- [ ] State ownership and write ownership are clear; handoffs have typed contracts; no circular delegation without a stop condition.

**Architect question:** Could a new engineer tell which agent owns a decision, state change, or failure?

## 5. Orchestration and control flow
- [ ] Deterministic routing in code where possible; LLM routing only where classification is genuinely fuzzy.
- [ ] Workflow steps explicit and observable; the system distinguishes fixed workflow · router · planner · multi-agent · autonomous loop.
- [ ] Every loop has a stopping rule; every branch a fallback; the path chosen is explainable and replayable from logs/traces.

**Architect question:** Is the LLM controlling the process because it should, or because the architecture avoided a decision?

## 6. State, memory, and source of truth
- [ ] Session state, working memory, long-term memory, cache, and source of truth are separate.
- [ ] Model context is a lossy cache, not authority; the authoritative store for every important fact is named.
- [ ] Memory writes are explicit and risk-reviewed; retention + deletion rules exist.
- [ ] Stale data is detected; freshness/TTL is part of the data contract; the agent refuses/refreshes/escalates on stale data; state-changing ops are transactional where needed.

**Architect question:** If memory, cache, and database disagree, who wins?

## 7. Data, RAG, and knowledge grounding
- [ ] Every external knowledge source has an owner and provenance; freshness, timestamp, and trust level are tracked.
- [ ] Trusted internal data is distinguished from untrusted external content; retrieval is bounded and ranked; important claims can be cited.
- [ ] RAG content is treated as **data, not instructions**; defenses against poisoned docs and indirect prompt injection exist.
- [ ] Behavior is defined when sources conflict and when no reliable source exists.

**Architect question:** Can an untrusted webpage, PDF, email, or uploaded file secretly control the agent?

## 8. Tool design and least privilege
- [ ] Tools are typed contracts; names are specific; descriptions include boundaries/examples.
- [ ] Read vs write tools separated; money/destructive/side-effect tools isolated; inputs validated; authorization enforced in code, not by the model.
- [ ] Tool outputs structured + token-efficient + enough context for the next step; errors explicit and recoverable.

**Architect question:** If the model calls the wrong tool with plausible-looking arguments, what prevents damage?

## 9. Guardrails as code
- [ ] Safety, money, PII, and policy rules enforced in code/callbacks — the prompt is not the only guardrail.
- [ ] Guardrails run before high-risk actions and after model output where needed; they have deterministic fallbacks.
- [ ] Guardrails are tested with adversarial cases, are observable, block unsafe execution, and record when/why they fired.

**Architect question:** What happens when the model gives a confident, well-written, unsafe answer?

## 10. Human-in-the-loop and approval design
- [ ] Human approval required for high-risk actions; approval screens show action, reason, affected entity, cost, irreversible consequences.
- [ ] Human can approve/reject/edit/escalate; decisions logged; the agent can't bypass approval via another tool.
- [ ] Timeout/no-response handled; approval fatigue avoided by requiring approval only where it matters.

**Architect question:** Is the human making an informed decision, or just clicking "approve"?

## 11. Reliability and failure handling
- [ ] Timeouts on every external call; retries with backoff+jitter; state-changing actions idempotent; duplicate tool calls don't double side-effect.
- [ ] Partial failure modeled; compensating actions where needed; failure states user-safe (unknown/pending/escalated/retrying/failed); no raw exceptions to users.
- [ ] Graceful degradation when tools/models/data fail; dead-letter/review queue for failed high-value tasks.

**Architect question:** What happens when the model retries the same write action three times?

## 12. Scalability and resource control
- [ ] Stateless per request where possible; session state externalized; hot paths cached; independent work parallelized.
- [ ] Fan-out, context growth, tool-call growth, memory growth, and token usage are all bounded.
- [ ] Concurrency limits defined; rate limits enforced per user, tenant, and system.

**Architect question:** Can one user, one prompt, or one bad loop exhaust the system?

## 13. Observability and auditability
- [ ] Every request has a trace ID; traces capture agent, model, prompt version, tool calls, latency, errors, final verdict.
- [ ] Decisions, guardrail fires, and human approvals logged; tool args logged safely with PII redaction; token usage + cost measured.
- [ ] p50/p95/p99 latency measured; replay supported; dashboards for quality/cost/latency/tool errors/guardrails; alerts for abnormal cost, failures, tool usage, safety violations.

**Architect question:** Can you explain a bad production answer after the fact?

## 14. Evaluation and testing
- [ ] Eval set from real cases incl. happy paths, edge cases, adversarial inputs, stale data, missing data, tool failures; expected outcomes defined.
- [ ] Results tracked over time; prompt/tool/model changes run against evals; regression thresholds defined; red-team tests for injection + tool misuse.
- [ ] Unit tests for deterministic code; integration tests for tool contracts; e2e tests for critical journeys.

**Architect question:** How do you know the system got better instead of just sounding better?

## 15. Prompt, model, and configuration lifecycle
- [ ] Prompts versioned + reviewed + linked to eval results; model versions pinned; model/config changes treated as production changes and auditable.
- [ ] Rollback for prompt/model/config; model tier defined per task; fallback for model outage/degradation; framework lock-in avoided where possible.

**Architect question:** Can you safely answer "what changed?" when quality drops?

## 16. Security and abuse resistance
- [ ] User input, tool output, and retrieved docs are untrusted by default; external content separated from system instructions.
- [ ] Prompt injection + **indirect** prompt injection in the threat model; secrets never exposed to the model or logged; AuthN/AuthZ enforced outside the model.
- [ ] Agent identity/permissions explicit; tenant boundaries enforced; PII minimized + redacted from logs; dangerous tool combinations restricted; abuse + rate limits; a **kill switch**.

**Architect question:** If the agent reads malicious instructions from a user, webpage, file, email, or tool output, can it still act safely?

## 17. Cost and latency budget
- [ ] Stated p95 latency + per-request cost targets; token + tool/API cost estimated per path.
- [ ] Cheaper models for routine tasks, stronger only when needed; unnecessary LLM hops avoided; stable expensive results cached.
- [ ] Cost tracked per user/tenant/feature/agent; alerts for cost spikes.

**Architect question:** Can the business afford this system at 10x usage?

## 18. Deployment, release, and rollback
- [ ] Reproducible build; one-command/pipeline deploy; config environment-based; health + readiness checks.
- [ ] Rollback tested (incl. prompt/model/config); releases canaried; risky features flagged; the same artifact moves across environments.

**Architect question:** Can you ship safely without betting the whole product on one release?

## 19. Incident response and production operations
- [ ] Runbooks for bad outputs, tool misuse, runaway cost, model outage, data leakage.
- [ ] Disable one agent or one tool without disabling the whole system; review queue for suspicious/failed actions.
- [ ] Team can identify affected users, replay the incident path, and correct/compensate bad actions.

**Architect question:** When something goes wrong at 2am, what exact lever do you pull?

## 20. Product UX and trust
- [ ] User understands what the agent can/can't do; sees when it's uncertain; sees when info is stale; can inspect sources/reasoning.
- [ ] User can correct the agent and undo/cancel where possible.
- [ ] The agent avoids false certainty, doesn't hide failure behind confident language, and communicates escalation clearly.

**Architect question:** Does the UX make the agent's limits visible, or over-trust the model?

## 21. Production readiness gates
A system does **not** ship if any of these are ❌:
- [ ] Agentic justification
- [ ] Risk tiering
- [ ] Tool authorization
- [ ] Guardrails as code
- [ ] Human approval for high-risk actions
- [ ] Idempotency on writes
- [ ] Eval coverage
- [ ] Observability
- [ ] Prompt/model rollback
- [ ] Security threat model
- [ ] Incident runbook
- [ ] Kill switch

## 22. Review format
For each section: **(1)** score ✅/⚠️/❌ · **(2)** name the gap · **(3)** name the risk · **(4)** link the
evidence · **(5)** file the follow-up issue · **(6)** assign an owner · **(7)** set severity —
P0 blocks production · P1 must fix before scale · P2 should fix soon · P3 improvement.

> A design with ❌ in guardrails, tool authorization, reliability, evals, observability, or security
> does not move from demo to production.

---

### Where FloodPing stands against this (worked example)
✅ agentic justification (LLM only normalizes messy location text) · ✅ guardrails as code (freshness
guard) · ✅ idempotent-ish writes + vet-don't-block reports · ✅ observability (OTel→Cloud Trace) ·
✅ deploy/rollback (Cloud Run revisions) · ⚠️ evals (unit tests only, no eval set yet) · ⚠️ human
approval (no high-risk actions yet) · ❌ kill switch · ❌ rate limits · ❌ incident runbook. *It's a
teaching demo — the ❌/⚠️ rows are exactly the "demo → production" gap this checklist exists to expose.*

[1]: https://www.anthropic.com/research/building-effective-agents
[2]: https://genai.owasp.org/llmrisk/llm01-prompt-injection/
[3]: https://www.nist.gov/itl/ai-risk-management-framework
