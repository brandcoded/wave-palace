# Feature Slices — WavePalace

Build one slice at a time. Only the MVP slice is implemented.

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

## Future slice 1: Animated / looping video backgrounds

Replace the static cover image background on the web player with a looping MP4
visual per channel. Requires resolving the audio+video mux architecture for
VRChat (either pre-muxed upload or Cloudflare Worker on-the-fly mux service).
Each channel supports either a static image or an animated loop (`visualType`:
`"image"` or `"video"`).

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
