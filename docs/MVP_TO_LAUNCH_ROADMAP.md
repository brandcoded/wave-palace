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
**Target VRChat stream format (Slice 3):** `stream.wavepalace.live/live/{slug}.ts`

## 2. Complete vertical slices

Add slices one at a time per `FEATURE_SLICES.md`. Slice order:

| Slice | Name | Status | Depends on |
|---|---|---|---|
| 1 | Animated / looping video backgrounds | ✅ COMPLETE (v0.4.0) — admin UI toggle pending Slice 3 | Slice 3 for admin UI toggle |
| 1B | Channel & Host Info Display on Player | ✅ COMPLETE — title, host, genre/mood in overlay; VRChat MP4 overlay parity also complete | None |
| 2 | DJ / Artist submission requests | ✅ COMPLETE — public proposal form, API-backed options, R2 profile image upload, pending submission storage | None |
| 3 | Music director dashboard (Admin UI) | 🔲 NOT STARTED | Auth |
| 3 add-on | Track metadata schema + now-playing display | ✅ COMPLETE — `TrackItem` playlist contract, web overlay, and VRChat MP4 timed now-playing text shipped | None |
| 3 add-on | Play count event tracking | 🔲 NOT STARTED | Slice 3 |
| 4 | Live event streaming — Link-In and Ingest Keys | 🔲 NOT STARTED | Slice 3 + VPS (AzuraCast + SRS provisioned) |
| 5 | Media URL validation & compatibility checker | ✅ COMPLETE | None |
| 6 | Featured / sponsored channels | 🔲 NOT STARTED | None |
| 7 | Production analytics dashboard | 🔲 NOT STARTED | Slice 3 add-ons (play count + track metadata) |
| 8 | Play Metrics + Artist Reporting | 🔲 NOT STARTED | Slice 3 add-ons + Code Capture (Slice 9) for follow/contact data |
| 9 | Code Capture + Follow Intent + Notification Stack | 🔲 NOT STARTED — product spec drafted | Slice 3 (code management in admin UI) + Slice 8 Phase 1–2 (event tracking) |

Each slice ships with UI, API, tests, and docs.

## 3. Production hardening

- Switch from seed mode to MongoDB Atlas (`MONGODB_URI`).
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
| Streaming VPS | Hetzner CPX31 (~$16/mo) | AzuraCast + SRS + FFmpeg — provisioned at Slice 3 |
| CDN / proxy | Cloudflare (free) | HTTPS termination, `stream.wavepalace.live` custom domain |

See `DEPLOYMENT.md` for env vars and steps.

## 5. True streaming architecture (Slice 3 target)

Full detail in `FEATURE_SLICES.md` under "Production streaming architecture."
Summary of what changes at Slice 3:

- Provision Hetzner CPX31 VPS
- Deploy Docker Compose: AzuraCast + SRS + FFmpeg combiner (one process per channel)
- WavePalace FastAPI proxies AzuraCast REST API — admin never touches AzuraCast
- VRChat URL changes from `/muxed/{id}.mp4` to `/live/{slug}.ts`
- Mux approach retired for PC; kept as Quest fallback until HTTP-TS Quest testing confirms compatibility
- Instant track add/delete/update — zero re-encode
- All listeners synchronized in real time

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
- Monitor VPS stream uptime (AzuraCast + SRS) once Slice 3 is provisioned.
- Periodically re-verify VRChat compatibility (host behavior changes).
- Test HTTP-TS Quest compatibility when VPS is live — retire mux MP4 fallback if confirmed.

## 8. Feature update workflow

Pick one slice → branch → build UI + API + data + tests → update `docs/` and
`CHANGELOG.md` → review against `AGENTS.md` → merge → deploy → smoke test.
