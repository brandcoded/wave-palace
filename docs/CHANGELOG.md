# Changelog — WavePalace

All notable changes to this project are documented here.

## [Unreleased] — Planning / Status Cleanup

- Marked Slice 9 as **Code Capture + Follow Intent + Notification Stack** in
  planning/status docs, with Discord as primary delivery, browser push as
  secondary, email fallback, VRChat username as attribution only, and SMS
  explicitly deferred.

## [0.7.1] — Admin UI Mobile Responsive

- Hamburger nav drawer replaces sidebar below `lg` breakpoint
- Submissions and channels pages use card layout on mobile (table hidden below `lg`)
- Channel edit and new channel forms use single-column grid on mobile (`grid-cols-1 sm:grid-cols-2`)
- All tap targets ≥ 40px; main content clears sticky top bar via `pt-16`

## [0.7.0] — Music Director Admin Dashboard

### Added
- Password-protected admin UI at `/admin` — single ADMIN_SECRET, JWT (HS256,
  24h) stored in httpOnly cookie. Login, logout, and session-check endpoints.
- **Submission review queue** at `/admin/submissions` — pending/approved/rejected
  tabs with count badge, detail drawer, approve/reject with optional notes.
- **Channel management** at `/admin/channels` — list all channels (including
  unpublished), create, edit, publish-toggle, soft-delete.
- **Channel edit form** — inline track management with drag-to-reorder
  (`@dnd-kit/sortable`), per-track title/artist editing, MP3 upload → R2,
  cover image / visual loop upload, one-click VRChat re-mux.
- **Media upload endpoints** — `POST /api/admin/upload/{image,video,audio}`
  with MIME type + size validation; streamed to R2.
- **Submission options management** at `/admin/options` — edit genre/mood/
  energy/theme lists in place; changes immediately reflected on public form.
- **Play count add-on** — `POST /api/channels/{slug}/play` increments
  `playCount` in MongoDB; in-memory rate limit (1/IP/slug/30 min); web player
  fires once per slug per session via `sessionStorage`.
- `ADMIN_SECRET` and `JWT_SECRET` env vars added to `render.yaml`.
- 24 new pytest tests covering all admin routes (auth, submissions, channels,
  uploads, options, play count).

## [0.6.0] — DJ / Artist Submission Form

### Added
- Public `/submit` page for DJs, artists, and hosts to propose WavePalace
  channels without auth. The form supports API-backed multi-select chips,
  sample links, rights attestation, optional notes, and a success confirmation.
- `GET /api/submission-options` returns genre, mood, energy, and theme option
  lists from MongoDB with seed fallback.
- `POST /api/submissions/upload-image` validates optional JPEG/PNG/WebP profile
  images up to 5 MB and uploads them to R2 under `submissions/images/`.
- `POST /api/submissions` stores validated proposals as `pending`; no
  submission is auto-published.
- Backend submission repositories, service-layer validation, and pytest
  coverage for options, image upload, and submission validation cases.

## [0.5.0] — VRChat MP4 Text Overlay + Web Player Info in Overlay

