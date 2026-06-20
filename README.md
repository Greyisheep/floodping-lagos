# FloodPing Lagos 🌧️

A real-time, street-level flood assistant for Lagos: ask *"is this route flooded right now?"*,
**report** flooding (everyone on the page gets a popup), and get a **flash-flood forecast** — built
as the live demo for **"Systems Design in Agentic Systems"** (GDG Cloud / Build with AI) on
**Google ADK 2.2** + **gemini-3.5-flash**.

> 🔴 **Live:** https://floodping-130785602363.us-central1.run.app · Design gates:
> [`CHECKLIST.md`](CHECKLIST.md) · Group brief: [`DESIGN-CHALLENGE.md`](DESIGN-CHALLENGE.md) ·
> Run it: [`FOLLOW-ALONG.md`](FOLLOW-ALONG.md)

## The point
The LLM does **one** fuzzy job — turning *"chevron roundabout side after orchid"* into a real
location. Everything that matters for correctness is **code**:

- **Routing is code** — a deterministic `before_model_callback` picks check-vs-report, no LLM call.
- **Fusion is code** — `get_flood_status` fuses citizen reports + live rain (Google Weather →
  Open-Meteo failover) + a 6h forecast into a **dynamic freshness window** (a report goes stale in
  20 min when raining vs 90 min when dry) and a **flash-flood prediction**.
- **Provenance is explicit** — replies + the UI card always separate a citizen **REPORT** (ground
  truth) from a forecast **PREDICTION** (never conflated).
- **Safety is code** — a `freshness_guard` (`after_model_callback`) refuses "passable" unless a
  *fresh* report backs it.
- **Reports vet, never block** — a low-possibility report is still recorded and still **broadcast**
  to every connected client (SSE `/events` → popup).

```
FloodPingRouter (root)         before_model_callback = flood_router_guard   (routing in code)
├── CheckAgent  (read)         after_model_callback  = freshness_guard      (safety in code)
│     get_flood_status ─► citizen reports + Google Weather + 6h forecast + flash-flood prediction
└── ReportAgent (write)
      submit_report   ─► records + VETS (possibility) + BROADCASTS to everyone  (never blocks)
```

**Stack:** ADK 2.2 · gemini-3.5-flash · FastAPI · Docker · Cloud Run · **Cloud SQL**
(`DatabaseSessionService`, stateless sessions) · **OTel → Cloud Trace** · Google Geocoding +
Weather. Data layer is stubbed; the guardrails are the deliverable.

## Run it
```bash
pip install pytest && PYTHONPATH=. pytest -q          # deterministic logic needs no key
cp .env.example .env && $EDITOR .env                  # GOOGLE_API_KEY (+ GOOGLE_WEATHER_API_KEY optional)

docker build -t floodping . && docker run --rm -p 8080:8080 --env-file .env floodping
#   browser UI:          http://localhost:8080/   (chat + flood card + live report popups)
#   built-in ADK CLI/UI: adk run floodping   |   adk web
#   force rain (demo):   add  -e FLOODPING_DEMO_RAIN_MM=8
#   stateless sessions:  add  -e DATABASE_URL=sqlite:///./floodping.db   (/health shows the backend)

curl -s localhost:8080/chat -H 'content-type: application/json' -d '{"message":"Is Orchid Road flooded?"}'
curl -s localhost:8080/chat -H 'content-type: application/json' -d '{"message":"Can I pass Ikorodu Road?"}'   # guard -> Unknown
```

## Deploy to Cloud Run
```bash
# secrets via Secret Manager — plaintext never touches git, the image, or a flag
printf '%s' "$GEMINI_KEY"  | gcloud secrets create floodping-gemini  --data-file=-
printf '%s' "$WEATHER_KEY" | gcloud secrets create floodping-weather --data-file=-

gcloud run deploy floodping --source . --region us-central1 --allow-unauthenticated \
  --no-cpu-throttling --max-instances=1 \
  --set-secrets  "GOOGLE_API_KEY=floodping-gemini:latest,GOOGLE_WEATHER_API_KEY=floodping-weather:latest" \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=false,FLOODPING_MODEL=gemini-3.5-flash,OTEL_TO_CLOUD=1"
```
- `--no-cpu-throttling` lets the OTel span batch flush; `--max-instances=1` keeps the in-process
  report broadcast reaching every client (across instances you'd need Redis/Pub-Sub — see the
  [design challenge](DESIGN-CHALLENGE.md)).
- Stateless sessions: add `--add-cloudsql-instances <PROJECT>:<REGION>:floodping-db` +
  `--set-secrets DATABASE_URL=floodping-dburl:latest` (URL `postgresql+asyncpg://…?host=/cloudsql/<icn>`).

## Tear down (stop all charges)
Delete everything you stood up — Cloud SQL is the main ongoing cost:
```bash
PROJECT=deepstack-492609   # your project

gcloud run services delete floodping --region us-central1 --project $PROJECT --quiet
gcloud sql instances delete floodping-db --project $PROJECT --quiet            # only if you created Cloud SQL
for s in floodping-gemini floodping-weather floodping-dburl; do
  gcloud secrets delete "$s" --project $PROJECT --quiet
done
gcloud artifacts repositories delete cloud-run-source-deploy \
  --location us-central1 --project $PROJECT --quiet                            # build images

# verify nothing remains
gcloud run services list --region us-central1 --project $PROJECT | grep floodping || echo "clean"
gcloud sql instances list --project $PROJECT | grep floodping || echo "clean"
```
Enabled APIs are free at rest, so you can leave them. The GitHub repo is the lasting artifact — one
`gcloud run deploy --source .` brings it all back.

## Scope
One city (Lagos), chat + a browser UI, four jobs: check · predict · report · broadcast. Out of scope
by design: map UI, photo pipeline, route multi-segment, cross-instance fan-out, email ingestion —
those are the [`DESIGN-CHALLENGE.md`](DESIGN-CHALLENGE.md) extensions.
