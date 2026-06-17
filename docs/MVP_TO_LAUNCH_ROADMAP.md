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

## 2. Complete vertical slices

Add slices one at a time per `FEATURE_SLICES.md` (submissions → director
dashboard → URL/compatibility checker → featured channels → analytics). Each
ships with UI, API, tests, and docs.

## 3. Production hardening

- Switch from seed mode to MongoDB Atlas (`MONGODB_URI`).
- Add request logging, error monitoring, and rate limiting.
- Introduce auth before any dashboard/submission write paths.
- Validate and sanitize all media URLs (HTTPS-only).
- Add a takedown/removal policy and rights attestation.

## 4. Deployment plan

Frontend → Vercel. Backend → Render. Database → MongoDB Atlas. See
`DEPLOYMENT.md` for env vars and steps.

## 5. Launch checklist

- [ ] All MVP "Definition of Done" items pass (see README).
- [ ] Seed media replaced with cleared/licensed media.
- [ ] CORS locked to the production frontend origin.
- [ ] Licensing notes + takedown policy published.
- [ ] Smoke tests pass against deployed URLs.
- [ ] 404 and API-down states verified in production.

## 6. Maintenance plan

- Keep dependencies patched (Next.js, FastAPI, Pydantic).
- Monitor backend health (`/health`) and media-host availability.
- Periodically re-verify VRChat compatibility (host behavior changes).

## 7. Feature update workflow

Pick one slice → branch → build UI + API + data + tests → update `docs/` and
`CHANGELOG.md` → review against `AGENTS.md` → merge → deploy → smoke test.
