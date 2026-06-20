# 🌧️ Follow Along · FloodPing Lagos
### Systems Design in Agentic Systems · GDG Cloud / Build with AI

## 1 · Try it now 📱  →  **floodping-130785602363.us-central1.run.app**
- `Is Orchid Road flooded?` — a citizen report **+** a forecast (kept separate)
- `Can I pass Ikorodu Road?` — watch it refuse to guess on stale data
- `where is flooded in Lagos?`  ·  `Can I get from Yaba to Lekki?`
- `Report flooding at Admiralty Road, road-blocked` — a friend reports → **you get a popup** 🚨

## 2 · Run it
```bash
git clone https://github.com/Greyisheep/floodping-lagos && cd floodping-lagos
pip install google-adk==2.2.0 && export GOOGLE_API_KEY=...   # aistudio.google.com/apikey
adk run floodping      # chat in your terminal   ·   adk web   # UI at :8000
```
Full app (chat UI + flood card + live popups):
```bash
cp .env.example .env   # paste your key
docker build -t floodping . && docker run --rm -p 8080:8080 --env-file .env floodping   # → localhost:8080
```

## 3 · Ship it to Cloud Run
```bash
gcloud run deploy floodping --source . --region us-central1 --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=YOUR_KEY,GOOGLE_GENAI_USE_VERTEXAI=false"
```
*(Production: keys → Secret Manager. See [`README.md`](README.md).)*

## The point 👀
- **Routing & safety are code** — not the prompt.
- **Report ≠ prediction** — ground truth vs. forecast, never blurred.
- **The LLM does one fuzzy job** — parsing messy locations.
- **Vet, don't block** — every report broadcasts to everyone.

**Design your own:** [`DESIGN-CHALLENGE.md`](DESIGN-CHALLENGE.md) + [`CHECKLIST.md`](CHECKLIST.md).
*AI builds what you can specify — systems design is knowing what to specify.*
