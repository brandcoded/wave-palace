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

## API domain & admin cookies (REQUIRED for the admin dashboard)

**The backend must be served from a subdomain of the frontend's domain** — in
production, `api.wavepalace.live` (frontend is `wavepalace.live`). This is not a
cosmetic choice: the admin dashboard authenticates with an httpOnly session
cookie (`wp_admin_token`, set `SameSite=None; Secure`), and the browser only
sends that cookie back if the API is the **same site** as the frontend.

Setup:

- Add `api.wavepalace.live` as a **custom domain** on the Render service, and a
  CNAME for `api` in DNS pointing to the Render target. The `*.wavepalace.live`
  TLS cert covers it.
- Frontend env: `NEXT_PUBLIC_API_BASE_URL = https://api.wavepalace.live`
  (env-only changes do **not** auto-deploy on Vercel — trigger a redeploy).
- Backend env: `FRONTEND_ORIGIN = https://wavepalace.live` (the CORS allow-origin
  stays the **frontend** origin, not the API). CORS uses
  `allow_credentials=True`, so the origin must be an exact match, never `*`.

### Third-party-cookie failure mode (watch for this)

If the API is served from a **different site** than the frontend (e.g. the raw
`*.onrender.com` URL, or any unrelated domain), admin login appears to succeed
(`POST /api/admin/login` returns 200 and sets the cookie) but every following
request fails: `GET /api/admin/me` returns **401** and the admin dashboard
renders **blank**. Cause: the cookie is third-party, so Chrome/Safari store it
on the login response but refuse to send it on the cross-site `me` request.
The fix is always to put the API back on an `api.` subdomain of the frontend so
the cookie is same-site (confirm `sec-fetch-site: same-site` on the `me`
request). Do **not** "simplify" the API back to the onrender URL — it silently
breaks admin auth.

## Database — MongoDB Atlas (optional for MVP)

- Create a free cluster and a `channels` collection in database `wavepalace`.
- Each document matches the Channel schema in `API_CONTRACT.md`.
- Set `MONGODB_URI` on the backend; the app switches off seed mode automatically.

## Environment variables

| Service  | Variable                  | Notes                                  |
|----------|---------------------------|----------------------------------------|
| backend  | `MONGODB_URI`             | empty = seed mode                      |
| backend  | `MONGODB_DATABASE`        | default `wavepalace`                   |
| backend  | `FRONTEND_ORIGIN`         | CORS allow-origin = **frontend** origin (`https://wavepalace.live`); exact match, never `*` |
| backend  | `ADMIN_SECRET`            | admin login secret                     |
| backend  | `JWT_SECRET`              | signs the `wp_admin_token` session JWT |
| frontend | `NEXT_PUBLIC_API_BASE_URL`| backend base URL = **`api.` subdomain of the frontend** (`https://api.wavepalace.live`) so admin cookies are same-site |

## Smoke test checklist

- [ ] `GET /health` returns `{"status":"ok"}`.
- [ ] Home page lists at least 3 channels; filters work.
- [ ] Channel detail page plays sample media.
- [ ] Copy Web Link and Copy VRChat Link both confirm.
- [ ] Unknown slug shows the 404 page.
- [ ] Backend-down state shows the friendly error.
- [ ] Admin login at `/admin/login` loads the dashboard (not blank); the `me`
      request returns 200 with `sec-fetch-site: same-site`.
