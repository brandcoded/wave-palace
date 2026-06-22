# MVP → Launch Roadmap — WavePalace

## 1. MVP build (current)

Walking skeleton + the Public Visual Channel Playback slice. Runs locally with
seed-mode fallback. Backend tests green.

**MVP media architecture decision (locked):**
- Audio and cover image are separate files on Cloudflare R2 (`stream.wavepalace.live`)
- Web player: streams `audioUrl` + renders `coverImageUrl` as background with channel/song info overlay
- VRChat: `vrchatPlaybackUrl` points to a pre-muxed static MP4 (cover image + audio baked in) uploaded to R2
- Animated/looping video backgrounds deferred to Future Slice 1
- Hero copy updated to reflect static image + audio (not "cinematic loops") until video backgrounds ship

**Current VRChat stream format:** `stream.wavepalace.live/muxed/{channel_id}/{slug}.mp4`
**Target VRChat stream format (Slice 4):** `stream.wavepalace.live/live/{slug}.ts`

## 2. Complete vertical slices

Add slices one at a time per `FEATURE_SLICES.md`. Slice order:

| Slice | Name | Status | Depends on |
|---|---|---|---|
| 1 | Animated / looping video backgrounds | ✅ COMPLETE (v0.4.0) — admin UI toggle shipped in Slice 3 | None |
| 1B | Channel & Host Info Display on Player | ✅ COMPLETE — title, host, genre/mood in overlay; VRChat MP4 overlay parity also complete | None |
| 2 | DJ / Artist submission requests | ✅ COMPLETE — public proposal form, API-backed options, R2 profile image upload, pending submission storage | None |
| 3 | Music director admin dashboard | ✅ COMPLETE (v0.7.0) — JWT auth, submission review, channel CRUD, drag-to-reorder, R2 uploads, mobile parity | None |
| 3 add-on | Track metadata schema + now-playing display | ✅ COMPLETE — `TrackItem` playlist contract, web overlay, and VRChat MP4 timed now-playing text shipped | None |
| 3 add-on | Play count event tracking | ✅ COMPLETE (v0.7.0) | None |
| 5 | Media URL validation & compatibility checker | ✅ COMPLETE (v0.8.0) — `POST /api/admin/channels/{slug}/validate-urls` | None |
| 3 add-on | External Stream Passthrough (`liveStreamUrl` + admin UI) | 🔲 NOT STARTED | Slice 3 admin dashboard · no VPS · admin pastes VRCDN/OBS/.ts URL · VRChat-only passthrough · interim path before Slice 4 Link-In |
| 6 | Sponsor Primitive (thin monetization) | ✅ COMPLETE (v0.9.0) | Slice 3 ✅ (admin) — no VPS dep |
| **Pre-Slice 4 add-on** | **Streaming readiness + mux/stream toggle** | **✅ COMPLETE** | `streamingActive` + `vrchatFallbackUrl` schema · admin per-channel toggle + bulk toggle · no VPS dep · activation = flag flip |
| Pre-Slice 4 | Hetzner VPS provisioning (AzuraCast + SRS + FFmpeg) | ⬜ DEFERRED | ~2–3 hrs · CPX32 FSN1 ~$51/mo with backups · see `docs/VPS_PROVISIONING.md` · provision when live events are priority |
| 4 | Live event streaming — Link-In and Ingest Keys | 🔲 NOT STARTED — after Slice 6 | Slice 3 ✅ + VPS provisioned (Hetzner CPX32 FSN1) · toggle infra ships pre-Slice 4, no frontend work at activation · External Stream Passthrough (Slice 3 add-on) covers no-VPS interim path |
| 4 add-on | Event Sponsorship (QR bridge + sponsor frame) | 🔲 WITH Slice 4 | Slice 6 `sponsor` object + Slice 4 streaming path |
| 6B | Full Ad Stack (rotation, CPM, audio stings, reporting) | 🔲 NOT STARTED — after Slice 4 | Slice 4 (AzuraCast for audio stings) · see `MONETIZATION_PLAN.md` |
| 7 | Production analytics dashboard | ✅ COMPLETE | `GET /api/admin/analytics` · summary stat cards · follow breakdown · channel leaderboard · 14 tests |
| 8 | Play Metrics + Artist Reporting | 🔲 NOT STARTED | Slice 3 add-ons + Code Capture (Slice 9) for follow/contact data |
| 9 | Code Capture + Follow Intent + Notification Stack | ✅ COMPLETE | 6-char codes · admin generate/deactivate · `/follow/[code]` landing · Discord OAuth · Resend email opt-in · browser push schema · SMS raises NotImplementedError |
| Legal | DMCA Takedown Form | ✅ COMPLETE | `/legal/takedown` form · `/admin/takedowns` queue · 4 API endpoints · SMTP notification · 15 tests |
| **10** | **Identity & Roles (auth foundation)** | ✅ COMPLETE | Opaque sessions (`wp_session`) · `UserDocument`/`SessionDocument` schemas · `AuthService` · Discord + email magic link + password login · `require_roles` guards · `get_current_admin` shim (no lockout) · `/admin/users` page · 26 tests |
| 11 | Host Onboarding & Ownership | ✅ COMPLETE (v0.14.0) | `Channel.owner_ids` + `auto_publish` · single-use 7-day invite links · `POST /api/host/invite/accept` · `require_channel_owner` dep · admin Ownership panel · `/host/join` page · 19 tests |
| 12 | Host Dashboard | 🔲 NOT STARTED — PLANNED | Slice 11 · scoped `/host` area: own channels, tracks, analytics, edits |

