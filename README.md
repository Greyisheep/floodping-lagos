# FloodPing Lagos 🌧️

A street-level flood route checker for Lagos. Ask *"is this route flooded right now?"*, or
report flooding. Built as the live demo for **"Systems Design in Agentic Systems"**
(GDG Cloud / Build with AI, Lagos) on **Google ADK 2.2**.

> Tracking issue: [#1](https://github.com/Greyisheep/floodping-lagos/issues/1) ·
> Design gates: [`CHECKLIST.md`](CHECKLIST.md)

## The point
The LLM is used for **one** thing: turning messy human text
(*"chevron roundabout side after orchid"*) into a normalized location. Everything that
matters for correctness is **code**:

- **Routing is code** — a deterministic `before_model_callback` sends check-vs-report without
  an LLM call (`floodping/guardrails.py: flood_router_guard`).
- **Safety is code** — a `freshness_guard` (`after_model_callback`) refuses to call a road
  "passable" unless a **recent** report backs it (`> 45 min` or none → "Unknown").

```
FloodPingRouter (root)            before_model_callback = flood_router_guard
├── CheckAgent  (read)            after_model_callback  = freshness_guard
│     tool: get_flood_status
└── ReportAgent (write)
      tool: submit_report
```

## Run it

```bash
# 0. the deterministic logic needs no key — run the unit tests first
pip install pytest && PYTHONPATH=. pytest -q

# 1. set your model key (AI Studio). NEVER commit it.
cp .env.example .env && $EDITOR .env      # set GOOGLE_API_KEY

# 2. local, in Docker
docker build -t floodping .
docker run --rm -p 8080:8080 --env-file .env floodping

# 3. ask it
curl -s localhost:8080/chat -H 'content-type: application/json' \
  -d '{"message":"Is Orchid Road flooded?"}'                 # fresh report -> passable
curl -s localhost:8080/chat -H 'content-type: application/json' \
  -d '{"message":"Can I pass Ikorodu Road?"}'                # only stale report -> guardrail: Unknown
```

## Deploy to Cloud Run

```bash
# key is injected at runtime — never in git, never in the image
gcloud run deploy floodping --source . --region us-central1 --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=$KEY,GOOGLE_GENAI_USE_VERTEXAI=false"
```

Tear down: `gcloud run services delete floodping --region us-central1`.

## Scope
This is one slice (check + report, Lagos, chat). Out of scope by design: map UI, photo
pipeline, PostGIS, trust-score ML, WhatsApp ingestion — see [#1](https://github.com/Greyisheep/floodping-lagos/issues/1).
The data layer is **stubbed** (`floodping/data.py`); the guardrail is the deliverable.
