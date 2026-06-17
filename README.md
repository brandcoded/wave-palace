# WavePalace

Visual radio channels for the web and VRChat. Curated music, cinematic loops,
and shareable playback links for lounges, worlds, parties, and late-night
digital spaces.

This repository is a **polished MVP**: visually strong and product-ready, but
intentionally narrow in scope.

## Stack

- **Frontend:** Next.js (App Router) · TypeScript · Tailwind CSS · Lucide icons
- **Backend:** Python FastAPI · Uvicorn · Pydantic
- **Data:** MongoDB-ready repository with in-memory **seed fallback** (no DB
  needed to run)
- **Tests:** pytest
- **Deploy targets:** Vercel (frontend) · Render (backend) · MongoDB Atlas (DB)

## Folder structure

```
wave-palace/
  apps/
    frontend/   Next.js app (presentation / features / shared layers)
    backend/    FastAPI app (api / services / repositories / seed / schemas)
  docs/         PRODUCT_BRIEF, ARCHITECTURE, API_CONTRACT, FEATURE_SLICES,
                LICENSING_NOTES, MVP_TO_LAUNCH_ROADMAP, DEPLOYMENT, CHANGELOG
  AGENTS.md     Rules for future coding agents
  README.md
```

## Local setup

### Backend

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # leave MONGODB_URI empty to use seed mode
uvicorn app.main:app --reload --port 8000
```

API: `http://localhost:8000` · Swagger: `http://localhost:8000/docs`

### Frontend

```bash
cd apps/frontend
npm install
cp .env.example .env.local    # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

App: `http://localhost:3000`

### Tests

```bash
cd apps/backend
pytest
```

## Environment variables

| Service  | Variable                   | Purpose                              |
|----------|----------------------------|--------------------------------------|
| backend  | `MONGODB_URI`              | empty → local seed mode              |
| backend  | `MONGODB_DATABASE`         | database name (default `wavepalace`) |
| backend  | `FRONTEND_ORIGIN`          | CORS allow-origin                    |
| frontend | `NEXT_PUBLIC_API_BASE_URL` | backend base URL                     |

## MVP scope

Browse curated channels → filter by genre/mood/energy/theme → open a channel →
play visual-audio media in the browser → copy a web link or a VRChat playback
link. Backed by `/health`, `/api/channels`, and `/api/channels/{slug}`.

## Out of scope (MVP)

User accounts, auth, admin/music-director dashboards, DJ/artist submission
forms, payments, ads, uploads, file storage, AI recommendations, analytics,
email automation, team accounts, full CMS, live streaming, and any restreaming
of Spotify / Apple Music / TIDAL / SoundCloud / YouTube / Mixcloud. Third-party
links appear only as "Listen elsewhere" attribution.

## Deployment

See `docs/DEPLOYMENT.md` (Vercel + Render + MongoDB Atlas) and
`docs/MVP_TO_LAUNCH_ROADMAP.md`.

## Definition of Done (MVP)

- [x] Workspace created; frontend and backend run locally
- [x] `/health` works
- [x] Home page renders with ≥ 3 seeded channels
- [x] Filters work
- [x] Channel detail page + sample media player
- [x] Copy Web Link and Copy VRChat Link work
- [x] Friendly error states (API down, media error, 404)
- [x] Backend tests pass (run `pytest`)
- [x] Docs + README present
- [x] Future features documented, not built

## Known limitations

- Seed media are freely-usable placeholders; replace with cleared/licensed media
  before launch (see `docs/LICENSING_NOTES.md`).
- VRChat compatibility depends on the media host and world/player settings.
- Seed mode is in-memory; data resets on restart until MongoDB is configured.
