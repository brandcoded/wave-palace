# Feature Slices — WavePalace

Build one slice at a time. The MVP slice and mux service are implemented.

## MVP slice (COMPLETE): Public Visual Channel Playback

As a listener or VRChat host, I can browse curated channels, push play on a
channel, and immediately hear non-stop persistent streaming music — each channel
behaves like a streaming radio station tuned by genre, mood, energy, theme, DJ,
host, or event (similar to Music Choice). Tracks cycle automatically through the
channel's playlist: when a track ends, the next starts with no user interaction,
looping back to track 1 after the last. A track counter shows the current
position. A static channel art image displays behind the player. I can copy
either the web link or the VRChat playback link to share the channel.

**Media architecture:** Each channel has a `playlist` (ordered `TrackItem`
objects with URL, title, and artist metadata) and a `coverImageUrl` stored on
Cloudflare R2 (`stream.wavepalace.live`). The web player cycles through
`playlist` automatically and renders `coverImageUrl` as background. The
`audioUrl` field is retained for backwards compatibility and always equals
`playlist[0].url`. The VRChat link (`vrchatPlaybackUrl`) points to a pre-muxed
static MP4 (cover image + audio combined) uploaded to R2 — single direct file,
most VRChat-compatible format.

Includes: home hero + directory grid, filter chips, channel detail/player page
with push-play persistent streaming + playlist cycling + track counter, Copy Web
Link, Copy VRChat Link, seed data + API, friendly error states, tests.

## MVP add-on (COMPLETE): Automatic VRChat MP4 Mux Service

An internal admin endpoint that downloads `coverImageUrl` + `audioUrl` for
each channel, runs FFmpeg to mux them into a single H.264/AAC MP4 with
`-movflags +faststart`, uploads the result to R2 at
`muxed/{channel_id}/{slug}.mp4`, and returns the public `vrchatPlaybackUrl`.

Endpoints: `POST /api/channels/{slug}/mux` and `POST /api/mux/all`.
Requires `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` env vars.
FFmpeg is installed on Render via `render.yaml` build command.

---

## Production streaming architecture (target — replaces mux approach)

**Goal:** True streaming — all listeners synchronized, instant playlist updates,
VRChat PC + Quest compatible, fully self-hosted, open source only.

### Stack

```
[Next.js Admin UI /admin]
        ↓  WavePalace API calls only — admin never touches AzuraCast
[WavePalace FastAPI]
        ↓  proxies AzuraCast REST API internally
        ↓  manages R2 uploads
        ↓  manages MongoDB records
[AzuraCast]  ← open source (GPL), self-hosted on VPS
        ↓  RTMP audio stream per channel
[FFmpeg combiner]  ← one process per channel — combines audio + visual loop
        ↓  RTMP (audio + video)
[SRS — Simple Realtime Server]  ← open source (MIT), self-hosted
        ↓  HTTP-TS output per channel
[Cloudflare proxy]  ← free HTTPS termination
        ↓
https://stream.wavepalace.live/live/late-night-house.ts  ← VRChat static URL
        ↓                    ↓
[VRChat PC + Quest]    [Web player audio + video loop]

[Cloudflare R2]    ← audio files, visual loops, cover images, ad videos
[MongoDB Atlas]    ← channel metadata, playlists, host info, ad records
```

### Layer details

**AzuraCast — Playlist Scheduling**
Open source internet radio automation. Manages track rotation, playlist
scheduling, DJ handoffs. Full REST API — WavePalace FastAPI proxies all calls.
Admin never opens AzuraCast.

**FFmpeg Combiner — Audio + Visual Merge**
One FFmpeg process per channel, running continuously on the VPS. Pulls
AzuraCast's Icecast audio stream + a looping MP4 from R2, merges them, and
pushes a single RTMP stream to SRS.

```bash
ffmpeg \
  -stream_loop -1 -re -i https://stream.wavepalace.live/channels/{id}/loop.mp4 \
  -i http://localhost:8080/radio/late-night-house/listen \
  -c:v libx264 -preset ultrafast -r 1 -tune stillimage \
  -c:a aac -b:a 256k \
  -f flv rtmp://localhost/live/late-night-house
```

Visual loop update = FFmpeg process restarts for that channel only (2–5 s).
All other channels unaffected.

**SRS — Stream Output**
Receives RTMP from FFmpeg. Outputs HTTP-TS per channel. Lightweight, MIT.
```
https://stream.wavepalace.live/live/late-night-house.ts  ← VRChat
http://localhost:8080/radio/late-night-house/listen       ← Icecast (web audio)
```

**Web player**
Two decoupled elements:
- `<audio>` → Icecast URL from AzuraCast (true streaming audio)
- `<video>` → R2 visual loop MP4 (muted, looping — unchanged from current)
- React refs sync play/pause between both

**VRChat**
One static HTTP-TS URL per channel — never changes. H.264 video loop + AAC
audio. PC (ProTV, USharpVideo, VizVid) confirmed compatible. Quest over HTTPS
needs testing.

### Admin operations — all through WavePalace UI

| Admin action | WavePalace does internally |
|---|---|
| Add track | Upload MP3 to R2 → AzuraCast API adds to playlist → plays next rotation |
| Delete track | AzuraCast API removes → R2 delete → MongoDB remove |
| Reorder playlist | AzuraCast API reorder |
| Update track | Upload new MP3 to R2 → AzuraCast API swap URL → MongoDB update |
| Update visual loop | Upload MP4 to R2 → MongoDB update → restart FFmpeg for that channel |
| Update cover image | Upload to R2 → MongoDB update |
| Add ad video | Upload to R2 → create ad record in MongoDB |
| Update channel info | MongoDB write → AzuraCast station metadata API |
| Update host info | MongoDB write |
| Publish/unpublish | Toggle `isPublished` → start/stop FFmpeg + AzuraCast station |
| Check stream health | SRS HTTP API → surfaced in admin UI |

### Song add / delete / update flows

**Add:**
```
Admin uploads MP3 → FastAPI uploads to R2 (tracks/{channel_id}/{uuid}.mp3)
→ FastAPI calls AzuraCast API: POST /api/station/{id}/files
→ AzuraCast adds to playlist → plays next rotation
→ FastAPI writes metadata to MongoDB
→ Zero re-encode. VRChat URL unchanged — stream updates live.
```

**Delete:**
```
Admin clicks delete → FastAPI removes from AzuraCast → deletes from R2
→ removes from MongoDB → never plays again. Immediate. No mux, no downtime.
```

**Update / replace:**
```
Admin uploads replacement → FastAPI uploads to R2 at new UUID key
→ AzuraCast API swaps track URL → MongoDB update → old file deleted from R2
→ plays next rotation. Zero re-encode.
```

**Update visual loop:**
```
Admin uploads new loop.mp4 → FastAPI uploads to R2 (channels/{id}/loop.mp4)
→ MongoDB visualLoopUrl updated → FastAPI signals FFmpeg restart for that channel
→ FFmpeg restarts with new video (2–5 s) → VRChat stream continues
→ Web player picks up new visual on next page load
```

### Mux vs true streaming comparison

