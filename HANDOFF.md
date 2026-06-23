# WavePalace — Agent Handoff Document

> For seamless handoffs between **Claude Code** and **Codex**. Read this before touching any code.
> Last updated: 2026-06-22

---

## What WavePalace is

Visual radio web app — curated music channels with cinematic backdrops, shareable as web links and VRChat playback URLs. Think Music Choice for VRChat lounges and digital spaces.

**Not:** a Spotify clone, a live-streaming platform, a social network, or a CMS. Stay narrow.

---

## Repo layout

```
wave-palace/
  apps/
    frontend/          Next.js (App Router) · TypeScript · Tailwind
    backend/           FastAPI · Pydantic · Python
  docs/                Product brief, architecture, API contract, feature slices,
                       roadmap, deployment, licensing notes, changelog
  AGENTS.md            Rules every coding agent must follow
  HANDOFF.md           ← this file
  README.md
  WavePalace_Revenue_Model.xlsx   ← NOT committed — local only
  build_revenue_model.py          ← NOT committed — local only
```

---

## Current state (as of 2026-06-22)

> **Production deploy:** `origin/main` is at `e286d7e`. **Slice 10 (Identity &
> Roles)** and **Slice 11 (Host Onboarding & Ownership)** shipped at `34878d7`
> (now an ancestor) and are live. Since then, additional work landed on `main`:
> `/creators` + `/listeners` landing routes, global nav/button polish, and a
> **Vercel build fix** (`e286d7e` — framer-motion `Variants` typing) that resolved
> a failed frontend build. Render (backend) + Vercel (frontend) auto-deploy on push
> to `main`. Still smoke-test the host invite flow + Discord login on `/host/join`
> against the live environment. MongoDB Atlas connected, so `channel_invites` /
> `owner_ids` / `auto_publish` persist.

### What is COMPLETE and committed

| Slice | Feature | Version / Commit |
|---|---|---|
| MVP | Public visual channel playback — browse, filter, play, copy links | v0.1.0 |
| MVP | Playlist cycling + track counter | v0.2.0 |
| MVP add-on | VRChat MP4 mux service (`POST /api/mux/all`) | v0.3.0 |
| 1 | Looping video backdrops (`visualLoopUrl` on web player + mux) | v0.4.0 |
| 1B | Channel & host info in player overlay (title, host, genre/mood) | v0.5.0 |
| 1B add-on | VRChat MP4 overlay parity — channel info burned into MP4 via FFmpeg `drawtext` | v0.5.0 |
| 3 add-on | `TrackItem` schema (`url`, `title`, `artist`) replacing flat playlist strings | main (pre-Slice 2) |
| 3 add-on | Web player now-playing display ("Artist — Track Title" per track) | main (pre-Slice 2) |
| 2 | DJ / Artist submission form — public form → pending queue, profile image upload | v0.6.0 |
| 3 | Music director admin dashboard — JWT auth, submission review, channel CRUD, drag-to-reorder, R2 uploads | v0.7.0 |
| 3 add-on | Play count event tracking (`POST /api/channels/{slug}/play`) | v0.7.0 |
| 3 | Admin UI mobile parity | `88a40a5` |
| 5 | Media URL validation & compatibility checker — `POST /api/admin/channels/{slug}/validate-urls` | v0.8.0 |
| 6 | Sponsor Primitive — `sponsor` object on Channel, admin panel, web player overlays, VRChat drawtext parity, impression/click tracking | v0.9.0 |
| Pre-Slice 4 add-on | Streaming readiness + mux/stream toggle — `streamingActive` + `vrchatFallbackUrl` schema, admin toggle, bulk endpoint | `f34b343` |
| 9 | Code Capture + Follow Intent + Notification Stack — 6-char codes, `/follow/[code]`, Discord OAuth, email double opt-in, `/follows`, admin `/admin/codes`, 19 backend tests | `459e67d` |
| 9 add-on | Per-track mux codes burned into VRChat overlay | `94a0f49` |
| Legal | DMCA Takedown Form — public `/legal/takedown`, admin queue `/admin/takedowns`, SMTP email, 20 backend tests | `3104e62` |
| Infra | MongoDB Atlas connected — `MONGODB_URI` set on Render, `pymongo[srv]` pinned, idempotent seed | `9574d94` |
| **10** | **Identity & Roles** — opaque `wp_session` cookie, `UserDocument`/`SessionDocument`, Discord+email-link+password auth, `require_roles` guards, `/admin/users` page, 26 tests | main |
| **11** | **Host Onboarding & Ownership** — `Channel.owner_ids` + `auto_publish`, single-use 7-day invite links, `require_channel_owner` dep, admin Ownership panel, `/host/join` page, 19 tests | main |

