# WavePalace — Implementation Status

> Single source of truth for slice status. Update this file whenever a slice
> ships or changes state. `CLAUDE.md` carries a compact copy — keep both in sync.
> Last updated: 2026-06-19 (Slice 3 + admin mobile parity shipped — Slice 4 is next)

---

## Slice status

| Slice | Feature | Status | Notes |
|---|---|---|---|
| MVP | Public visual channel playback | ✅ COMPLETE (v0.1.0) | Browse, filter, play, copy links, error states |
| MVP | Playlist cycling + track counter | ✅ COMPLETE (v0.2.0) | Tracks auto-advance, loop, counter shown |
| MVP add-on | VRChat MP4 mux service | ✅ COMPLETE (v0.3.0) | `POST /api/mux/all`, `POST /api/channels/{slug}/mux`, R2 upload |
| 1 | Animated video loop backgrounds | ✅ COMPLETE (v0.4.0) | `visualLoopUrl` live on web player + mux · Admin UI toggle pending Slice 3 |
| 1B | Channel & host info in player overlay | ✅ COMPLETE (v0.5.0) | Title, host name, genre/mood in gradient bar |
| 1B add-on | VRChat MP4 overlay parity | ✅ COMPLETE (v0.5.0) | Channel info burned into MP4 via FFmpeg `drawtext` |
| 3 add-on† | TrackItem schema (`url`, `title`, `artist`) | ✅ COMPLETE (main) | Replaces flat `playlist: string[]` |
| 3 add-on† | Now-playing display | ✅ COMPLETE (main) | "Artist — Track Title" shown in web player |
| 2 | DJ / Artist submission form | ✅ COMPLETE (v0.6.0) | Public form → pending queue · Profile image upload to R2 · Multi-select chips from API · `submissions.py` routes + service + repo + tests |
| 3 | Music director admin dashboard | ✅ COMPLETE (v0.7.0) | JWT cookie auth · Submission review queue · Channel CRUD + drag-to-reorder tracks · R2 media uploads · Options management |
| 3 add-on | Play count event tracking | ✅ COMPLETE (v0.7.0) | `POST /api/channels/{slug}/play` · in-memory rate limit · sessionStorage gate on web player |
| **4** | **Live event streaming — Link-In + ingest keys** | **🔲 NEXT** | OBS push · HLS/RTMP/SRT pull · AzuraCast DJ mode · Depends on VPS provisioning |
| 5 | Media URL validation & compatibility checker | ⬜ NOT STARTED | No dependencies |
| 6 | Featured / sponsored channels | ⬜ NOT STARTED | First monetisation surface |
| 7 | Production analytics dashboard | ⬜ NOT STARTED | Depends on Slice 3 add-ons |
| 8 | Play Metrics + Artist Reporting | ⬜ NOT STARTED | PM plan complete · Depends on Slice 3 add-ons + Slice 9 |
| 9 | Code Capture + Follow Intent + Notification Stack | ⬜ NOT STARTED | PM plan drafted · VRChat listener enters code → Discord/email/push follow intent · SMS explicitly deferred |

† TrackItem / now-playing shipped in commits `2d3a72c`, `2ee4fa2`, `e2385bc` before Slice 2 was merged; status docs now reflect that it already shipped.

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
