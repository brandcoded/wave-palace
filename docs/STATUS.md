# WavePalace — Implementation Status

> Single source of truth for slice status. Update this file whenever a slice
> ships or changes state. `CLAUDE.md` carries a compact copy — keep both in sync.
> Last updated: 2026-06-22 (Slice 11 — Host Onboarding & Ownership complete)
> Production: `origin/main` @ `e286d7e` — Slices 10 + 11 live (shipped at `34878d7`); since-then landing routes (`/creators`, `/listeners`), nav polish, and a Vercel build fix also deployed.
>
> **Hours worked** column counts all time on a slice: PM prep, prompt writing,
> build sessions, debugging, testing, and deploy. Pre-column-add slices show `—`.

---

## Slice status

| Slice | Feature | Status | Hrs | Notes |
|---|---|---|---|---|
| MVP | Public visual channel playback | ✅ COMPLETE (v0.1.0) | 7 | Browse, filter, play, copy links, error states |
| MVP | Playlist cycling + track counter | ✅ COMPLETE (v0.2.0) | 11 | Tracks auto-advance, loop, counter shown |
| MVP add-on | VRChat MP4 mux service | ✅ COMPLETE (v0.3.0) | 11 | `POST /api/mux/all`, `POST /api/channels/{slug}/mux`, R2 upload |
| 1 | Animated video loop backgrounds | ✅ COMPLETE (v0.4.0) | 15 | `visualLoopUrl` live on web player + mux · Admin UI toggle shipped in Slice 3 (v0.7.0) |
| 1B | Channel & host info in player overlay | ✅ COMPLETE (v0.5.0) | 4 | Title, host name, genre/mood in gradient bar |
| 1B add-on | VRChat MP4 overlay parity | ✅ COMPLETE (v0.5.0) | 7 | Channel info burned into MP4 via FFmpeg `drawtext` |
| 3 add-on† | TrackItem schema (`url`, `title`, `artist`) | ✅ COMPLETE (main) | 6 | Replaces flat `playlist: string[]` |
| 3 add-on† | Now-playing display | ✅ COMPLETE (main) | — | "Artist — Track Title" shown in web player (counted in TrackItem row) |
| 2 | DJ / Artist submission form | ✅ COMPLETE (v0.6.0) | 13 | Public form → pending queue · Profile image upload to R2 · Multi-select chips from API · `submissions.py` routes + service + repo + tests |
| 3 | Music director admin dashboard | ✅ COMPLETE (v0.7.0) | 20 | JWT cookie auth · Submission review queue · Channel CRUD + drag-to-reorder tracks · R2 media uploads · Options management |
| 3 add-on | Play count event tracking | ✅ COMPLETE (v0.7.0) | 3 | `POST /api/channels/{slug}/play` · in-memory rate limit · sessionStorage gate on web player |
| 3 add-on | External Stream Passthrough | ⬜ NOT STARTED | — | `liveStreamUrl` field · admin pastes VRCDN/OBS/.ts URL → VRChat players hit external stream directly · no VPS · VRChat-only (web player uses playlist MP3s) · no overlay burned in · tradeoffs: no uptime control, URL tied to creator's infra |
| Pre-Slice 4 add-on | Streaming readiness + mux/stream toggle | ✅ COMPLETE | 13 | `streamingActive` + `vrchatFallbackUrl` on Channel schema · `PATCH /api/admin/channels/{slug}` accepts both fields · `POST /api/admin/channels/streaming/bulk` flips all channels · admin edit page: streaming toggle + live stream URL field in VRChat section · admin channels list: "Activate / Deactivate Streaming" bulk button · public API exposes both fields · 7 new backend tests · no VPS required |
| **6** | **Sponsor Primitive (thin monetization)** | **✅ COMPLETE (v0.9.0)** | **22** | `sponsor` object on Channel · admin PATCH endpoint + edit-page panel (name, logo, text, CTA URL, placement, date window, active/featured toggles, impression/click counters) · web player overlays (logo bug, lower-third text, pause-screen takeover) · directory featured-pin + "Sponsored" badge · VRChat parity (sponsor text burned into drawtext) · impression/click tracking with 30-min TTL rate limit · 22 backend tests · No VPS dep |
| Pre-Slice 4 | Hetzner VPS provisioning | ⬜ DEFERRED | — | CPX32 FSN1 · 4 vCPU / 8 GB · Ubuntu 22.04 · ~$42/mo base (~$51 with backups) · AzuraCast + SRS + FFmpeg · provision when live events become priority · see `docs/VPS_PROVISIONING.md` |
| **Pre-Slice 4 add-on** | **Streaming readiness + mux/stream toggle** | **✅ COMPLETE** | — | (counted in row above) |
| 4 | Live event streaming — Link-In + ingest keys | ⬜ AFTER Pre-Slice 4 | — | OBS push · HLS/RTMP/SRT pull · AzuraCast DJ mode · Requires VPS provisioned · toggle infra ships pre-Slice 4 so no frontend work needed here |
| 4 add-on | Event Sponsorship (QR bridge + sponsor frame) | ⬜ WITH Slice 4 | — | Event-sponsor intro frame + QR-code bridge baked into the live MP4 · Depends on Slice 6 `sponsor` object + Slice 4 streaming path |
| 5 | Media URL validation & compatibility checker | ✅ COMPLETE (v0.8.0) | 7 | `POST /api/admin/channels/{slug}/validate-urls` · HTTPS/reachability/content-type/VRChat-compat checks · "Check URLs" button in admin channel edit |
| 6B | Full Ad Stack | ⬜ AFTER Slice 4 | — | Multi-sponsor rotation · web CPM measurement · intro/outro splash · idle card · opt-in audio stings (AzuraCast) · sponsor reporting dashboard · See `MONETIZATION_PLAN.md` |
| 7 | Production analytics dashboard | ✅ COMPLETE | 11 | `GET /api/admin/analytics` · admin-auth required · total plays/follows/channels/sponsors summary cards · follow breakdown by channel (Discord/Email/Push) · channel leaderboard sorted by playCount desc · unpublished channels shown muted · no PII exposed · 14 backend tests · `/admin/analytics` page |
| 8 | Play Metrics + Artist Reporting | ⬜ NOT STARTED | — | PM plan complete · Depends on Slice 3 add-ons + Slice 9 |
| **10** | **Identity & Roles (auth foundation)** | **✅ COMPLETE** | 8 | Opaque server-side sessions (`wp_session` cookie, 30-day TTL) · `UserDocument` + `SessionDocument` + `EmailLoginTokenDocument` schemas · `SeedUserRepository` + `MongoUserRepository` + `SeedSessionRepository` + `MongoSessionRepository` · `AuthService`: bootstrap admin, session issue/revoke, Discord upsert, email magic link (Resend), password bcrypt · `get_current_user` FastAPI dep (wp_session + grace-period JWT fallback) · `require_roles(*roles)` factory · `get_current_admin` shim (no lockout) · `POST /api/admin/login` now issues `wp_session` · `GET /api/auth/me`, `POST /api/auth/logout`, `POST /api/auth/email/request`, `GET /api/auth/email/verify`, `POST /api/auth/register`, `POST /api/auth/login` · `GET/PATCH /api/admin/users` · `POST /api/auth/discord/initiate?intent=login`, generalized callback · admin login page: Discord + email-link + secret tabs · `SignInPanel.tsx` component · `/admin/users` management page (role editor, activate/deactivate) · Users nav item (admin-only) · `displayName` in sidebar · 26 backend tests · TS clean |
| **11** | **Host Onboarding & Ownership** | **✅ COMPLETE (v0.14.0)** | — | `Channel.owner_ids` + `auto_publish` (admin-only, stripped from public API) · `ChannelInviteToken` schema + `InviteRepository` (Seed + Mongo, `channel_invites`) · single-use 7-day SHA-256-hashed tokens · `InviteService` generate/accept/list · `POST/GET /api/admin/channels/{slug}/invites` · `POST /api/host/invite/accept` · `GET /api/admin/channels/{slug}/owners` · `require_channel_owner` dep (admin/MD bypass) · `get_channels_by_owner` repo method · admin Ownership panel (hosts, remove, invite link, auto_publish toggle) · `/host/join?token=` page with `SignInPanel` · 19 backend tests (251 total) · TS clean |
| 12 | Host Dashboard | ⬜ NOT STARTED — PLANNED | — | After Slice 11 · scoped `/host` area: own channels, tracks, analytics, edits |
| Legal | DMCA Takedown Form (`/legal/takedown` + admin queue) | ✅ COMPLETE | 13 | Public form → `POST /api/takedowns` · admin queue `/admin/takedowns` · status flow pending→reviewed→actioned/dismissed · best-effort SMTP email to `ADMIN_EMAIL` · MongoDB-backed with seed fallback · 15 backend tests · `/legal` index page |
| 9 | Code Capture + Follow Intent + Notification Stack | ✅ COMPLETE | 26 | 6-char alphanumeric codes · admin generate/deactivate UI · public `/follow/[code]` landing · Discord OAuth confirmed-instantly · email double opt-in via Resend · browser push schema only · SMS raises NotImplementedError · `/follows` listener page · admin `/admin/codes` page · Follow Codes panel on channel edit page · `CodeInput` pill in site header · `POST/GET /api/admin/codes` · `GET /api/codes/{code}` · `POST /api/codes/{code}/follow` · `POST /api/follows/confirm` · `GET/PATCH/DELETE /api/follows` · Discord OAuth `/api/auth/discord/initiate` + `/callback` · 19 backend tests (146 total) · build clean |