### What is NOT STARTED / DEFERRED

| Slice | Feature | Depends on |
|---|---|---|
| 3 add-on | External Stream Passthrough (`liveStreamUrl` + admin UI) | Slice 3 ✅ — no VPS |
| Pre-Slice 4 | Hetzner CPX32 FSN1 VPS provisioning | ⬜ DEFERRED — provision when live events are priority |
| 4 | Live event streaming — Link-In + Ingest Keys | Slice 3 ✅ + VPS provisioned |
| 4 add-on | Event Sponsorship (QR bridge + sponsor frame) | Slice 6 `sponsor` object + Slice 4 streaming path |
| 6B | Full Ad Stack (rotation, CPM, audio stings, reporting) | Slice 4 ✅ (AzuraCast for audio stings) |
| 8 | Play Metrics + Artist Reporting | Slice 3 add-ons ✅ + Slice 9 ✅ |
| 12 | Host Dashboard | ⬜ PLANNED — Slice 11 ✅ · scoped `/host` area: own channels, tracks, analytics, edits · uses `require_channel_owner` + `get_channels_by_owner` |

**Slices 6, 7, 9, 10, 11, Pre-Slice 4 add-on, and DMCA are all complete.** The next build options are: **Slice 12 — Host Dashboard** (the scoped `/host` area; everything it needs — ownership, `require_channel_owner`, `get_channels_by_owner` — shipped in Slice 11), **External Stream Passthrough** (small, no VPS), **Slice 8 artist reporting**, or **provision Hetzner VPS → Slice 4 live events**. Rationale + copy-paste build prompts: `docs/MONETIZATION_PLAN.md`.

> **Note on auth:** "Introduce auth before dashboard/submission write paths" (roadmap §3) is delivered by **Slice 10** (real user identity + stackable roles). **Slice 11** adds channel ownership (`owner_ids`) and the invite flow on top; **Slice 12** (host dashboard) is the remaining piece of the host program.

**Build one slice at a time. Do not start a slice until the previous one is merged and smoke-tested.**

### Streaming deferral + toggle infrastructure (pre-Slice 4 add-on)

All VRChat playback currently served from mux MP4 (`vrchatFallbackUrl`) on R2.
`streamingActive = False` on all channels. Streaming infrastructure is deferred
until Slice 4 (live events) becomes a priority — CPX32 FSN1 at ~$51/mo is a
meaningful ongoing cost before the product generates revenue.