| Factor | Mux (current) | True streaming (target) |
|---|---|---|
| True streaming | No — progressive download | Yes — real-time synchronized |
| All listeners synchronized | No | Yes |
| Add / delete / update a song | Full re-encode 1–15 min | Instant |
| Update visual loop | Full re-encode 1–15 min | 2–5 s FFmpeg restart |
| Playlist length limit | ~15–20 tracks | Unlimited |
| VRChat PC | Yes — direct MP4 | Yes — HTTP-TS |
| VRChat Quest | Yes — direct MP4 | Needs testing |
| Visual loop in VRChat | Yes — baked into MP4 | Yes — baked into HTTP-TS via FFmpeg |
| Visual loop on web | R2 MP4 in `<video>` | R2 MP4 in `<video>` (same) |
| Admin via WavePalace UI | Manual mux trigger only | Full control |
| VRChat URL changes | Never | Never |
| Stream URL format | `muxed/{id}.mp4` | `live/{slug}.ts` |
| Infrastructure | R2 + FFmpeg on Render | VPS + AzuraCast + SRS + FFmpeg |
| Open source tools | FFmpeg only | AzuraCast (GPL) + SRS (MIT) + FFmpeg |
| Monthly cost added | ~$0 | ~$16–20/mo (VPS) |
| Closest equivalent | On-demand file CDN | Music Choice, SiriusXM |

### VPS spec (3 channels)

| Component | CPU | RAM |
|---|---|---|
| AzuraCast | 2 vCPU | 2 GB |
| SRS | 0.5 vCPU | 256 MB |
| FFmpeg × 3 (ultrafast, 1 fps) | ~1 vCPU | ~512 MB |
| OS overhead | 0.5 vCPU | 512 MB |
| **Total** | **~4 vCPU** | **~3.5 GB** |

**VPS: Hetzner CPX32 (FSN1)**

| Field | Value |
|---|---|
| Provider | Hetzner Cloud (hetzner.com/cloud) |
| Server | CPX32 — 4 vCPU, 8 GB RAM (newer generation than CPX31) |
| OS | Ubuntu 22.04 LTS |
| Region | FSN1 — Falkenstein, Germany |
| Monthly cost | ~$42/mo base · ~$51/mo with backups enabled |
| Hetzner project name | `wavepalace` |

**Why Hetzner CPX32 over alternatives:**
- CPX32 at ~$42/mo vs ~$48/mo on DigitalOcean/Linode for identical specs
- No AWS/GCP ecosystem needed — VPS runs one job: AzuraCast + SRS + FFmpeg

**Why FSN1 (Falkenstein):**
- Avoid ASH (Ashburn): active Load Balancer incident + higher pricing
- Avoid HEL1 (Helsinki): active Object Storage incident at decision time
- Avoid NBG1 (Nuremberg): active Object Storage incident at decision time
- FSN1: no active incidents, lower cost

Scale to CPX42 or CPX52 for 10+ channels.

**Provisioning:** See `docs/VPS_PROVISIONING.md` for full step-by-step guide and smoke test checklist. **Provision the VPS before writing any Slice 4 code** — Slice 4 wires FastAPI to a running VPS rather than setting up both simultaneously.

**Deferral:** VPS provisioning is deferred until Slice 4 (live events) becomes a priority. The ~$42–51/mo is a meaningful ongoing cost before the product generates revenue. The toggle infrastructure (schema + admin UI) ships as a pre-Slice 4 add-on with no VPS dependency — activation requires only VPS provisioning + a database flag flip, no code deploy.

### Mux tradeoffs — accepted at current scale

The mux approach remains the active VRChat delivery method. Known limitations
and their impact at current scale (3 channels, stable playlists, no live events):

| Limitation | Impact at current scale |
|---|---|
| VRChat worlds not synchronized — each listener starts MP4 at a different time | Low — listeners don't expect radio sync yet |
| Playlist updates require re-mux (1–15 min encode) | Low — stable playlists, infrequent changes |
| Practical track limit ~15–20 per channel (MP4 length) | Low — current channels are well under limit |
| Live events (Slice 4) completely blocked until VPS is live | **Hard dependency — the only blocking limitation** |
| No server-side now-playing source of truth | Low — web player tracks index locally |

Revisit when any limit is hit or live events are scheduled.

### Monthly cost (true streaming — when VPS is active)

| Service | Tool | Cost/mo |
|---|---|---|
| VPS (AzuraCast + SRS + FFmpeg) | Hetzner CPX32 FSN1 | ~$42 base / ~$51 with backups |
| Media storage | Cloudflare R2 | ~$0–1 |
| Frontend | Vercel free | $0 |
| Backend | Render Starter | $7 |
| Database | MongoDB Atlas Flex | $8–30 |
| Cloudflare proxy | Free plan | $0 |
| **Total (streaming active)** | | **~$57–89/mo** |

---

## ~~Slice 1: Animated / looping video backgrounds~~ — COMPLETE (v0.4.0)

Frontend and data layer fully shipped ahead of schedule. `ChannelPlayer.tsx`
renders a muted looping `<video>` when `visualLoopUrl` is present, falls back
to `<img>` when not. All 3 seed channels have `visualLoopUrl` populated.
`mux_service.py` handles both image and video covers via `_VIDEO_EXTS`
detection — no mux changes needed when a loop is set.

**Admin UI toggle** (`Visual type: ○ Image ● Video Loop`) with per-channel
upload slots shipped in Slice 3 (v0.7.0). The mux pipeline already supported
it — only the admin interface was pending.

## Slice 1B: Channel & Host Info Display on Player (COMPLETE)

Channel title, "Hosted by {host}", genre, and mood are displayed inside the
`ChannelPlayer` gradient overlay. Redundant title/host/tags block removed from
below the player; description kept as standalone paragraph.

## Planned: VRChat MP4 Overlay Parity (COMPLETE)

Burn the same channel info (title, host, genre · mood) into the muxed VRChat
MP4 via FFmpeg `drawtext` so VRChat viewers see it without any UI layer.
Text sits over a semi-transparent dark band at the bottom of the 1280×720
frame — mirroring the web player gradient. Video-loop path burns text into the
30-second segment encode only; the final mux stays `-c:v copy` (no extra CPU).
Depends on: `fonts-dejavu-core` installed on Render.
Re-mux required after deploy (`POST /api/mux/all` + Cloudflare cache purge).

## ~~Slice 2: DJ / Artist submission requests~~ — COMPLETE

A public `/submit` form lets hosts, DJs, and artists submit channel proposals
for review. Submissions are stored with `status = "pending"` and are never
auto-published.

- `GET /api/submission-options` returns admin-managed genre, mood, energy, and
  theme options with seed fallback
- `POST /api/submissions/upload-image` validates JPEG/PNG/WebP profile images
  up to 5 MB and uploads them to R2 under `submissions/images/`
- `POST /api/submissions` validates option values, sample links, description
  length, contact email, and rights attestation before storing the pending
  submission
- Frontend fetches chip options from the API, uploads profile images on select,
  and shows a success confirmation without adding admin review UI

