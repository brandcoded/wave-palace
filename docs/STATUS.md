# WavePalace — Implementation Status

> Single source of truth for slice status. Update this file whenever a slice
> ships or changes state. `CLAUDE.md` carries a compact copy — keep both in sync.
> Last updated: 2026-06-21 (Slice 9 — Code Capture + Follow Intent + Notification Stack complete)

---

## Slice status

| Slice | Feature | Status | Notes |
|---|---|---|---|
| MVP | Public visual channel playback | ✅ COMPLETE (v0.1.0) | Browse, filter, play, copy links, error states |
| MVP | Playlist cycling + track counter | ✅ COMPLETE (v0.2.0) | Tracks auto-advance, loop, counter shown |
| MVP add-on | VRChat MP4 mux service | ✅ COMPLETE (v0.3.0) | `POST /api/mux/all`, `POST /api/channels/{slug}/mux`, R2 upload |
| 1 | Animated video loop backgrounds | ✅ COMPLETE (v0.4.0) | `visualLoopUrl` live on web player + mux · Admin UI toggle shipped in Slice 3 (v0.7.0) |
| 1B | Channel & host info in player overlay | ✅ COMPLETE (v0.5.0) | Title, host name, genre/mood in gradient bar |
| 1B add-on | VRChat MP4 overlay parity | ✅ COMPLETE (v0.5.0) | Channel info burned into MP4 via FFmpeg `drawtext` |
| 3 add-on† | TrackItem schema (`url`, `title`, `artist`) | ✅ COMPLETE (main) | Replaces flat `playlist: string[]` |
| 3 add-on† | Now-playing display | ✅ COMPLETE (main) | "Artist — Track Title" shown in web player |
| 2 | DJ / Artist submission form | ✅ COMPLETE (v0.6.0) | Public form → pending queue · Profile image upload to R2 · Multi-select chips from API · `submissions.py` routes + service + repo + tests |
| 3 | Music director admin dashboard | ✅ COMPLETE (v0.7.0) | JWT cookie auth · Submission review queue · Channel CRUD + drag-to-reorder tracks · R2 media uploads · Options management |
| 3 add-on | Play count event tracking | ✅ COMPLETE (v0.7.0) | `POST /api/channels/{slug}/play` · in-memory rate limit · sessionStorage gate on web player |
| 3 add-on | External Stream Passthrough | ⬜ NOT STARTED | `liveStreamUrl` field · admin pastes VRCDN/OBS/.ts URL → VRChat players hit external stream directly · no VPS · VRChat-only (web player uses playlist MP3s) · no overlay burned in · tradeoffs: no uptime control, URL tied to creator's infra |
| Pre-Slice 4 add-on | Streaming readiness + mux/stream toggle | ✅ COMPLETE | `streamingActive` + `vrchatFallbackUrl` on Channel schema · `PATCH /api/admin/channels/{slug}` accepts both fields · `POST /api/admin/channels/streaming/bulk` flips all channels · admin edit page: streaming toggle + live stream URL field in VRChat section · admin channels list: "Activate / Deactivate Streaming" bulk button · public API exposes both fields · 7 new backend tests · no VPS required |
| **6** | **Sponsor Primitive (thin monetization)** | **✅ COMPLETE (v0.9.0)** | `sponsor` object on Channel · admin PATCH endpoint + edit-page panel (name, logo, text, CTA URL, placement, date window, active/featured toggles, impression/click counters) · web player overlays (logo bug, lower-third text, pause-screen takeover) · directory featured-pin + "Sponsored" badge · VRChat parity (sponsor text burned into drawtext) · impression/click tracking with 30-min TTL rate limit · 22 backend tests · No VPS dep |
| Pre-Slice 4 | Hetzner VPS provisioning | ⬜ DEFERRED | CPX32 FSN1 · 4 vCPU / 8 GB · Ubuntu 22.04 · ~$42/mo base (~$51 with backups) · AzuraCast + SRS + FFmpeg · provision when live events become priority · see `docs/VPS_PROVISIONING.md` |
| **Pre-Slice 4 add-on** | **Streaming readiness + mux/stream toggle** | **✅ COMPLETE** | Schema + admin toggle + bulk endpoint + 7 tests — see row above |
| 4 | Live event streaming — Link-In + ingest keys | ⬜ AFTER Pre-Slice 4 | OBS push · HLS/RTMP/SRT pull · AzuraCast DJ mode · Requires VPS provisioned · toggle infra ships pre-Slice 4 so no frontend work needed here |
| 4 add-on | Event Sponsorship (QR bridge + sponsor frame) | ⬜ WITH Slice 4 | Event-sponsor intro frame + QR-code bridge baked into the live MP4 · Depends on Slice 6 `sponsor` object + Slice 4 streaming path |
| 5 | Media URL validation & compatibility checker | ✅ COMPLETE (v0.8.0) | `POST /api/admin/channels/{slug}/validate-urls` · HTTPS/reachability/content-type/VRChat-compat checks · "Check URLs" button in admin channel edit |
| 6B | Full Ad Stack | ⬜ AFTER Slice 4 | Multi-sponsor rotation · web CPM measurement · intro/outro splash · idle card · opt-in audio stings (AzuraCast) · sponsor reporting dashboard · See `MONETIZATION_PLAN.md` |
| 7 | Production analytics dashboard | ⬜ NOT STARTED | Depends on Slice 3 add-ons |
| 8 | Play Metrics + Artist Reporting | ⬜ NOT STARTED | PM plan complete · Depends on Slice 3 add-ons + Slice 9 |
| 9 | Code Capture + Follow Intent + Notification Stack | ✅ COMPLETE | 6-char alphanumeric codes · admin generate/deactivate UI · public `/follow/[code]` landing · Discord OAuth confirmed-instantly · email double opt-in via Resend · browser push schema only · SMS raises NotImplementedError · `/follows` listener page · admin `/admin/codes` page · Follow Codes panel on channel edit page · `CodeInput` pill in site header · `POST/GET /api/admin/codes` · `GET /api/codes/{code}` · `POST /api/codes/{code}/follow` · `POST /api/follows/confirm` · `GET/PATCH/DELETE /api/follows` · Discord OAuth `/api/auth/discord/initiate` + `/callback` · 19 backend tests (146 total) · build clean |

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
2. Set the next slice row to `🔲 NEXT — ready to build`
3. Update the compact table in `CLAUDE.md` to match
4. Update `HANDOFF.md` current-state table
5. Update `docs/MVP_TO_LAUNCH_ROADMAP.md` Status column
