# 🌧️ Follow Along — Build a Lagos Flood Agent
### Systems Design in Agentic Systems · GDG Cloud / Build with AI · Lagos

> Project this. Attendees: open the live demo on your phone, then follow the steps.

---

## 0 · Try the live one right now 📱
### **https://floodping-130785602363.us-central1.run.app**

Type any of these:
- `Is Orchid Road flooded?`               — a citizen report + a forecast prediction (kept separate)
- `Can I pass Ikorodu Road?`              — watch it refuse to guess on a stale report
- `where is flooded in Lagos?`   ·   `Can I get from Yaba to Lekki?`   — city-wide + a route
- `Report flooding at Admiralty Road, road-blocked`   — have a friend on the page report it: **everyone gets a popup** 🚨

---

## 1 · Get the code
```bash
git clone https://github.com/Greyisheep/floodping-lagos
cd floodping-lagos
```

## 2 · Talk to it on your machine
```bash
pip install google-adk==2.2.0
export GOOGLE_API_KEY=...     # free key: https://aistudio.google.com/apikey

adk run floodping             # chat in your terminal
#   …or…
adk web                       # browser UI at http://localhost:8000
```

Run the full app (with the chat UI) in Docker:
```bash
cp .env.example .env          # paste your key into .env
docker build -t floodping . && docker run --rm -p 8080:8080 --env-file .env floodping
# open http://localhost:8080
```

## 3 · Ship it to Google Cloud Run
```bash
gcloud run deploy floodping --source . --region us-central1 --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=YOUR_KEY,GOOGLE_GENAI_USE_VERTEXAI=false"
```
*(Production: put keys in Secret Manager instead — see [`README.md`](README.md).)*

---

## What to notice (the whole point) 👀
- **Routing is code, not an LLM call** — a `before_model_callback` picks check-vs-report.
- **Safety is code, not the prompt** — the guard refuses "passable" without a *fresh* report.
- **Report ≠ prediction** — a citizen *report* (ground truth) and a *forecast* prediction are never blurred.
- **The LLM does one fuzzy job** — turning *"chevron roundabout side after orchid"* into a real location.
- **Freshness is dynamic** — a report goes stale in 20 min raining vs 90 min dry.
- **Report once, everyone sees it** — reports broadcast to all clients, vetted but **never blocked**.

## Now design your own
Use [`DESIGN-CHALLENGE.md`](DESIGN-CHALLENGE.md) (the brief) + the [`CHECKLIST.md`](CHECKLIST.md) gates. Then prompt your favourite AI to build it,
and deploy it the same way. **AI builds what you can specify — systems design is knowing what to specify.**