† TrackItem / now-playing shipped in commits `2d3a72c`, `2ee4fa2`, `e2385bc` before Slice 2 was merged; status docs now reflect that it already shipped.

---

## Mux deferral tradeoffs — accepted at current scale

| Limitation | Impact | Gate |
|---|---|---|
| VRChat worlds not synchronized — each listener starts MP4 at a different time | Low | No listener expectation of sync yet |
| Playlist updates require re-mux (1–15 min encode) | Low | Stable playlists, infrequent changes |
| Practical track limit ~15–20 per channel | Low | Current channels well under limit |
| Live events (Slice 4) completely blocked | **Hard dependency** | VPS must be provisioned first |
| No server-side now-playing source of truth | Low | Web player tracks index locally |

Revisit when any limit is hit or the first live event is scheduled.

---

## Launch checklist — remaining items

- [ ] Verify muxed MP4s play in VRChat (image/video visible + audio + overlay text)
- [ ] Replace seed media with cleared/licensed media
- [ ] Lock CORS to production frontend origin (`FRONTEND_ORIGIN` env var on Render)
- [ ] Publish licensing notes + takedown policy
- [ ] Smoke tests pass against deployed URLs
- [ ] 404 and API-down states verified in production

---

## How to update this file

When a slice ships:
1. Change its status row to `✅ COMPLETE (vX.Y.Z)` and add brief notes
2. Update the **Hrs** cell with total hours for the slice (prep + prompts + build + test + deploy)
3. Set the next slice row to `🔲 NEXT — ready to build`
4. Update the compact table in `CLAUDE.md` to match
5. Update `HANDOFF.md` current-state table
6. Update `docs/MVP_TO_LAUNCH_ROADMAP.md` Status column

**Tracking hours:** count every hour that touched the slice — PM time writing the
feature brief/prompts, Claude Code sessions building it, debugging rounds, manual
testing, and anything done to get it live. Update the cell each session; don't
wait until the slice is done.