Each slice ships with UI, API, tests, and docs.

## 3. Production hardening

- **[✅ DONE] MongoDB Atlas connected.** `MONGODB_URI` is set on Render. `pymongo[srv]` pinned so `mongodb+srv://` URIs resolve. Atlas seeded idempotently. Admin data persists across restarts. (`9574d94`, `e80ed77`)
- Add request logging, error monitoring, and rate limiting.
- Introduce auth before any dashboard/submission write paths (mux endpoints first).
- Validate and sanitize all media URLs (HTTPS-only).
- Add `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` to Render env vars.
- Add a takedown/removal policy and rights attestation.

## 4. Deployment plan

| Layer | Platform | Notes |
|---|---|---|
| Frontend | Vercel (free) | Next.js — `apps/frontend` |
| Backend API | Render Starter ($7/mo) | FastAPI — `apps/backend` |
| Database | MongoDB Atlas Flex ($8–30/mo) | Metadata only, no binary files |
| Media storage | Cloudflare R2 (~$0–1/mo) | Audio, video, images via `stream.wavepalace.live` |
| Streaming VPS | Hetzner CPX32 FSN1 (~$51/mo with backups) | **DEFERRED** — provision when live events (Slice 4) are priority · AzuraCast + SRS + FFmpeg · see `docs/VPS_PROVISIONING.md` |
| CDN / proxy | Cloudflare (free) | HTTPS termination, `stream.wavepalace.live` custom domain |

See `DEPLOYMENT.md` for env vars and steps.

## 5. True streaming architecture — build now, activate later

Full detail in `FEATURE_SLICES.md` under "Production streaming architecture."

**Current state:** All VRChat playback served from mux MP4 on R2. Mux is fully functional at current scale. VPS deferred — ~$51/mo is a meaningful cost before revenue. Build the streaming infra now, activate it when the VPS is provisioned.

**Pre-Slice 4 add-on (no VPS dep — build now):**
- Add `streamingActive: bool = False` + `vrchatFallbackUrl: str | None` to Channel schema
- Player logic: `streamingActive` flag controls which URL serves VRChat
- Admin per-channel toggle, bulk toggle, mux refresh controls
- Run `POST /api/mux/all` to populate `vrchatFallbackUrl`

**Pre-Slice 4 (when live events become priority — ~2–3 hrs infrastructure):**
- Provision Hetzner CPX32 FSN1 VPS (see `docs/VPS_PROVISIONING.md`)
- Deploy Docker Compose: AzuraCast + SRS + FFmpeg combiner (one process per channel)
- Smoke test: `https://stream.wavepalace.live/live/{slug}.ts` plays in VLC + VRChat

**Slice 4 (code — VPS already running):**
- WavePalace FastAPI proxies AzuraCast REST API — admin never touches AzuraCast
- Live event endpoints (ingest keys + link-in)
- Activation: use existing bulk toggle — no frontend work, no schema migration
- Mux MP4s remain on R2 as warm fallback indefinitely

## 6. Launch checklist

- [x] All MVP "Definition of Done" items pass (see README).
- [x] Playlist cycling implemented — tracks auto-advance, loop, track counter shown.
- [x] Mux service deployed — `POST /api/mux/all` produces VRChat-compatible MP4s on R2.
- [x] Ran `POST /api/mux/all` in production — all 3 channels muxed to 720p MP4s on R2; `vrchatPlaybackUrl` now points to them.
- [x] Animated video loop backgrounds live — `visualLoopUrl` active on all 3 seed channels (v0.4.0).
- [x] Channel & host info in player overlay — title, host name, genre/mood tags in gradient controls bar (Slice 1B).
- [x] VRChat MP4 overlay parity — channel info burned into muxed MP4 via FFmpeg `drawtext`.
- [x] TrackItem now-playing metadata shipped — playlist entries include `url`, `title`, `artist`; web overlay and muxed MP4 output show the current track.
- [ ] Verify muxed MP4s actually play in VRChat (image/video visible + audio + overlay text).
- [ ] Seed media replaced with cleared/licensed media.
- [ ] CORS locked to the production frontend origin.
- [ ] Licensing notes + takedown policy published.
- [ ] Smoke tests pass against deployed URLs.
- [ ] 404 and API-down states verified in production.

## 7. Maintenance plan

- Keep dependencies patched (Next.js, FastAPI, Pydantic).
- Monitor backend health (`/health`) and media-host availability.
- Monitor VPS stream uptime (AzuraCast + SRS) once Slice 4 VPS is provisioned.
- Periodically re-verify VRChat compatibility (host behavior changes).
- Test HTTP-TS Quest compatibility when VPS is live — retire mux MP4 fallback if confirmed.

## 8. Feature update workflow

Pick one slice → branch → build UI + API + data + tests → update `docs/` and
`CHANGELOG.md` → review against `AGENTS.md` → merge → deploy → smoke test.