**VRChat URL routing chain (three tiers, evaluated in order):**
1. `liveStreamUrl` set → external passthrough (creator's infrastructure — VRCDN, OBS/.ts, .mp4)
2. `streamingActive = true` → WavePalace live stream (`live/{slug}.ts` via SRS on VPS)
3. Default → mux MP4 (`vrchatFallbackUrl` on R2)

**Schema fields (pre-Slice 4 add-on + Slice 3 add-on):**
- `liveStreamUrl: str | None` — Slice 3 add-on · admin-settable via channel editor · VRChat-only (web player uses `playlist` MP3s regardless) · no overlay burned in · cleared when reverting to mux/streaming
- `streamingActive: bool = False` — pre-Slice 4 add-on · controls tier 2 routing · default False (all channels start on mux)
- `vrchatFallbackUrl: str | None` — pre-Slice 4 add-on · permanent mux MP4 URL · populated by `POST /api/mux/all` · never overwritten by streaming cutover

**Admin controls (pre-Slice 4 add-on, no VPS dependency):**
- Per-channel streaming toggle: `Live Stream ↔ Mux MP4`
- Bulk toggle: flip all channels at once (emergency fallback or first activation)
- Mux refresh: per-channel and all-channels buttons
- External Stream URL field: paste VRCDN/OBS/.ts URL → sets `liveStreamUrl`

**VRCDN note:** Prior decision "No VRCDN — all streaming self-hosted" applies to WavePalace's own infrastructure. Passthrough of a creator's existing VRCDN URL via `liveStreamUrl` is acceptable — WavePalace consumes their stream, not the VRCDN platform.

When the VPS is provisioned (Slice 4), activation = verify streams → run `POST /api/mux/all` → use bulk toggle. No code changes, no deploy.

### Slice 9 — shipped

Slice 9 is complete. Code capture (`CodeInput` pill in site header), `/follow/[code]` landing page, Discord OAuth + bot DM, Resend email double opt-in, `/follows` listener preferences page, admin `/admin/codes` page, Follow Codes panel on channel edit, per-track codes burned into VRChat overlay. 19 backend tests. SMS/Twilio remains permanently deferred (`NotImplementedError`).

### Local-only / worktree notes

Check `git status` before every commit. This worktree may contain unrelated
local changes from the user or another agent; stage only the files needed for
the current slice or docs cleanup.

| File | Status |
|---|---|
| `WavePalace_Revenue_Model.xlsx` | Business/revenue model — keep local, do not commit unless explicitly requested |
| `build_revenue_model.py` | Script that built the xlsx — keep local, do not commit unless explicitly requested |

### Launch checklist — remaining items

- [ ] Verify muxed MP4s actually play in VRChat (image/video visible + audio + overlay text)
- [ ] Replace seed media with cleared/licensed media
- [ ] Lock CORS to production frontend origin (`FRONTEND_ORIGIN` env var on Render)
- [ ] Publish licensing notes + takedown policy
- [ ] Smoke tests pass against deployed URLs
- [ ] 404 and API-down states verified in production

---

## Local development

### Backend

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # leave MONGODB_URI empty → seed mode, no DB needed
uvicorn app.main:app --reload --port 8000
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Seed mode: 3 published channels + 1 unpublished

### Frontend

```bash
cd apps/frontend
npm install
cp .env.example .env.local    # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev                   # port 3000 (or 3001 per .claude/launch.json)
```

### Tests

```bash
cd apps/backend
pytest
```

All tests must stay green. Add tests for every backend change.

---

## Environment variables

### Backend (`apps/backend/.env`)

| Variable | Required | Notes |
|---|---|---|
| `MONGODB_URI` | No | Empty = seed mode |
| `MONGODB_DATABASE` | No | Default: `wavepalace` |
| `FRONTEND_ORIGIN` | Yes (prod) | CORS allow-origin — Vercel URL in production |
| `R2_ACCOUNT_ID` | Mux only | Cloudflare R2 dashboard → Manage R2 API Tokens |
| `R2_ACCESS_KEY_ID` | Mux only | Same |
| `R2_SECRET_ACCESS_KEY` | Mux only | Same |
| `R2_BUCKET_NAME` | Mux only | Default: `wavepalace-media` |
| `R2_PUBLIC_BASE_URL` | Mux only | Default: `https://stream.wavepalace.live` |
| `FONT_PATH` | Mux only | Default: `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf` |

### Slice 9 backend additions (active — added to Render at Slice 9)

| Variable | Service | Notes |
|---|---|---|
| `DISCORD_BOT_TOKEN` | Render | Discord bot for DM notifications |
| `DISCORD_CLIENT_ID` | Render | Discord OAuth2 client ID |
| `VAPID_PUBLIC_KEY` | Render | Web Push API — generate once with `py-vapid` |
| `VAPID_PRIVATE_KEY` | Render | Web Push API — generate once with `py-vapid` |

### Slice 10 backend additions (active — added to Render at Slice 10)

| Variable | Service | Notes |
|---|---|---|
| `DISCORD_CLIENT_SECRET` | Render | Discord OAuth2 client secret (admin login + follow flow) |
| `DISCORD_REDIRECT_URI` | Render | Must be `https://api.wavepalace.live/api/auth/discord/callback` |
| `RESEND_API_KEY` | Render | Email magic-link delivery — free tier sufficient |
| `JWT_SECRET` | Render | **Required** — signs Discord OAuth state tokens; default in source is public, must be set in prod |
| `ADMIN_SECRET` | Render | Break-glass admin login secret — rotate if ever shared or committed |

**Future (not active — do not add to Render until SMS is activated):**

| Variable | Notes |
|---|---|
| `TWILIO_ACCOUNT_SID` | Requires A2P 10DLC carrier registration + TCPA compliance |
| `TWILIO_AUTH_TOKEN` | Same |
| `TWILIO_FROM_NUMBER` | Same |

### Frontend (`apps/frontend/.env.local`)

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Yes | `http://localhost:8000` locally; HTTPS URL in prod |

---

## Architecture in one page

```
[Next.js frontend — Vercel]
  src/app/                    App Router: / · /channels/[slug] · /submit · /admin/* · /follow/[code] · /follows · /host/join
  src/presentation/           Pure visual components (AppShell, GlassPanel, …)
  src/features/channels/      Channel browsing + player
    lib/                      Typed API client
    types/                    TypeScript types
    components/               ChannelGrid, ChannelCard, ChannelPlayer, CopyLinkButton, …
  src/features/admin/         Admin dashboard (auth-gated)
    lib/adminApi.ts           Typed admin API client
    types/admin.ts            Admin TypeScript types
    components/               Submission review, channel editor, track list (dnd-kit)
          ↓ fetch
[FastAPI backend — Render]
  app/api/routes/             channels · health · mux · submissions · admin · play
  app/services/               channel_service · mux_service · submission_service · admin_service
  app/repositories/           SeedChannelRepository / MongoChannelRepository · R2Repository
                              SubmissionRepository (Seed + Mongo)
  app/schemas/                Channel · TrackItem · ExternalLink · ChannelSubmission
  app/seed/                   In-memory seed channels + submission options
          ↓ optional
[MongoDB Atlas]               channels · submissions · submission_options collections
          ↓
[Cloudflare R2]               stream.wavepalace.live — MP3s, images, video loops,
                              muxed VRChat MP4s, submission profile images
```

**Key invariant:** route handlers are thin transport. Business rules live in services. The service layer never touches HTTP or the DB driver directly.

### Current Channel schema

```python
class TrackItem(BaseModel):
    url: str
    title: str = ""
    artist: str = ""

class Channel(BaseModel):
    id: str
    slug: str
    title: str
    description: str
    genre: str
    mood: str
    energy: str
    theme: str
    hostName: str
    coverImageUrl: HttpUrl
    visualLoopUrl: str | None      # looping MP4; falls back to coverImageUrl
    audioUrl: HttpUrl              # = playlist[0], kept for backwards compat
    playlist: list[TrackItem]      # ordered, cycles on web player
    vrchatPlaybackUrl: str
    externalLinks: list[ExternalLink]
    rightsStatus: str
    isPublished: bool
    # Planned fields (not yet built):
    liveStreamUrl: str | None = None          # Slice 3 add-on — external passthrough URL
    streamingActive: bool = False             # Pre-Slice 4 add-on — routes VRChat to live/{slug}.ts
    vrchatFallbackUrl: str | None = None      # Pre-Slice 4 add-on — permanent mux MP4 URL
```

### Media architecture (current — "mux" approach)

- **Web player:** streams `audioUrl`, cycles `playlist`, shows `visualLoopUrl` or `coverImageUrl` as backdrop
- **VRChat:** `vrchatPlaybackUrl` → pre-muxed MP4 on R2 — full playlist audio + visual baked in, channel info via `drawtext`
- **True streaming (Slice 4 + VPS):** AzuraCast + SRS + FFmpeg combiner on Hetzner CPX32 FSN1; VRChat URL becomes `live/{slug}.ts` — full spec in `docs/FEATURE_SLICES.md`

---

## API surface (current)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | `{"status":"ok"}` |
| GET | `/api/channels` | None | Published channels; filter by `genre`, `mood`, `energy`, `theme` |
| GET | `/api/channels/{slug}` | None | Single channel; 404 if missing/unpublished |
| POST | `/api/channels/{slug}/play` | None | Increment play count |
| GET | `/api/submission-options` | None | Genre/mood/energy/theme option lists for submit form |
| POST | `/api/submissions/upload-image` | None | Upload profile image to R2 (10/IP/hr rate limit) |
| POST | `/api/submissions` | None | Create pending channel submission |
| POST | `/api/channels/{slug}/mux` | None (Render shell) | Mux one channel → R2 |
| POST | `/api/mux/all` | None (Render shell) | Mux all channels (background job) |
| GET | `/api/mux/status` | None | Poll mux job |
| GET | `/api/admin/submissions` | JWT cookie | List pending/reviewed submissions |
| PATCH | `/api/admin/submissions/{id}` | JWT cookie | Approve / reject submission |
| GET | `/api/admin/channels` | JWT cookie | List all channels (incl. unpublished) |
| POST | `/api/admin/channels` | JWT cookie | Create channel |
| PATCH | `/api/admin/channels/{slug}` | JWT cookie | Update channel metadata / tracks |
| DELETE | `/api/admin/channels/{slug}` | JWT cookie | Delete channel |
| POST | `/api/admin/channels/{slug}/upload-image` | JWT cookie | Upload cover image to R2 |
| POST | `/api/admin/channels/{slug}/upload-video` | JWT cookie | Upload visual loop to R2 |
| POST | `/api/admin/channels/{slug}/upload-audio` | JWT cookie | Upload track MP3 to R2 |

Full shapes: `docs/API_CONTRACT.md`.

---

## Deployment

| Layer | Platform | Config |
|---|---|---|
| Frontend | Vercel | Root Dir: `apps/frontend`; env: `NEXT_PUBLIC_API_BASE_URL` |
| Backend API | Render Starter ($7/mo) | Root Dir: `apps/backend`; start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Database | MongoDB Atlas Flex ($8–30/mo) | Set `MONGODB_URI` on Render to leave seed mode |
| Media storage | Cloudflare R2 (~$0–1/mo) | `stream.wavepalace.live` custom domain |
| Streaming VPS | Hetzner CPX32 FSN1 (~$51/mo with backups) | **DEFERRED** — provision when Slice 4 (live events) becomes priority · 4 vCPU / 8 GB / Ubuntu 22.04 / FSN1 — see `docs/VPS_PROVISIONING.md` |

**Service dependencies (active at Slice 4):**
- **Hetzner Cloud** — `hetzner.com/cloud`, project `wavepalace`, CPX32 FSN1 (Falkenstein)
- **AzuraCast** — Docker, self-hosted on VPS; admin access at `azuracast.wavepalace.live` (WavePalace FastAPI proxies all calls — admin never opens AzuraCast directly)
- **SRS (Simple Realtime Server)** — Docker, self-hosted on VPS; ports 1935 (RTMP in), 1985 (HTTP API), 8080 (HTTP-TS out)
- **FFmpeg** — systemd services on VPS, one per channel (combines Icecast audio + R2 visual loop → RTMP → SRS)

**DNS (add before Slice 4):**
- `stream.wavepalace.live` A record → VPS IP, Cloudflare proxy **OFF** (DNS only, grey cloud)
- HTTP-TS requires direct connection; Cloudflare proxy does not handle it on the free plan; HTTPS termination happens on the VPS

**Note:** Admin auth uses a JWT cookie. The cookie must be set as `Secure; SameSite=Strict`. Because the frontend is on Vercel (`wavepalace.live`) and the API is on Render (`api.wavepalace.live`), both must share the `wavepalace.live` parent domain for same-site cookies — the Render service must be accessed via `api.wavepalace.live` (custom domain), not the default `*.onrender.com` URL.

After any mux-affecting deploy: run `POST /api/mux/all` + purge Cloudflare cache for `stream.wavepalace.live/muxed/`.

Full deploy steps: `docs/DEPLOYMENT.md`.

---

## Rules every agent must follow (from `AGENTS.md`)

1. **One vertical slice at a time.** Ship UI + API + tests + docs before starting another.
2. **Do not overbuild.** No features beyond what is explicitly requested.
3. **Layer separation is load-bearing.** Route handlers = thin. Business logic = services. Data = repositories.
4. **Third-party streaming links are attribution only.** Spotify, YouTube, SoundCloud etc. are "Listen elsewhere" — never playback sources.
5. **Update docs + CHANGELOG** for every feature change.
6. **Backend tests stay green.** Add tests for every backend change.
7. **Visual direction: dark, immersive, cinematic, glassy, music-forward.** Not a SaaS dashboard.

---

## Recommended next actions

1. **Pre-Slice 4 add-on (Streaming readiness + toggle)** — schema + admin UI, no VPS dep. `streamingActive` + `vrchatFallbackUrl` + per-channel toggle + bulk flip.
2. **Slice 4 (Live event streaming)** — follows Pre-Slice 4 add-on. Full spec in
   `docs/FEATURE_SLICES.md`. Requires VPS provisioning (Hetzner CPX32 FSN1 +
   Docker Compose: AzuraCast + SRS + FFmpeg — see `docs/VPS_PROVISIONING.md`).
   Build the Event-Sponsorship add-on (QR bridge) alongside it.
3. **VRChat smoke test** — verify muxed MP4s play in an actual VRChat world.
4. **Keep Slice 9 as planned scope only** until explicitly requested; the current product spec is documentation, not implementation authorization.

---

## Key docs map

| Doc | What's in it |
|---|---|
| `AGENTS.md` | Rules for coding agents — read first |
| `docs/STATUS.md` | Canonical slice status (this is authoritative) |
| `docs/FEATURE_SLICES.md` | Full spec for every slice, including true streaming architecture |
| `docs/MONETIZATION_PLAN.md` | Ad/sponsorship inventory, build sequence (Sponsor Primitive before Slice 4), and copy-paste build prompts |
| `docs/MVP_TO_LAUNCH_ROADMAP.md` | Status table, launch checklist, deployment plan |
| `docs/ARCHITECTURE.md` | Layer diagram and design rationale |
| `docs/API_CONTRACT.md` | Full request/response shapes |
| `docs/DEPLOYMENT.md` | Step-by-step deploy instructions |
| `docs/VPS_PROVISIONING.md` | Hetzner CPX32 FSN1 VPS setup — AzuraCast + SRS + FFmpeg, smoke test checklist |
| `docs/CHANGELOG.md` | Version history with rationale |
| `docs/LICENSING_NOTES.md` | Media rights and seed data notes |