Delivered in Slice 3 (v0.7.0): review queue UI, option management UI, JWT auth,
admin approval/publishing workflows, channel CRUD, drag-to-reorder tracks,
R2 media uploads, options management, mobile parity.

## ~~Slice 3: Music director dashboard (Admin UI)~~ — COMPLETE (v0.7.0)

Internal tool to review submissions, publish/unpublish channels, edit metadata,
manage tracks and playlists, upload media, and configure channel info and host
info — all through WavePalace UI with no access to third-party dashboards.

Requires auth (introduced here, not before). Covers all admin operations listed
in the "Production streaming architecture" section above. WavePalace FastAPI
acts as the single control plane — AzuraCast, SRS, R2, and MongoDB are
internal implementation details the admin never touches directly.

Admin scope: Songs, Ads, Videos, Channel info, Host info, Stream health.


### ~~Slice 3 add-on: Track metadata schema + now-playing display~~ — COMPLETE

Show "Now playing: Artist — Track Title" on the player. This shipped ahead of
the Slice 3 admin dashboard: `playlist` now uses `TrackItem` objects
`{ url, title, artist }`, and the web player shows title + artist in the
overlay when metadata is present.

- Seed data includes title/artist metadata for each track
- Backend and frontend channel contracts expose `playlist: TrackItem[]`
- Web player displays current track title + artist in the overlay, updates on
  track advance
- VRChat mux burns per-track now-playing text into MP4 output using timed
  FFmpeg `drawtext`
- Future Slice 3 admin UI should let admins enter title/artist when uploading
  or editing tracks
- For true streaming (Slice 3 + VPS): AzuraCast's `/api/nowplaying` endpoint
  returns the currently playing track in real time — player polls or subscribes
  via SSE, no manual entry needed

Remaining Slice 3 work is admin editing and live-stream now-playing integration,
not the TrackItem schema or static playlist display.

### Slice 3 add-on: Play count tracking

Simple play event counter. When the user hits Play on a channel, the frontend
calls `POST /api/channels/{slug}/play`. Backend increments a `playCount` field
in MongoDB. No dashboard yet — data collection only, so Slice 7 has real data
to work with.

Lightweight enough to ship alongside the admin dashboard. Depends on Slice 3
(auth + backend infrastructure in place).

### Slice 3 add-on: External Stream Passthrough

**Status: 🔲 NOT STARTED · No VPS required · Small effort**

A creator already has a VRChat-compatible stream running — a VRCDN URL, an
OBS → personal RTMP server → HTTP-TS output, or any direct `.ts` or `.mp4`
link. The admin pastes that URL into a `liveStreamUrl` field on the channel
editor. When set, VRChat players hit the external stream directly. WavePalace
serves as the directory and web experience; the stream infrastructure belongs
to the creator.

**Schema addition:**

```python
liveStreamUrl: str | None = None
# When set, overrides vrchatPlaybackUrl for VRChat delivery.
# Cleared when channel reverts to mux or WavePalace streaming.
# VRChat-only — web player uses playlist MP3s regardless.
```

**Full VRChat URL routing chain (three tiers, evaluated in order):**

```
1. liveStreamUrl set    → serve liveStreamUrl  (external passthrough — creator's infrastructure)
2. streamingActive true → serve vrchatPlaybackUrl  (WavePalace stream — live/{slug}.ts)
3. default              → serve vrchatFallbackUrl  (mux MP4 on R2)
```

**Admin UI:**
- Location: channel detail/edit page in the Slice 3 admin dashboard
- Section label: **External Stream Passthrough**
- Field label: **External Stream URL**
- Input: URL text field · placeholder: `https://stream.vrcdn.live/live/{key}.ts`
- Helper text: "When set, VRChat players will stream directly from this URL. Leave blank to use WavePalace mux or streaming."
- Clear button: removes `liveStreamUrl` and reverts to normal routing
- Warning when populated: "WavePalace has no control over this stream's uptime. If the external stream goes down, this channel will go dark for VRChat players."

**Supported URL formats:**

| Source | Format | VRChat compatible |
|---|---|---|
| VRCDN | `https://stream.vrcdn.live/live/{key}.ts` | Yes |
| OBS → personal RTMP → HTTP-TS | `https://their-server/live/{slug}.ts` | Yes |
| Direct MP4 link | `https://example.com/stream.mp4` | Yes |
| HLS stream | `https://example.com/stream.m3u8` | Partial — some VRChat players only |
| Twitch / YouTube public stream | Public URL | No — ToS violation, not supported |

**Note on VRCDN:** The prior roadmap decision "No VRCDN — all streaming
self-hosted" applies to WavePalace's own infrastructure. Passthrough of a
creator's existing VRCDN URL via `liveStreamUrl` is acceptable — WavePalace
is consuming their stream, not building on the VRCDN platform.

**Known tradeoffs:**
- VRChat URL changes if the creator rotates their stream key or moves infrastructure — WavePalace does not own this URL
- No uptime control — if the creator's stream dies, the channel goes dark for VRChat players
- No burned-in overlay — title, host, now-playing are not applied; stream bypasses FFmpeg entirely
- Web player compatibility varies — VRCDN HTTP-TS works in some browsers; HLS requires HLS.js (not currently in the web player); plain `.mp4` works everywhere
- Web player falls back to mux MP4 audio (`playlist` MP3s) regardless of `liveStreamUrl` — passthrough is VRChat-only

**Best use case:** Occasional or guest channels where a creator brings their
own stream infrastructure and WavePalace surfaces it in the directory. Not
suitable as a permanent channel setup — use Slice 4 Link-In for that.

**Relationship to Slice 4 Link-In:** External Stream Passthrough is a
low-friction stopgap — the stream URL goes directly to the creator's
infrastructure with no WavePalace control. Slice 4 Link-In is the production
version: WavePalace pulls the external stream via FFmpeg, rebroadcasts it on
its own permanent `live/{slug}.ts` URL, applies the overlay, and controls
fallback. Use Passthrough for guest/occasional channels; use Link-In for
permanent live channels.

**Validation:** `liveStreamUrl` must pass the same reachability check as other
media URLs — the Slice 5 media validation service is already built; reuse it.

## Pre-Slice 4 add-on: Streaming readiness + mux/stream toggle

**Status: 🔲 NOT STARTED**

Build all streaming-readiness code now — schema changes, player switching logic,
and admin toggle controls — with **no VPS dependency**. When the Hetzner VPS is
provisioned, activation requires only a database flag flip. Zero code changes.
Zero deploys.

**Why build now:** Schema and admin UI work is minimal and costs nothing extra.
Having the toggle infrastructure in place means Slice 4 only needs VPS wiring +
live event endpoints — not frontend work or a schema migration mid-deploy.

### Schema additions

```python
streamingActive: bool = False      # default False — all channels start on mux
                                   # True = serve live/{slug}.ts (VPS must be live)
vrchatFallbackUrl: str | None      # permanent mux MP4 URL — populated by mux/all
                                   # never overwritten by streaming cutover
```

