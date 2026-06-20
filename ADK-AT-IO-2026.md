# ADK at Google I/O 2026 — the developer's map
### What "latest Google" actually means for agent builders (and where FloodPing uses it)

> **Headline:** ADK 2.0 (Python GA **May 19 2026**) turns ADK into Google's **code-first engineering
> layer for production, graph-orchestrated, multi-agent systems** — while AI Studio, Antigravity 2.0,
> and Managed Agents cover the faster/prototyping paths. The shift: *from "AI that assists" to "agents
> that navigate complex tasks."* ([I/O '26 keynote][1], [Cloud I/O '26][2])

## The agent-stack ladder
| Lower friction (start fast) | Higher control (build architecture) |
|---|---|
| **AI Studio** — prompt-to-app | **ADK 2.0** — code-first control over routing, workflows, tools, state, multi-agent |
| **Managed Agents API** — hosted agent in one call | ↳ *"custom agent meshes" + complex orchestration* |
| **Antigravity 2.0** — desktop/CLI/SDK to steer agents | |

*Antigravity & Managed Agents are faster to start; **ADK is where you go when your agent needs architecture.*** ([Cloud I/O '26][2])

## ADK 2.0 — the three workflow capabilities
The big architecture shift: **from a hierarchical agent-executor to a graph-based execution engine**.
Agents, tools, and functions become **nodes in a graph**. `BaseAgent` now subclasses `BaseNode`. ([ADK 2.0][3])

1. **Graph workflows** — nodes (agents / tools / code / human-input) + edges define what runs next.
   Use for deterministic routing, branching, mixing code with AI, human approval mid-flow. *"Avoid
   putting complex logic in long prompts."* (Caveat: **live streaming incompatible**; **task mode
   disabled** for graphs in 2.0.0.) ([graphs][4])
2. **Dynamic workflows** — define flow with **normal code**: decorators, loops, conditionals, recursion,
   `async/await`, parallel `asyncio.gather`, **checkpointing + resume**, human-in-the-loop pauses.
   *(This is the most approachable way into the graph engine — the path to revisit for FloodPing.)* ([dynamic][5])
3. **Collaborative workflows** — a coordinator delegates to specialist sub-agents; modes: **chat / task /
   single-turn**. ([collaboration][6])

## The rest of the surface
- **Skills** — reusable capability packs (instructions + resources + tools), loaded incrementally via
  `SkillToolset`. Tools = callable; Skills = packaged capability; agents gain domain behavior without
  prompt bloat. ([skills][7])
- **MCP & A2A** — MCP connects agents to external tools/systems (the I/O codelab used Google Maps MCP);
  A2A is agent-to-agent interop. Devs get **ADK + A2A + MCP**. ([Cloud I/O '26][2])
- **Integrations ecosystem** — HuggingFace, MongoDB, Pinecone, AgentOps/Phoenix/MLflow, StackOne,
  BigQuery/Spanner/Pub-Sub — added in a few lines via `McpToolset`. ([integrations][8])
- **Languages** — Python, TypeScript, Go, Java, Kotlin; **ADK for Android** + on-device **Gemini Nano**
  (hybrid cloud/on-device orchestration). ([ADK home][9], [Kotlin/Android][10])
- **Deploy** — containerize anywhere, or Cloud Run / GKE / **Agent Runtime (Agent Engine)**. Plus
  **Agent Executor** — a durable runtime for long-running agents (snapshots, resume, sandboxing). ([ADK home][9], [Agent Executor][11])
- **Eval / observability / safety** — evals check **trajectory**, not just the final answer; OTel
  logs/metrics/traces; safety covers prompt injection, **indirect** injection via tools, jailbreaks,
  with guardrails/callbacks, Gemini-as-judge, sandboxed execution, and platform governance (Agent
  Identity/Gateway/Registry, Model Armor). ([evaluate][12], [observability][13], [safety][14])
- **Sessions / state / memory** — `SessionService` + `MemoryService`; Session = thread, State = session
  data, Memory = searchable cross-session. ([sessions][15])

## ⚠️ ADK 2.0 breaking changes (not just a version bump)
`Event` now has `node_info` + `output`; `BaseAgent` subclasses `BaseNode`; agents/tools/functions are
graph nodes; **don't manually append events**; exceptions are caught differently for retries/telemetry/
human-pause — **broad `try/except` can mask failures and break the runtime**. ([ADK 2.0][3])

## Where FloodPing sits on this map
| I/O '26 capability | FloodPing today |
|---|---|
| Code-first control (ADK 2.0) | ✅ `LlmAgent` + sub_agents + before/after callbacks |
| Deterministic routing | ✅ in code (`before_model_callback`) — the thesis |
| Graph / dynamic workflows | 🔜 not yet — **dynamic workflows** is the revisit path |
| Collaborative (coordinator + specialists) | ✅ minimally (Check / Report, least-privilege) |
| Sessions / state / memory | ✅ Session + State; **Cloud SQL** `DatabaseSessionService` |
| MCP / integrations | 🔜 weather/geocoding are direct calls (could be MCP) |
| Observability (OTel) | ✅ **OTel → Cloud Trace** |
| Eval (trajectory) | ⚠️ unit tests only — no eval set yet |
| Safety (injection, guardrails-as-code) | ✅ freshness guard; ⚠️ injection threat model TBD |
| Deploy | ✅ Cloud Run (Agent Engine is the managed alternative) |

> **The 2026 ADK lesson:** use ADK when the journey has **business-critical stages that need explicit
> orchestration** — graph workflows for critical paths, dynamic for runtime-dependent logic,
> collaborative for specialists, Skills for domain packs, MCP/A2A for interop, **evals + observability
> from day one.** Google turned ADK into the *serious engineering layer* for agent systems.

[1]: https://developers.googleblog.com/all-the-news-from-the-google-io-2026-developer-keynote/
[2]: https://cloud.google.com/blog/topics/developers-practitioners/io26-news-for-agent-developers-on-google-cloud
[3]: https://adk.dev/2.0/
[4]: https://adk.dev/graphs/
[5]: https://adk.dev/graphs/dynamic/
[6]: https://adk.dev/workflows/collaboration/
[7]: https://adk.dev/skills/
[8]: https://developers.googleblog.com/supercharge-your-ai-agents-adk-integrations-ecosystem/
[9]: https://adk.dev/
[10]: https://developers.googleblog.com/adk-kotlin-android-building-ai-agents/
[11]: https://cloud.google.com/blog/products/ai-machine-learning/agent-executor-googles-distributed-agent-runtime
[12]: https://adk.dev/evaluate/
[13]: https://adk.dev/observability/
[14]: https://adk.dev/safety/
[15]: https://adk.dev/sessions/