### Added
- Channel title, "Hosted by {host}", and genre · mood are now **burned into
  the lower portion of every muxed VRChat MP4** via FFmpeg `drawtext`. A
  semi-transparent dark band (matching the web player's gradient) sits behind
  the text for legibility over any backdrop or video loop.
- `_drawtext_overlay()` helper in `mux_service.py` builds the filter chain.
  Returns an empty string when the font is absent so the mux still succeeds.
- `_escape_drawtext()` safely escapes `:`, `'`, `%`, `\` in channel strings so
  titles with apostrophes or colons don't break the FFmpeg filtergraph.
- **Still-image path:** overlay appended to the `[0:v]…[vout]` chain in
  `_build_image_mux_cmd` — text is burned into every frame.
- **Video-loop path:** overlay burned into the 30-second segment encode
  (`_build_segment_cmd`). The final `_build_video_mux_cmd` keeps `-c:v copy`
  — overlay repeats for free across all loops, no re-encode cost.
- `fonts-dejavu-core` added to `render.yaml` apt install; `FONT_PATH` env var
  (default `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`) wired through
  `Settings.font_path` in `app/core/config.py`.
- 8 new unit tests covering escape logic, overlay filter construction, and
  the guarantee that `_build_video_mux_cmd` never adds drawtext.
- **Web player overlay (Slice 1B):** channel title, "Hosted by {host}", and
  genre + mood chips moved into the `ChannelPlayer` gradient bar. The
  redundant title/host/tags block below the player was removed; description
  remains as a standalone paragraph. Player now accepts `hostName`, `genre`,
  `mood` props. Tags hidden on mobile (`hidden sm:flex`).
- **Now-playing metadata add-on:** playlist entries now use `TrackItem`
  objects (`url`, `title`, `artist`) instead of bare URL strings. The web player
  shows the current track metadata in the overlay, and the VRChat mux burns
  timed per-track now-playing text into the MP4 output.

### Upgrade note
Re-run `POST /api/mux/all` after deploying to regenerate all three MP4s with
burned-in overlays. Purge Cloudflare cache after the job completes.

## [0.4.0] — Looping Video Backdrops in VRChat MP4

### Added
- `visualLoopUrl` on each channel — a short looping MP4 used as the visual
  layer in the muxed VRChat file (falls back to `coverImageUrl` when unset).
- Mux service detects video vs image covers by extension and handles each:
  still images loop at 1 fps; video loops are encoded **once** to a normalized
  720p/15fps segment, then repeated via `-stream_loop` with `-c:v copy` (no
  re-encode) over the concatenated playlist audio.

### Why the encode-once + stream-copy approach
- A naive full-length re-encode of a 15-minute 720p video produced a 478 MB
  file and ~200s of CPU — far beyond Render's free tier (would time out) and
  too large to stream. Encoding only the 30s loop once (~450 frames) and
  stream-copying it keeps total CPU within budget; output is ~94 MB for a
  15-minute channel.
- `_FFMPEG_TIMEOUT_S` raised 300 → 600 for long multi-track video channels.

## [0.3.0] — Automatic VRChat MP4 Mux Service

### Added
- `POST /api/channels/{slug}/mux` — muxes a single channel's cover image +
  audio MP3 into a VRChat-compatible MP4 via FFmpeg (`-loop 1`, H.264/AAC,
  `-movflags +faststart`) and uploads to R2 at
  `muxed/{channel_id}/{slug}.mp4`.
- `POST /api/mux/all` — runs the mux job for every published channel in one
  call; per-channel errors are recorded without aborting the run.
- `app/services/mux_service.py` — orchestrates download → ffmpeg → upload.
- `app/repositories/r2_repository.py` — boto3 S3-compatible R2 client.
- R2 config in `app/core/config.py`: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`,
  `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_BASE_URL`.
- `boto3` added to `requirements.txt`.
- FFmpeg installed on Render via `render.yaml` `apt-get install -y ffmpeg`.
- 9 tests in `app/tests/test_mux.py` (all mocked, no real I/O).

### Production notes (lessons from the first live run)
- Downloads send a browser `User-Agent` — Cloudflare returns 403 to default
  Python/library agents on `stream.wavepalace.live`.
- Cover is downscaled to a fixed 1280×720 before encoding: a 1536² source
  cover OOM-killed Render's free-tier worker mid-job. 720p bounds memory/CPU
  and is the most VRChat-compatible resolution. Encode is 1 fps, `ultrafast`,
  single-thread, with a 90s timeout.
- `/api/mux/all` runs as a background job with a pollable `GET /api/mux/status`
  endpoint — a synchronous full-batch request exceeded Render's HTTP timeout
  (502). All three seed channels now mux in ~44s total.
- `vrchatPlaybackUrl` in seed data now points to the muxed MP4s (was falling
  back to the raw MP3s).

## [0.2.0] — Playlist Cycling

### Added
- Playlist cycling: each channel now has a `playlist: string[]` field (ordered
  MP3 URLs). The web player auto-advances to the next track on `onEnded` and
  loops back to track 1 after the last — no user interaction required.
- Track counter overlay on the player: "Track 1 of 4" updates as tracks advance.
  Hidden for single-track channels.
- Backend: `playlist` field added to Pydantic `Channel` schema and all seed
  channels. `channel_abc123` (Late Night House) ships with 4 tracks; others have
  single-item playlists. `audioUrl` is kept for backwards compatibility.

## [0.1.0] — MVP

### Added
- Walking skeleton: Next.js frontend + FastAPI backend, `/health` endpoint.
- MVP slice **Public Visual Channel Playback**:
  - Home hero + channel directory grid with genre/mood/energy/theme filters.
  - Channel detail/player page with in-browser playback (`webPlaybackUrl`).
  - Copy Web Link and Copy VRChat Link with feedback + clipboard fallback.
  - Friendly error states (API down, media load failure, 404).
- Backend API: `/api/channels`, `/api/channels/{slug}` (published-only).
- Pydantic schemas, channel service (business rules), channel repository with
  seed fallback and a Mongo-ready implementation.
- Three published seed channels (+ one unpublished, for tests).
- Backend pytest suite (health, listing, published-only, slug lookup, 404,
  filtering).
- Documentation set + `AGENTS.md` + root `README.md`.