Player switching logic (VRChat URL routing):
```
if streamingActive → serve live/{slug}.ts  (streaming — VPS must be live and verified)
else               → serve vrchatFallbackUrl  (mux MP4 on R2 — always available)
```

`streamingActive` defaults to `False` on all channels. No channel switches to
streaming until explicitly toggled after the VPS is verified end-to-end.

### Admin UI controls (all safe while VPS is dormant)

**A. Per-channel streaming toggle**
- Location: each channel's admin detail page
- Control: `Live Stream ↔ Mux MP4` toggle
- Sets `streamingActive` on that channel in MongoDB
- Warning shown when `streamingActive = true` but VPS is not confirmed live

**B. Bulk toggle — all channels at once**
- Location: top of `/admin/channels` list
- Two buttons: `Switch All to Live Stream` and `Switch All to Mux`
- Sets `streamingActive` on every channel in one operation
- Requires confirmation dialog before executing
- Primary use case: first activation when VPS goes live, or emergency fallback if VPS goes down

**C. Mux refresh controls**
- Per-channel: `Refresh Mux` button → `POST /api/channels/{slug}/mux` → updates `vrchatFallbackUrl`
- All channels: `Refresh All Mux` → `POST /api/mux/all` → updates all `vrchatFallbackUrl` fields
- Shows last mux refresh timestamp per channel
- Safe to run at any time regardless of streaming status

### Activation sequence (when VPS is ready — zero code changes)

1. Provision Hetzner CPX32 FSN1 VPS (see `docs/VPS_PROVISIONING.md`) — ~2–3 hrs
2. Verify `https://stream.wavepalace.live/live/{slug}.ts` plays in VLC and VRChat
3. Run `POST /api/mux/all` to ensure `vrchatFallbackUrl` is current before switching
4. Use per-channel toggle to switch channels one at a time — verify each in VRChat
5. Or use bulk toggle to switch all at once when confident
6. Mux MP4s remain on R2 as warm fallback indefinitely

### When to provision the VPS

Defer until any of these become true:
- Slice 4 (live events) is the next build priority
- A channel playlist exceeds ~15–20 tracks and re-mux delays are disruptive
- Playlist update frequency makes 1–15 min turnaround unacceptable
- First live event is scheduled

---

## Future slice 4: Live event streaming — Link-In and Ingest Keys

> **Note:** External Stream Passthrough (Slice 3 add-on) covers the immediate
> use case of surfacing creator-owned streams with no WavePalace infrastructure.
> Slice 4 Link-In is the production version — WavePalace pulls the external
> stream via FFmpeg, rebroadcasts on its own permanent URL, applies the overlay,
> and controls fallback. The `liveStreamUrl` field (Passthrough) and
> `streamingActive` flag (Slice 4) are separate controls on the same channel.

Extends channels with a **live event mode** alongside the regular playlist mode.
When a live event is active the playlist stream pauses and the live feed plays
on the channel's same static URL — VRChat players in-world see the live feed
automatically. When the event ends the channel reverts to playlist.

### Option F — Link-In (admin pastes an external stream URL)

Admin pastes an HLS, RTMP, or SRT URL directly in the WavePalace admin UI.
WavePalace pulls from it via FFmpeg and rebroadcasts on the channel's existing
HTTP-TS URL. The channel URL never changes.

```
[External stream: HLS / RTMP / SRT]
        ↓  admin pastes URL in WavePalace admin UI
[WavePalace FastAPI] — validates URL, starts ingestion
        ↓
[FFmpeg pull process] — pulls from external URL
        ↓  pushes RTMP internally
[SRS] — outputs HTTP-TS at channel's existing URL
        ↓
stream.wavepalace.live/live/[slug].ts — unchanged
        ↓               ↓
[VRChat players]   [Web player]
```

FFmpeg pull command:
```bash
ffmpeg -re -i [ADMIN_PASTED_URL] \
  -c:v copy -c:a aac -b:a 256k \
  -f flv rtmp://localhost/live/late-night-house
```

**Supported URL formats:**
| Source type | URL format | Works? |
|---|---|---|
| OBS → personal RTMP server | `rtmp://their-server/live/key` | Yes |
| OBS → SRT endpoint | `srt://their-server:9000` | Yes |
| Any HLS stream (private) | `https://example.com/stream.m3u8` | Yes |
| Vimeo Live (private link) | HLS URL from Vimeo embed | Yes |
| WavePalace's own OBS push | `rtmp://stream.wavepalace.live/ingest/key` | Yes — best for owned events |
| Twitch public stream | HLS URL | ToS violation — not supported |
| YouTube Live public | HLS URL | ToS violation — not supported |

Content creators cannot send a Twitch or YouTube link — rebroadcasting those
without platform permission violates ToS. They stream to a URL they own or
control instead (OBS → their own RTMP/SRT endpoint, or WavePalace provides
ingest credentials — see below).

**Use case coverage:**
| Use case | How it works | URL they send |
|---|---|---|
| DJ streams a live set | OBS → their own SRT/RTMP endpoint or free relay. Sends URL to admin | `rtmp://dj-server.com/live/key` or SRT |
| Gamer streams gameplay | OBS → private RTMP endpoint (not Twitch). Sends URL | `rtmp://their-endpoint/live/key` |
| Director screens a film | OBS or Wirecast → private HLS or RTMP. Sends URL | `https://private-hls.com/event.m3u8` |
| WavePalace runs own event | WavePalace OBS → pushes directly to WavePalace SRS ingest. No external URL needed | Internal RTMP — admin clicks "Go Live" |

### Recommended approach: WavePalace-provided ingest keys (push mode)

Instead of creators maintaining their own relay servers, WavePalace admin
generates a one-time stream key per event. Creator enters it in OBS — done.

```
Admin UI → "Create Live Event" on a channel
→ Generates stream key
→ Admin or organizer receives:
     Server: rtmp://stream.wavepalace.live/ingest
     Key:    late-night-house-[secret-token]
→ Creator enters into OBS — one field, no infrastructure required
→ WavePalace SRS accepts stream, outputs on channel's existing HTTP-TS URL
→ VRChat URL unchanged — in-world players see the live feed automatically
→ Admin clicks "End Event" — channel reverts to playlist
```

This is the cleanest experience for all parties — admin generates credentials,
creator enters them in OBS, no one runs extra infrastructure.

Creator setup options (when ingest keys are not used):
- **restream.io** — streams to multiple destinations including a custom RTMP URL simultaneously
- **OBS → personal SRS on a $4/mo VPS** — creator runs SRS, sends WavePalace the `.ts` URL

### Sub-modes summary

| Sub-mode | Trigger | Use case |
|---|---|---|
| **Ingest key (push)** | Admin generates key → creator uses in OBS | DJ sets, gameplay, film screenings, WavePalace events |
| **Link-In (pull)** | Admin pastes external HLS/RTMP/SRT URL | Creator already has a running stream endpoint |
| **AzuraCast DJ input** | Admin enables Live DJ mode in AzuraCast via WavePalace UI | Audio-only live events; visual loop continues as backdrop |

AzuraCast DJ input (audio-only) is available as a **Slice 3 add-on** — it uses
AzuraCast's built-in live takeover feature with no additional infrastructure.
Full A/V ingest (push and pull) requires the VPS to be provisioned.

