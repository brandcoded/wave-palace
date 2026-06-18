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

**Media architecture:** Each channel has a `playlist` (ordered list of MP3 URLs)
and a `coverImageUrl` stored on Cloudflare R2 (`stream.wavepalace.live`). The
web player cycles through `playlist` automatically and renders `coverImageUrl`
as background. The `audioUrl` field is retained for backwards compatibility and
always equals `playlist[0]`. The VRChat link (`vrchatPlaybackUrl`) points to a
pre-muxed static MP4 (cover image + audio combined) uploaded to R2 — single
direct file, most VRChat-compatible format.

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

## Future slice 1: Animated / looping video backgrounds + admin visual type selector

Replace the static cover image background on the web player with a looping MP4
visual per channel. The schema already supports this via the `visualLoopUrl`
field (optional, falls back to `coverImageUrl`) and the mux service already
detects video vs image by file extension automatically.

**Admin UX — Option B (explicit toggle):**
The music director dashboard (Slice 3) will include a visual type selector per
channel: `Visual type: ○ Image  ● Video Loop`. Each option has its own upload
slot — `coverImageUrl` for the static image, `visualLoopUrl` for the looping
MP4. The admin can switch between them without re-uploading either asset. The
mux service uses `visualLoopUrl` when set, falls back to `coverImageUrl` when
not — no code change needed at mux time.

**Web player:** When `visualLoopUrl` is present, the `<img>` backdrop in
`ChannelPlayer.tsx` is replaced with a muted, looping `<video>` element.
When absent, the existing `<img>` renders as before.

**VRChat mux:** No changes needed — `mux_service.py` already handles both
image and video covers via `_VIDEO_EXTS` detection. Re-running
`POST /api/mux/all` after uploading a loop video produces the correct output.

Depends on: Slice 3 (music director dashboard + auth) for the admin UI.
Can be partially activated now by manually setting `visualLoopUrl` in seed data.

## Future slice 2: DJ / Artist submission requests

A form for hosts/DJs to submit a channel proposal (title, links, rights
attestation). Goes to a review queue — not auto-published.

## Future slice 3: Music director dashboard

Internal tool to review submissions, publish/unpublish channels, and edit
metadata. Requires auth (introduced here, not before).

## Future slice 4: Media URL validation & compatibility checker

Validate that media URLs are reachable, HTTPS, and likely VRChat-compatible;
surface warnings on the channel page.

## Future slice 5: Featured / sponsored channels

Promote channels in the directory. First monetization surface.

## Future slice 6: Production analytics

Play counts, link-copy events, channel popularity — privacy-respecting.

**Do not build future slices until explicitly requested.**
