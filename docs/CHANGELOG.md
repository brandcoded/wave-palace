# Changelog — WavePalace

All notable changes to this project are documented here.

## [0.9.1] — Slice 6 add-on: public API sponsor filtering

### Added
- `ChannelService._with_live_sponsor()` — strips `sponsor` from public API responses when `isActive` is false, before `startDate`, or after `endDate`. Applied to both `list_published` and `get_published_by_slug`. Upcoming/expired sponsor details are never exposed to unauthenticated callers.
- 6 new tests in `test_channels.py` covering: active sponsor included, inactive stripped, before-start stripped, after-end stripped, within-window included, included in list endpoint. Suite: 114 pass, 2 skip.

## [0.9.0] — Sponsor Primitive (Slice 6)

### Added
- `Sponsor` Pydantic model on `Channel` (`name`, `logoUrl`, `text`, `clickUrl`, `placement`, `startDate`/`endDate`, `isActive`, `isFeatured`, `impressionCount`, `clickCount`). `sponsor_is_live()` pure helper handles timezone-aware window checks.
- `PATCH /api/admin/channels/{slug}/sponsor` — admin-auth endpoint to set or clear the sponsor. Accepts `null` body to clear.
- `POST /api/channels/{slug}/sponsor/impression` — public, IP rate-limited (30-min TTL), silently no-ops when sponsor is inactive or outside window.
- `POST /api/channels/{slug}/sponsor/click` — public, no rate limit.
- `increment_sponsor_impression` / `increment_sponsor_click` on both Seed and Mongo channel repositories (`$inc` on nested fields for Mongo).
- VRChat mux: sponsor text burned into MP4 as Row 4 drawtext line at `y=676`.
- Admin channel edit page: **Sponsor panel** between VRChat mux and URL health — fields for name, logo URL, display text, click URL, placement select, start/end datetime, active/featured toggles; Save and Clear buttons; live impression/click counter display.
- `ChannelPlayer`: `sponsor` prop accepted. Logo bug (top-right, `placement="bug"`), lower-third line (`placement="lower_third"` / `"backdrop"`), and pause-screen takeover card (dismissible, shown when paused). `recordSponsorImpression` fires once per slug per session (`sessionStorage` gate). `recordSponsorClick` fires on any sponsor CTA/logo click and opens `clickUrl`.
- Directory (`ChannelGrid`): featured active sponsors sorted to top. `ChannelCard`: "Sponsored" badge overlay on cover art when `isFeatured && isActive`.
- 22 backend tests in `tests/test_sponsor.py` (20 pass, 2 skipped for missing font on CI).

## [Unreleased] — Multi-value taxonomy (genre / mood / energy / theme)

- `genre`, `mood`, `energy`, `theme` changed from `str` to `list[str]` throughout backend (Pydantic schema, seed data, admin request models) and frontend (TypeScript types, player, cards, admin forms).
- `ChannelService._matches()` now checks array membership (case-insensitive) instead of exact string equality — `GET /api/channels?genre=House` still returns channels where `"House"` is one element of the genre array.
- `MongoChannelRepository` and `SeedChannelRepository` normalize legacy string values to single-element lists on read (`_normalize_taxonomy`) — no destructive migration needed for existing Mongo documents.
- `mux_service._drawtext_overlay()` call site joins list values with `", "` before passing to FFmpeg drawtext.
- Admin create/edit pages: genre, mood, energy, theme inputs replaced with `MultiSelectChips` component. Options fetched from `GET /api/admin/options` on mount. Chips toggle selection; selected chips show cyan highlight. Free-text entry removed.
- `ChannelPlayer`, `ChannelCard`: render one tag per element in the array.
- All 120 backend tests pass; `npm run build` clean.

## [Unreleased] — VR video progress feedback

