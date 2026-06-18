# Changelog — WavePalace

All notable changes to this project are documented here.

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
