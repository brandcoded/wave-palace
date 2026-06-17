# Changelog — WavePalace

All notable changes to this project are documented here.

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