Depends on: Slice 3 (admin dashboard + auth) + production streaming
architecture (AzuraCast + SRS VPS provisioned and running).

> **Sequencing note:** Slice 4 is now scheduled **after Slice 6 (Sponsor
> Primitive)** so live events ship sponsorable. See `docs/MONETIZATION_PLAN.md`.

> **Slice 4 scope is VPS + wiring only.** Toggle infrastructure (schema,
> player logic, admin UI controls) ships as a pre-Slice 4 add-on — no frontend
> work needed at Slice 4 activation. Slice 4 = VPS provisioning (Hetzner CPX32
> FSN1, `docs/VPS_PROVISIONING.md`) + AzuraCast/SRS/FFmpeg wiring + FastAPI
> proxy + live event endpoints. Activation = flip `streamingActive` via existing
> admin bulk toggle after VPS smoke test passes.

### Slice 4 add-on: Event Sponsorship (QR bridge + sponsor frame)

Build alongside Slice 4. Depends on Slice 6's `sponsor` object and Slice 4's
SRS/FFmpeg path. When a live event starts on a channel with a live sponsor:

- Prepend a 3–5s "This set sponsored by {sponsor.name}" intro frame (logo + text)
  to the event feed via the FFmpeg combiner.
- Burn a small, low-opacity **QR code** (encoding `sponsor.clickUrl` or the
  channel's follow code) into a corner of the live video — the only way to make a
  baked VRChat ad actionable, since the in-world player isn't clickable.
- Route the QR to `GET /s/{token}` → log a `sponsor_qr_scan` event → 302 to the
  destination, so scans are attributable.

This monetizes the exact moment a host drops a channel into a VRChat world. Full
build prompt in `docs/MONETIZATION_PLAN.md`.

## ✅ COMPLETE — Slice 5: Media URL validation & compatibility checker (v0.8.0)

HTTPS/reachability/content-type/VRChat-compat checks via `POST /api/admin/channels/{slug}/validate-urls`.
"Check URLs" button in admin channel edit form. 12 tests with respx mocks. See CHANGELOG [0.8.0].

## Slice 6: Sponsor Primitive (thin monetization) — ✅ COMPLETE (v0.9.0)

The first monetization surface, **resequenced ahead of Slice 4** so live events
are sponsorable on day one. Supersedes the old "Featured / sponsored channels"
(now folded in as the directory-slot surface). Full rationale, ad inventory,
data model, endpoints, and a copy-paste build prompt live in
`docs/MONETIZATION_PLAN.md`.

**Key insight:** WavePalace already has a visual layer on every channel *and* a
mux pipeline that bakes it into the VRChat MP4 — so sponsorship rides with the
channel into a VRChat world, near-zero impact on listening.

**Scope (thin):**
- `sponsor: Sponsor | None` on Channel (`apps/backend/app/schemas/sponsor.py`)
  with `sponsor_is_live()` date-window logic in the service layer.
- Admin sponsor panel (`PATCH /api/admin/channels/{slug}/sponsor`, JWT) — logo
  upload to R2, name, text, click URL, placement, active window, "Featured" toggle.
- Web Tier-1 overlays (zero audio impact): logo bug, sponsored lower-third,
  pause-screen takeover. Impression/click events via the play-event path
  (`POST /api/channels/{slug}/sponsor/{impression,click}`).
- Sponsored share card (OG image) on the channel page.
- Featured directory slot + "Sponsored" badge when `sponsor.isFeatured` and live.
- VRChat parity: burn the sponsor lower-third (and logo bug) into the muxed MP4
  via the existing `mux_service.py` drawtext/overlay path — no re-encode regression.

**Out of scope (→ Slice 6B):** multi-sponsor rotation, CPM billing, audio stings,
intro/outro splash frames, idle card, sponsor reporting dashboard.
Depends on: Slice 3 (admin) ✅, Slice 1B drawtext ✅, mux pipeline ✅. No VPS.

## Slice 6B: Full Ad Stack — after Slice 4

Builds out the rest of the ad inventory once live events draw real audience.
Full spec + build prompt in `docs/MONETIZATION_PLAN.md`.

**Scope:** multi-sponsor weighted rotation (`Channel.sponsors: list`), web CPM
measurement + nightly rollups, intro/outro splash frames (mux concat) for
evergreen channels, idle/inactivity card, **opt-in** between-track audio stings +
sponsored station ID (via AzuraCast jingle rotation — cheap once Slice 4 is
provisioned), and a sponsor reporting dashboard
(`GET /api/admin/sponsors/report`: impressions, clicks, QR scans, channel-time).

**Guardrails:** audio surfaces are opt-in per channel and between-track only;
VRChat is sold on reach + scans, never CPM. Depends on: Slice 4 (AzuraCast).

## Future slice 7: Production analytics

Admin-facing dashboard surfaced in the Slice 3 admin UI. Data collected by
Slice 3 add-ons feeds directly into this dashboard.

**Scope:**
- Play counts (collected via `POST /api/channels/{slug}/play` from Slice 3 add-on)
- Link-copy events (Web Link + VRChat Link copy buttons)
- Channel popularity ranking
- Privacy-respecting — no user accounts required, no PII stored

## Future slice 8: Play Metrics + Artist Reporting

Collect structured play and engagement events across web and VRChat contexts,
roll them up into per-artist, per-channel, per-host, and per-event reports, and
expose a licensing-ready usage log and public-safe overlay metrics payload.

**Phases:**
- Phase 1 (Slice 3 add-on): `POST /api/events` endpoint, anonymous session ID,
  `play_started` / `play_30s` / `heartbeat_15s` / `play_stopped` events from
  web player, stored in `play_events` MongoDB collection
- Phase 2 (Slice 3 add-on): Nightly rollup job → `metric_rollups` collection;
  `qualified_plays`, `unique_listeners`, `listener_minutes`,
  `aggregate_tuning_hours` per channel per day
- Phase 3: `GET /api/metrics/artists/{id}`, `/channels/{id}`, `/hosts/{id}`,
  `/events/{id}` — admin-only report endpoints
- Phase 4: `GET /api/usage-logs/export.csv` — track-level usage log with ISRC,
  artist, duration; labeled as internal metric, not certified royalty data
- Phase 5: `GET /api/overlay/{campaignId}/metrics` — public-safe payload
  (follower count, saves, qualified plays, active code) for stream compositor

**Key terminology rule:** Use "WavePalace-qualified play" and "listener session"
— not "stream." Qualified play = ≥ 30 continuous seconds. VRChat-derived counts
are always labeled estimated.

**Licensing note:** This feature creates a clean data foundation that could
support future reporting. It does not automatically satisfy ASCAP, BMI, SESAC,
SoundExchange, or any PRO/label reporting requirement.

Depends on: Slice 3 add-ons (play count + track metadata schema) for Phase 1–2.
Full report endpoints (Phase 3+) should follow Code Capture (Slice 9) so
follow/contact data exists to report on.

## Future slice 9: Code Capture + Follow Intent + Notification Stack

VRChat listeners are passive — they cannot click links from inside a VRChat
world. Code Capture bridges that gap: WavePalace burns a short code into the
VRChat stream overlay, the listener types it at `wavepalace.live` on a phone or
browser, and WavePalace resolves it to the current channel, artist, host, or
event so the listener can follow.

This is the primary mechanism for converting VRChat listeners into verified
followers and contacts. It feeds directly into Slice 8 reporting through
`code_resolved` and `follow_created` events.

Depends on: Slice 3 (admin dashboard to generate and manage codes) + Slice 8
Phase 1–2 (event tracking to record code_resolved and follow_created events).

### UX principle

Decide for the listener at capture, then give them control after. Discord is the
prominent capture CTA because the VRChat audience is Discord-native. Email is
available as a visually subordinate fallback. Browser push and VRChat username
belong in preferences after follow, not in the first capture moment.

### Notification stack

| Channel | Use case | Priority |
|---|---|---|
| Discord DM via bot | Follows, live alerts, announcements | Primary |
| Browser push (Web Push API) | Live alerts for web listeners | Secondary |
| Email via Resend | Advance announcements, account management, fallback | Fallback |
| VRChat username | Attribution and analytics only | Identity anchor |
| SMS via Twilio | "Going live right now" only | Future add-on — do not build now |

SMS is excluded from Slice 9. The data model may be future-ready for SMS, but
there is no SMS UI or API submission path until demand proves Discord and
browser push are insufficient.

### Code generation and resolution

Store codes in a MongoDB `codes` collection:

```python
class CodeDocument(BaseModel):
    code: str                    # e.g. "WAVE42" — 6 chars, uppercase alphanumeric
    channel_slug: str
    entity_type: str             # "channel" | "artist" | "host" | "event"
    entity_id: str
    created_at: datetime
    expires_at: datetime | None  # None = permanent; live event codes expire
    active: bool = True
```

Planned endpoints:

```http
POST /api/admin/codes
GET  /api/codes/{code}
POST /api/codes/{code}/follow
```

Code generation uses 6-character uppercase alphanumeric codes and checks
collisions against existing active codes. Admins generate codes from the Slice 3
dashboard per channel or per live event.

Resolution response (`GET /api/codes/{code}`):

```json
{
  "code": "WAVE42",
  "entity_type": "channel",
  "entity_id": "...",
  "display_name": "Late Night House",
  "host_name": "DJ Nova",
  "genre": "House",
  "mood": "Late Night",
  "cover_image_url": "..."
}
```

### Capture UX

Add a persistent code entry field in the site header and/or home page. It should
be small, always visible, and never buried.

The `/follow/{code}` page resolves the code and displays:

```text
[Channel cover image / visual]

Late Night House
Hosted by DJ Nova · House · Late Night

Follow this channel

[Connect Discord]

or enter your email ↓

[_________________________] [Follow]
```

Rules:
- Discord is the only prominent CTA
- Email is secondary and visually subordinate
- Browser push and VRChat username are not shown at capture
- SMS is not shown at capture
- No account creation, username, password, or profile form
- Expired/inactive codes show: "This code is no longer active — tune in at wavepalace.live"

### Follow submission and identity anchoring

`POST /api/codes/{code}/follow` accepts one of:

```json
{ "channel": "discord", "discord_user_id": "...", "discord_username": "..." }
```

```json
{ "channel": "email", "email": "user@example.com" }
```

```json
{ "channel": "browser_push", "push_subscription": { "...": "..." } }
```

It also accepts optional attribution:

```json
{ "vrchat_username": "VRCUSER_xyz" }
```

VRChat username is stored for attribution only and is never used for delivery.

Store follows in a MongoDB `follows` collection:

```python
class FollowDocument(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    channel_slug: str
    notification_channel: str       # "discord" | "email" | "browser_push" | "sms"
    discord_user_id: str | None
    discord_username: str | None
    email: str | None
    phone: str | None               # future-ready — unused until SMS is activated
    push_subscription: dict | None
    vrchat_username: str | None     # attribution only
    confirmed: bool = False         # True after double opt-in for email
    created_at: datetime
    code_used: str
```

Confirmation rules:
- Discord requires no extra confirmation after OAuth grants permission
- Email requires Resend double opt-in before the follow becomes active
- Browser push requires browser permission and no extra confirmation

### Discord bot (notification delivery)

A Discord bot DMs followers when triggered events occur (channel going live,
event announced, new guest DJ). The bot is the primary delivery path.

- OAuth flow: listener clicks "Connect Discord" → Discord OAuth2 → bot stores
  `discord_user_id` + `discord_username` → confirms follow → DM sent
- Bot token stored in `DISCORD_BOT_TOKEN` (Render env var)
- OAuth client ID stored in `DISCORD_CLIENT_ID`
- Bot scope: `bot` + `dm_channels` only — no server permissions needed
- Failure: if DM fails (user blocked bot, DMs closed), mark delivery failed;
  do not retry more than once; log event for admin visibility

### Browser push (Web Push API)

For web listeners who want live alerts without Discord. Secondary to Discord.

- VAPID keys generated once: `VAPID_PUBLIC_KEY` + `VAPID_PRIVATE_KEY` (Render)
- `push_subscription` blob from `navigator.serviceWorker.pushManager.subscribe()`
  stored verbatim in `FollowDocument.push_subscription`
- Subscription is per-device and expires; silently drop stale subscriptions on
  first send failure
- Push payload: `{ title, body, icon, url }` — keep small (< 128 chars body)

### SMS stub (future add-on — do not build in Slice 9)

Schema is future-ready with `phone` field in `FollowDocument` but no UI or API
path for SMS is exposed until demand proves Discord/push are insufficient.

```python
async def _send_sms(phone: str, message: str) -> None:
    # SMS not yet active — A2P 10DLC carrier registration and TCPA compliance
    # required before enabling. Use Discord or browser push for live alerts.
    raise NotImplementedError("SMS delivery is not enabled in this build.")
```

Required before activating: Twilio A2P 10DLC registration + TCPA opt-in flow.
Env vars (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`) are
documented in `HANDOFF.md` under "Future (not active)" — not added to Render.

### Notification service signatures

```python
# apps/backend/app/services/notification_service.py
async def notify_channel_going_live(channel_slug: str) -> None: ...
async def notify_event_announced(channel_slug: str, event: EventDocument) -> None: ...
async def notify_new_guest_dj(channel_slug: str, dj_name: str) -> None: ...
```

Each function fans out to all active follows for the channel:
1. Discord DMs (primary)
2. Web push notifications (secondary)
3. Resend email (fallback — only for `confirmed=True` email follows)
4. SMS — raises NotImplementedError until activated

### Listener preferences page (`/follows`)

After following, listeners can return to `wavepalace.live/follows` to:
- View their active follows
- Update notification preferences (Discord vs email vs push)
- Unfollow channels

Identity is resolved from session/cookie tied to their Discord user ID or
confirmed email — no separate account or password.

Endpoints:
```http
GET    /api/follows         # authenticated listener's own follows
PATCH  /api/follows/{id}    # update preferences
DELETE /api/follows/{id}    # unfollow
```

### Admin code management (in Slice 3 dashboard)

Admins generate codes from the admin dashboard per channel or per event.

```http
POST /api/admin/codes       # generate code for a channel/entity
GET  /api/admin/codes       # list all codes with status
DELETE /api/admin/codes/{code}  # deactivate code
```

Code generation rules:
- 6-character uppercase alphanumeric (e.g. `WAVE42`)
- Collision check against active codes before persisting
- Permanent by default; live event codes have an `expires_at`
- Admin can deactivate a code; expired/inactive codes show a friendly message

### Build order

1. Backend: `codes` collection + `CodeDocument` + admin code generation endpoints
2. Backend: `GET /api/codes/{code}` public resolve
3. Frontend: code entry field in site header + `/follow/{code}` page
4. Backend: `POST /api/codes/{code}/follow` — Discord and email paths
5. Backend: Resend double opt-in email flow
6. Backend: Discord OAuth + bot DM delivery
7. Frontend: browser push subscription + VAPID integration
8. Backend: `notification_service.py` fan-out functions
9. Frontend: `/follows` listener preferences page
10. Admin UI: code management panel in Slice 3 dashboard
11. Tests: code resolution, follow submission, duplicate-follow guard, expiry
12. Docs: update API_CONTRACT.md, CHANGELOG.md, STATUS.md

### Done criteria

- [ ] Admin can generate a 6-char code for a channel from the admin dashboard
- [ ] `GET /api/codes/{code}` returns channel info or expired message
- [ ] VRChat listener enters code on web → `/follow/{code}` page loads channel card
- [ ] Discord OAuth follow → bot DMs the listener confirming follow
- [ ] Email follow → Resend double opt-in → `confirmed=True` in DB
- [ ] Browser push follow → listener receives push on next trigger event
- [ ] `notify_channel_going_live()` fans out to all follow channels
- [ ] SMS path raises `NotImplementedError`; no SMS UI or endpoint exposed
- [ ] Expired/inactive codes show friendly "no longer active" message
- [ ] VRChat username stored for attribution; never used for delivery
- [ ] Listener can view + manage follows at `/follows`
- [ ] All backend paths have pytest coverage

**Do not build future slices until explicitly requested.**

---

## Legal / DMCA Takedown Form — COMPLETE

### Scope

DMCA-compliant copyright takedown intake form, admin review queue, and SMTP notification.

### What shipped

- `/legal` — legal index page (takedown, privacy placeholder, terms placeholder)
- `/legal/takedown` — public DMCA form with all required DMCA fields (claimant, org, email, role, infringing URL, description, proof, good-faith + accuracy checkboxes)
- `/legal/takedown/submitted` — confirmation page
- `/admin/takedowns` — admin queue: table view + drawer (status dropdown, notes, save)
- `POST /api/takedowns` — public submission; Pydantic validators enforce `good_faith=True`, `accuracy=True`; fires best-effort SMTP email to `ADMIN_EMAIL`
- `GET /api/takedowns` / `GET /api/takedowns/{id}` / `PATCH /api/takedowns/{id}/status` — admin endpoints
- Status flow: `pending → reviewed → actioned | dismissed`
- MongoDB-backed `TakedownRepository` + `SeedTakedownRepository` fallback
- "Takedowns" nav item in admin sidebar
- 15 backend tests

---

## Slice 7 — Production Analytics Dashboard — COMPLETE

### Scope

Read-only admin analytics page aggregating existing data: channel play counts, confirmed follows (by notification channel), and active follow codes. No new event collection — Slice 8 adds event-level tracking.

### What shipped

- `GET /api/admin/analytics` — admin-auth required; returns `AnalyticsSummaryResponse` with:
  - `total_plays` — sum of all channel `playCount` values
  - `total_follows` — confirmed follows only
  - `total_channels` / `published_channels` / `channels_with_sponsor`
  - `follow_breakdown` — totals by `discord` / `email` / `browser_push`
  - `top_channels` — all channels sorted by `play_count` descending; each includes per-channel follow breakdown + active code count
  - `generated_at` timestamp
- **No PII** — individual email addresses, Discord user IDs, and Discord usernames are never returned
- `/admin/analytics` — dashboard page: 4 stat cards · follow breakdown pills · full channel leaderboard table (unpublished channels shown muted)
- "Analytics" nav link in admin sidebar
- `get_all_follows()` added to `FollowRepository` ABC + both implementations for cross-channel aggregation
- 14 backend tests

---

## Slice 10 — Identity & Roles — COMPLETE

**Type:** Foundation slice — no host-facing UX yet. Slices 11 (Host Onboarding & Ownership)
and 12 (Host Dashboard) build directly on it.

**Goal:** Replace the single shared-secret admin login with a real user-identity system that
supports multiple login methods and stackable roles, and migrate the existing admin onto it
without running two auth systems side by side.

### Role model (locked)

- Global roles live on the `User`: `roles: list["music_director" | "admin"]` (empty = plain listener).
- **"Host" is NOT a global role** — it is derived from channel ownership (`Channel.owner_ids`,
  added in Slice 11). A label managing 10 channels is one user listed as owner on 10 channels.
  "Host + Music Director" is just `roles: ["music_director"]` plus owning a channel.
- Admin grants/revokes roles. Music Director manages content; **Admin manages people.**

### Capability matrix

| Capability | Listener | Host | Music Director | Admin |
|---|:---:|:---:|:---:|:---:|
| Play channels (no login) | ✅ | ✅ | ✅ | ✅ |
| Follow channels / save across devices | ✅ (opt-in login) | ✅ | ✅ | ✅ |
| Edit **own** channel content + metadata | — | ✅ | ✅ | ✅ |
| View **own** channel analytics | — | ✅ | ✅ | ✅ |
| See/manage **all** channels + submissions | — | — | ✅ | ✅ |
| Invite a host (link) | — | — | ✅ | ✅ |
| Toggle a host/channel's approval requirement | — | — | ✅ | ✅ |
| Grant/revoke roles, manage accounts | — | — | — | ✅ |

(Host and host-onboarding rows are delivered in Slices 11–12; the matrix is the target end state.)

### What exists today (reuse vs. replace)

| Current piece | File | Fate in Slice 10 |
|---|---|---|
| Single-secret admin login (`ADMIN_SECRET` → `wp_admin_token` JWT cookie) | `core/auth.py`, `routes/admin_auth.py` | **Replaced** — becomes a seeded admin *user*; secret kept only as a bootstrap fallback |
| `get_current_admin` Depends guard | `core/auth.py` | **Generalized** → `get_current_user` + `require_roles(...)` |
| Discord OAuth (listener-only, ties to follow codes) | `routes/auth_discord.py` | **Generalized** — same flow now also issues a login session, not just a follow |
| Resend email sender | `services/notification_service.py` | **Reused** for email-code (magic link) login |
| Frontend admin auth | `features/admin/lib/adminAuth.tsx`, `adminApi.ts`, `/admin/login` | **Migrated** to the new session + role-aware client |

### Data model

```python
class User(BaseModel):
    id: str
    email: str | None = None          # null for Discord-only accounts until linked
    email_verified: bool = False
    display_name: str
    avatar_url: str | None = None
    roles: list[Literal["music_director", "admin"]] = []   # empty = plain listener
    password_hash: str | None = None       # bcrypt; null if no password set
    discord_user_id: str | None = None     # links to Slice 9 Discord identity
    created_at: datetime
    last_login_at: datetime | None = None
    is_active: bool = True

class Session(BaseModel):
    id: str                # opaque uuid stored in the cookie (NOT a JWT)
    user_id: str
    created_at: datetime
    expires_at: datetime
    revoked: bool = False

class EmailLoginToken(BaseModel):
    token_hash: str        # store only a hash of the emailed token
    email: str
    expires_at: datetime   # 15 min
    consumed: bool = False
```

**Session decision (locked): opaque server-side sessions, not stateless JWT.** Revocation
(admin deactivates a user, user logs out everywhere) is required the moment roles exist, and
stateless JWTs can't revoke cleanly. Cookie holds a random session id; the server looks it up.
30-day TTL with sliding refresh.

### Login methods (ship in this order)

1. **Discord OAuth** — generalize `auth_discord.py`; find-or-create `User` by `discord_user_id`,
   issue a session. Existing follow-binding behavior preserved when a `wp_code` is present in state.
2. **Email code / magic link** — `POST /api/auth/email/request` emails a one-time link via Resend;
   `GET /api/auth/email/verify?token=...` find-or-creates a `User` by verified email, issues session.
3. **Email + password** — `register` / `login` with bcrypt. Lowest priority; password reset reuses
   the email-code flow.

All three converge on one helper: `issue_session(user) -> sets wp_session cookie`.

### API endpoints

```
GET  /api/auth/discord/initiate        # supports login intent, not just follow
GET  /api/auth/discord/callback        # find-or-create user, issue session
POST /api/auth/email/request           # { email } -> sends link, always 200 (no enumeration)
GET  /api/auth/email/verify            # ?token=... -> issue session, redirect
POST /api/auth/register                # { email, password, display_name }
POST /api/auth/login                   # { email, password }
GET  /api/auth/me                      # { id, display_name, roles, avatar_url } or 401
POST /api/auth/logout                  # revoke current session
GET   /api/admin/users                 # admin-only — list users
PATCH /api/admin/users/{id}/roles      # admin-only — { roles: [...] }
PATCH /api/admin/users/{id}/active     # admin-only — { is_active }
```

Legacy `POST /api/admin/login` (secret) stays alive as a **bootstrap fallback** only.

### Authorization guards (`core/auth.py`)

```python
get_current_user(...) -> User             # 401 if no valid session
require_roles("admin")                    # 403 if user lacks the role
require_roles("admin", "music_director")  # passes if user has ANY listed role
```

- `admin_channels`, `admin_submissions`, `admin_options`, `admin_codes`, `admin_uploads`,
  `admin_analytics`, `takedowns` → `require_roles("admin", "music_director")`
- New `admin/users` routes → `require_roles("admin")`
- `get_current_admin` kept as a thin shim aliasing `require_roles("admin", "music_director")`
  so existing route files change minimally.

### Migration plan (the load-bearing risk — design up front)

1. **Seed a bootstrap admin user.** If no user has `admin` and `ADMIN_SECRET` is set, the legacy
   `POST /api/admin/login` still works — but on success resolves to (or lazily creates) a single
   seeded admin `User` and issues the **new** `wp_session` cookie instead of `wp_admin_token`.
2. **Dual-cookie grace period.** `get_current_user` accepts a valid `wp_session` *or* a legacy
   valid `wp_admin_token` (treated as the seeded admin) so in-flight sessions survive deploy.
3. **Frontend:** `adminAuth.tsx` switches from cookie-presence to calling `GET /api/auth/me` and
   reading `roles`. `/admin/login` keeps the secret field (bootstrap) and gains Discord + email-link.
4. **Remove `wp_admin_token` issuance** once the seeded admin has logged in via the new flow at
   least once. `ADMIN_SECRET` stays only as break-glass bootstrap.

Seed mode: in-memory `SeedUserRepository` + a single seeded admin (`admin@wavepalace.local`,
no password, login via secret) so the dashboard works with zero DB config.

### New repositories / services / config

- `UserRepository` + `MongoUserRepository` + `SeedUserRepository`
- `SessionRepository` (Mongo + seed/in-memory)
- `AuthService` — find-or-create, session issue/revoke, email-token issue/verify, password hash/verify
- `requirements.txt`: add `passlib[bcrypt]` (Discord/JWT/Resend already present)
- New env var (optional): `SESSION_TTL_DAYS=30`

### Frontend changes

- `useCurrentUser()` hook → `GET /api/auth/me`; exposes `roles` for conditional rendering
- `/admin/login` → Discord button + email-link field + secret field (bootstrap)
- `/admin/layout.tsx` → gate on `roles.includes("admin") || roles.includes("music_director")`
- New `/admin/users` page (admin-only): user table + role checkboxes + active toggle
- Reusable `<SignInPanel />` (Discord + email-link) — Slices 11/12 reuse it for host login

### Out of scope (deferred to Slices 11–12)

- `Channel.owner_ids` + host-derived permissions → Slice 11
- Invite links, host application flow, `auto_publish` flag → Slice 11
- `/host` dashboard → Slice 12
- Listener follow-history adoption on login → bridge in Slice 11 or later
- MFA, "log out everywhere" UI, account-settings page

### Tests (pytest)

- Discord callback creates a user + session; second login reuses the same user
- Email-code: request → verify creates/reuses user, issues session; expired/consumed token → 400;
  request for any email always returns 200 (no enumeration)
- Password register + login; wrong password → 401; bcrypt hash never stored plaintext
- `require_roles` allows/denies across role combinations; deactivated user → 403 with valid session
- `GET /api/auth/me` returns roles; 401 when no session
- Admin user-management: grant/revoke roles, deactivate; music_director → 403 on `/admin/users`
- **Migration:** legacy secret login issues a new session + resolves to seeded admin; legacy
  `wp_admin_token` still accepted during grace period
- Seed-mode parity for all of the above

### Definition of Done

- [ ] `User` + `Session` schemas; User/Session repositories (Mongo + seed)
- [ ] `AuthService` + generalized `core/auth.py` (`get_current_user`, `require_roles`)
- [ ] Discord, email-code, and password login all issue sessions
- [ ] All existing `admin_*` routes gated by `require_roles`, behavior unchanged for current admin
- [ ] `/admin/users` page + role/active management endpoints
- [ ] Legacy secret login migrated to bootstrap fallback; no lockout across deploy
- [ ] Frontend admin gate reads `roles` from `/api/auth/me`
- [ ] All tests pass; seed-mode parity verified
- [ ] Docs updated (`STATUS.md`, `CLAUDE.md`, `FEATURE_SLICES.md`, `MVP_TO_LAUNCH_ROADMAP.md`,
      `CHANGELOG.md`, `API_CONTRACT.md`, `HANDOFF.md`)