- **Single-channel elapsed timer**: Channel edit page consolidates `handleMux` and `handleMuxChannel` into one `handleMuxVideo()`. While muxing, both the warning-banner button and the VRChat mux section button show a live `M:SS` elapsed counter (e.g. "Updating VR Video… 1:24"). A `setInterval` drives the counter; it is cleared on success or error. Success clears the `muxOutdated` banner inline without a page reload.
- **Bulk update progress panel**: Channels list page replaces the static "Updates queued" message with a live per-channel progress panel. Clicking "Update All VR Videos" calls `POST /api/mux/all`, then polls `GET /api/mux/status` every 3 s. The panel shows a progress bar (`doneCount / totalCount`) and a per-channel row with state icons (pending / running / done / error). Polling stops when `running === false`; the channel list auto-refreshes to clear "VR outdated" badges.
- No backend changes — uses existing `POST /api/mux/all` → 202 + `GET /api/mux/status` contract.
- No new packages — `lucide-react` (Clock, CheckCircle, XCircle, Loader2) + Tailwind only.

## [Unreleased] — Mux dirty-flag system + cache TTL reduction

- **Mux outdated tracking**: `muxOutdated` and `muxLastAt` fields on Channel
- **Auto-dirty-flag**: PATCH `/api/admin/channels/{slug}` sets `muxOutdated: true` when overlay-affecting fields (title, hostName, genre, mood, visualLoopUrl, coverImageUrl, playlist) change
- **Sponsor triggers re-mux**: PATCH `/api/admin/channels/{slug}/sponsor` always sets `muxOutdated: true` (sponsor text in overlay)
- **Auto-clear after mux**: `POST /api/channels/{slug}/mux` clears `muxOutdated` and sets `muxLastAt` on success
- **Admin UI warning banner**: Channel detail page shows "VR video is out of date" banner with "Update VR Video" button when `muxOutdated: true`
- **Channel list badge**: "VR outdated" badge on each channel when `muxOutdated: true`
- **Bulk update button**: "Update All VR Videos" appears at top of channel list when at least one channel is outdated
- **Cache TTL reduction**: R2 muxed MP4 cache reduced from 5 min → 60 sec via `cache_control` parameter, so Cloudflare edge picks up updates within ~1 min without manual purge
- **5 new tests** in `test_mux_outdated.py` covering overlay-field detection, sponsor changes, mux-clear behavior. Suite: 120 pass, 2 skip.

## [Unreleased] — Image Auto-Resize on Upload

- **Image processing on admin upload** — `POST /api/admin/upload/image` now 
  auto-resizes images over 1920×1080 to 1920×1080 (aspect ratio preserved), 
  converts to WebP, and compresses if over 500 KB. All formats (JPEG/PNG/WebP) 
  input; WebP output. Upload limit raised from 10 MB to 20 MB. Transparent to 
  the client — API surface unchanged. Tests: 115 pass, 2 skip.
- Submission form upload endpoint and audio/video uploads untouched.

## [Planning / Status Cleanup]

- **Monetization re-sequenced** (Growth/Monetization PM). Added
  `docs/MONETIZATION_PLAN.md` — ad/sponsorship inventory (Tiers 1–4), the
  decision to ship a thin **Sponsor Primitive (Slice 6)** *before* Slice 4 so
  live events are sponsorable on day one, an **Event-Sponsorship add-on**
  (QR bridge + sponsor frame) for Slice 4, a **Full Ad Stack (Slice 6B)** after
  Slice 4, and copy-paste build prompts for each. Slice 6 supersedes the old
  "Featured / sponsored channels" (now the directory-slot surface). Updated
  STATUS.md, CLAUDE.md, HANDOFF.md, MVP_TO_LAUNCH_ROADMAP.md, and
  FEATURE_SLICES.md to make Slice 6 the next build. No code shipped — planning only.
- Marked Slice 9 as **Code Capture + Follow Intent + Notification Stack** in
  planning/status docs, with Discord as primary delivery, browser push as
  secondary, email fallback, VRChat username as attribution only, and SMS
  explicitly deferred.

## [0.8.0] — Media URL Validation (Slice 5)

### Added
- `POST /api/admin/channels/{slug}/validate-urls` — checks all playlist audio URLs
  and `visualLoopUrl` for HTTPS, reachability, content-type, and VRChat MP4 compat.
  Uses `asyncio.gather` so one timeout doesn't block others. R2 trusted host skips
  content-type sniffing. Returns `URLCheckResult[]`.
- "Check URLs" section in admin channel edit form — shows per-URL green/amber/red
  result rows with inline warning text. Mobile-friendly, tap target ≥ 40px.
- `respx>=0.22.0` added to backend dev deps (12 new tests, 88 total passing).

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
