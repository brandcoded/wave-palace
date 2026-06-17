# Deployment — WavePalace

## Local development

Backend:

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # leave MONGODB_URI empty for seed mode
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd apps/frontend
npm install
cp .env.example .env.local    # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Visit `http://localhost:3000`. The backend serves `http://localhost:8000`
(`/docs` for Swagger).

## Frontend — Vercel

- Import the repo; set **Root Directory** to `apps/frontend`.
- Framework preset: Next.js (auto-detected).
- Env var: `NEXT_PUBLIC_API_BASE_URL` = your deployed backend URL (https).
- Deploy. Vercel handles build (`next build`) and hosting.

## Backend — Render

- New **Web Service** from the repo; **Root Directory** `apps/backend`.
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env vars: `FRONTEND_ORIGIN` = your Vercel URL; optionally `MONGODB_URI` and
  `MONGODB_DATABASE` to leave seed mode.

## Database — MongoDB Atlas (optional for MVP)

- Create a free cluster and a `channels` collection in database `wavepalace`.
- Each document matches the Channel schema in `API_CONTRACT.md`.
- Set `MONGODB_URI` on the backend; the app switches off seed mode automatically.

## Environment variables

| Service  | Variable                  | Notes                                  |
|----------|---------------------------|----------------------------------------|
| backend  | `MONGODB_URI`             | empty = seed mode                      |
| backend  | `MONGODB_DATABASE`        | default `wavepalace`                   |
| backend  | `FRONTEND_ORIGIN`         | CORS allow-origin                      |
| frontend | `NEXT_PUBLIC_API_BASE_URL`| backend base URL                       |

## Smoke test checklist

- [ ] `GET /health` returns `{"status":"ok"}`.
- [ ] Home page lists at least 3 channels; filters work.
- [ ] Channel detail page plays sample media.
- [ ] Copy Web Link and Copy VRChat Link both confirm.
- [ ] Unknown slug shows the 404 page.
- [ ] Backend-down state shows the friendly error.
