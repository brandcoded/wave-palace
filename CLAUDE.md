# WavePalace — Claude Code Context

Visual radio web app: curated music channels with cinematic backdrops, shareable
as web links and VRChat playback URLs. Think Music Choice for VRChat lounges.

Full docs: `HANDOFF.md` (architecture, env vars, deploy) · `AGENTS.md` (rules)
Full status: `docs/STATUS.md` (canonical) — this file carries a compact copy.

---

## Implementation status (compact)

| Slice | Feature | Status |
|---|---|---|
| MVP | Public visual channel playback | ✅ COMPLETE |
| MVP | Playlist cycling + track counter | ✅ COMPLETE |
| MVP add-on | VRChat MP4 mux service | ✅ COMPLETE |
| 1 | Animated video loop backgrounds | ✅ COMPLETE |
| **1C** | **Audio Visualizer** (Web Audio canvas, 5 styles, 6 themes, backdrop modes, VRChat mux FFmpeg filter) | **✅ COMPLETE** |
| 1B | Channel & host info in player overlay | ✅ COMPLETE |
| 1B add-on | VRChat MP4 overlay parity (drawtext) | ✅ COMPLETE |
| 3 add-on | TrackItem schema + now-playing display | ✅ COMPLETE |
| 2 | DJ / Artist submission form | ✅ COMPLETE |
| 3 | Music director admin dashboard | ✅ COMPLETE |
| 3 add-on | Play count event tracking | ✅ COMPLETE |
| 3 add-on | External Stream Passthrough (`liveStreamUrl` + admin UI, no VPS) | ⬜ NOT STARTED |
| 6 | Sponsor Primitive (thin monetization) | ✅ COMPLETE |
| **Pre-Slice 4 add-on** | **Streaming readiness + mux/stream toggle (schema + admin UI, no VPS dep)** | **✅ COMPLETE** |
| Pre-Slice 4 | Hetzner VPS provisioning (AzuraCast + SRS + FFmpeg) | ⬜ DEFERRED — provision when live events are priority |
| 4 | Live event streaming — Link-In + ingest keys | ⬜ AFTER Pre-Slice 4 + VPS provisioned |
| 4 add-on | Event Sponsorship (QR bridge + sponsor frame) | ⬜ WITH Slice 4 |
| 5 | Media URL validation & compatibility checker | ✅ COMPLETE |
| 6B | Full Ad Stack (rotation, CPM, audio stings, reporting) | ⬜ AFTER Slice 4 |
| 7 | Production analytics dashboard | ✅ COMPLETE |
| 8 | Play Metrics + Artist Reporting | ⬜ NOT STARTED |
| 9 | Code Capture + Follow Intent + Notification Stack | ✅ COMPLETE |
| **10** | **Identity & Roles** (auth foundation: User/Session, stackable roles, Discord/email-code/password login, migrates admin JWT) | ✅ COMPLETE |
| **11** | **Host Onboarding & Ownership** (`Channel.owner_ids` + `auto_publish`, single-use invite links, `require_channel_owner`, `/host/join`) | ✅ COMPLETE |
| **12** | **Logged-In Dashboard** (`/home`, listen history, saves, notifications, recommendations, `UserMenuIsland`, `ChannelCard` heart, `ChannelPlayer` listen event) | **✅ COMPLETE** |
| **13** | **Notification System** (Resend email + Discord bot DM, per-follow notify_ prefs, throttle, new-track hook, admin trigger + digest cron endpoint, `/follows` prefs panel + unsubscribe deep link) | **✅ COMPLETE** |
| **13 add-on** | **Discord guild-join** (auto-PUT follower into WavePalace server on OAuth callback via `guilds.join` scope; fixes `50278` DM errors; graceful degradation; `DISCORD_GUILD_ID` env var; 9 backend tests) | **✅ COMPLETE** |
| **13 add-on** | **Public Metrics Display** (`follower_count`, `listener_count`, `worlds_count`, `trending` on Channel schema + API; `active_listener_count` 15-min window; `metrics.ts` threshold display utilities; ChannelCard metric row + Trending badge; ChannelPlayer overlay metrics; 60s ChannelGrid polling; `/home` taste reflection; `/follows` Early listener badge; 9 backend tests) | **✅ COMPLETE** |
| Legal | DMCA Takedown Form (`/legal/takedown` + admin queue) | ✅ COMPLETE |

**Always update this table and `docs/STATUS.md` when a slice ships.**

**Monetization sequence (Growth/Monetization PM):** the thin **Sponsor Primitive
(Slice 6)** ships *before* Slice 4 so live events are sponsorable on day one; the
**Full Ad Stack (Slice 6B)** follows Slice 4. Full plan + copy-paste build prompts
in `docs/MONETIZATION_PLAN.md`. Slice 6 supersedes the old "Featured / sponsored
channels" (now folded in as the directory-slot surface).

---

## Key rules (full rules in `AGENTS.md`)

- Build one vertical slice at a time — UI + API + tests + docs before starting another
- Do not overbuild — no auth, payments, uploads, analytics, or AI unless explicitly requested
- Route handlers are thin — business logic lives in services, data in repositories
- Third-party streaming links (Spotify, YouTube, SoundCloud) are attribution only — never playback sources
- Visual direction: dark, immersive, cinematic, glassy, music-forward — not a SaaS dashboard

---

## Stack

- Frontend: Next.js (App Router) · TypeScript · Tailwind · `apps/frontend/src/`
- Backend: FastAPI · Pydantic · Python · `apps/backend/app/`
- Data: MongoDB Atlas (seed fallback when `MONGODB_URI` is empty)
- Media: Cloudflare R2 at `stream.wavepalace.live`

## When a slice ships — update these files

1. `docs/STATUS.md` — full status table (canonical)
2. `CLAUDE.md` — compact status table above (this file)
3. `HANDOFF.md` — current-state table
4. `docs/MVP_TO_LAUNCH_ROADMAP.md` — Status column
5. `docs/FEATURE_SLICES.md` — mark slice header COMPLETE
6. `docs/CHANGELOG.md` — add version entry
7. `docs/API_CONTRACT.md` — add any new endpoints
