# AGENTS.md — Instructions for coding agents working on WavePalace

WavePalace is a visual radio web app: curated music/audio channels paired with
background visuals, with shareable web and VRChat playback links.

## Operating rules

1. **Build one vertical slice at a time.** Ship a complete, working slice
   (UI + API + data + tests + docs) before starting another.
2. **Do not overbuild.** The MVP is intentionally narrow. Resist adding
   infrastructure "for later."
3. **Keep the layers separate:**
   - Presentation — `apps/frontend/src/presentation`, `apps/frontend/src/shared`
   - Feature UI — `apps/frontend/src/features/*`
   - Business/service — `apps/backend/app/services`
   - Data/repository — `apps/backend/app/repositories`, `apps/backend/app/seed`
   - Route handlers stay thin; business logic belongs in services.
4. **Do not add** payments, auth, uploads, file storage, analytics, an admin
   dashboard, AI features, email automation, or team accounts unless the user
   explicitly requests them.
5. **Never turn third-party streaming links into playback sources.** Spotify,
   Apple Music, TIDAL, SoundCloud, YouTube, and Mixcloud links are attribution
   ("Listen elsewhere") only. The player uses `webPlaybackUrl`; the VRChat copy
   uses `vrchatPlaybackUrl`.
6. **Update docs when adding features** (`docs/` + `CHANGELOG.md`).
7. **Add backend tests for backend changes** and keep `pytest` green.
8. **Preserve the WavePalace visual direction:** dark, immersive, cinematic,
   glassy, music-forward. Not a generic SaaS dashboard.

## Definition of done for a slice

UI renders and is responsive; API contract documented in `docs/API_CONTRACT.md`;
business rules enforced in the service layer; tests cover the new behavior;
docs and changelog updated.
