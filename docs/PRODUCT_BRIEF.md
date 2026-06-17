# Product Brief — WavePalace

**App name:** WavePalace

**One-sentence description:** A visual radio web app where listeners discover
curated music channels that pair audio streams with channel art and shareable
web and VRChat playback links.

**Target users:** VRChat world owners and event hosts, digital lounge and party
curators, DJs/selectors who want a stylish channel page, and listeners who want
ambient visual radio for the web.

**Problem solved:** It's hard to share a polished, visual, looping music channel
that works both on the web and inside VRChat video players. WavePalace gives each
channel a beautiful playback page and ready-to-paste links.

**Core user action:** Browse channels → push play on a channel → listen to
non-stop persistent streaming music (like a radio station tuned by genre, mood,
energy, theme, DJ, host, or event) with channel art (static image) and channel/
song info displayed → copy a web link or a VRChat playback link.

**Revenue / value moment:** The shareable VRChat link — the moment a host drops a
WavePalace channel into a world or event is the core value event. (Monetization
such as featured/sponsored channels is a future slice, not in the MVP.)

**MVP scope:**
- Polished landing page with hero + channel directory grid
- Filter chips (genre, mood, energy, theme)
- Channel detail/player page with push-play, non-stop persistent streaming
  (each channel behaves like a streaming radio station — always playing, no
  manual track selection required, similar to Music Choice)
- Playlist cycling: tracks auto-advance on end, loop back to track 1 —
  no manual interaction required; track counter displays current position
- Copy Web Link and Copy VRChat Link
- FastAPI backend with `/health`, `/api/channels`, `/api/channels/{slug}`
- Seed data with seed-mode fallback (no database required to run)
- Backend tests + documentation

**Out of scope (MVP):** accounts, auth, uploads, payments, ads, analytics,
admin/music-director dashboards, DJ/artist submission forms, AI recommendations,
live streaming, and any restreaming of third-party music services.

**Media architecture (MVP):** Each channel stores audio and visuals as separate
files on Cloudflare R2. The web player renders a static cover image as background
and streams `audioUrl` directly. For VRChat, a pre-muxed static MP4 (cover image
+ audio baked in) is uploaded to R2 and served as `vrchatPlaybackUrl` — a single
direct file URL, most reliable format for VRChat video players. Animated/looping
video backgrounds are deferred to a future slice.

**Risk level:** Low–medium. The product is technically narrow; the main external
risks are music licensing and VRChat media-host compatibility (both deferred and
documented, see `LICENSING_NOTES.md`).

**Complexity level:** Low. Two small apps (Next.js + FastAPI), in-memory seed
data, no auth or persistence required for the MVP.
