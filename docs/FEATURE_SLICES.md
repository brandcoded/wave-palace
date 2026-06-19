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

Recommended: **Hetzner CPX31** — 4 vCPU, 8 GB, ~$16/mo.
Scale to CPX41 (8 vCPU, ~$30/mo) for 10+ channels.

### Monthly cost (true streaming)

| Service | Tool | Cost/mo |
|---|---|---|
| VPS (AzuraCast + SRS + FFmpeg) | Hetzner CPX31 | ~$16 |
| Media storage | Cloudflare R2 | ~$0–1 |
| Frontend | Vercel free | $0 |
| Backend | Render Starter | $7 |
| Database | MongoDB Atlas Flex | $8–30 |
| Cloudflare proxy | Free plan | $0 |
| **Total** | | **~$31–54/mo** |

---

## ~~Slice 1: Animated / looping video backgrounds~~ — COMPLETE (v0.4.0)

Frontend and data layer fully shipped ahead of schedule. `ChannelPlayer.tsx`
renders a muted looping `<video>` when `visualLoopUrl` is present, falls back
to `<img>` when not. All 3 seed channels have `visualLoopUrl` populated.
`mux_service.py` handles both image and video covers via `_VIDEO_EXTS`
detection — no mux changes needed when a loop is set.

**Remaining work (Slice 3):** Admin UI toggle (`Visual type: ○ Image ● Video
Loop`) with per-channel upload slots. The mux pipeline already supports it —
only the admin interface is pending.

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

Reserved for Slice 3: review queue UI, option management UI, auth, and admin
approval/publishing workflows.

## Future slice 3: Music director dashboard (Admin UI)

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

## Future slice 4: Live event streaming — Link-In and Ingest Keys

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

## Future slice 5: Media URL validation & compatibility checker

Validate that media URLs are reachable, HTTPS, and likely VRChat-compatible;
surface warnings on the channel page.

## Future slice 6: Featured / sponsored channels

Promote channels in the directory. First monetization surface.

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

## Future slice 9: Code Capture + Follow Intent

VRChat listeners see or hear a short code in the stream (via the visual overlay
or audio cue). They enter it at wavepalace.live. WavePalace resolves the code
to the current artist, channel, host, or event and lets the listener follow,
save, or request updates — bridging the gap between passive VRChat listening and
verified engagement.

This is the primary mechanism for converting VRChat listeners (who cannot click)
into verified followers and contacts. Feeds directly into Slice 8 reporting
(code entries, code conversions, follow-created events).

Depends on: Slice 3 (admin dashboard to generate and manage codes) + Slice 8
Phase 1–2 (event tracking to record code_resolved and follow_created events).

**Do not build future slices until explicitly requested.**
