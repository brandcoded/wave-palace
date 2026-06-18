# API Contract — WavePalace

Base URL (local): `http://localhost:8000`

All responses are JSON. Only published channels with valid playback URLs are
exposed publicly.

## GET /health

Walking-skeleton health check.

```json
{ "status": "ok", "service": "wavepalace-api" }
```

## GET /api/channels

Returns published channels. Optional, case-insensitive query parameters:

| Param  | Example       |
|--------|---------------|
| genre  | `House`       |
| mood   | `Late Night`  |
| energy | `Medium`      |
| theme  | `Lounge`      |

Example: `GET /api/channels?genre=House&mood=Late%20Night`

Response: `200` with an array of Channel objects (see schema below). An empty
array is returned when nothing matches.

## GET /api/channels/{slug}

Returns a single published channel by slug.

- `200` — the Channel object.
- `404` — `{ "detail": "Channel not found" }` when the slug does not exist, is
  unpublished, or is missing required playback URLs.

## Channel object

```json
{
  "id": "channel_late_night_house",
  "slug": "late-night-house",
  "title": "Late Night House",
  "description": "Deep house and midnight lounge energy for VRChat worlds.",
  "genre": "House",
  "mood": "Late Night",
  "energy": "Medium",
  "theme": "Lounge",
  "hostName": "DJ Skyy",
  "coverImageUrl": "https://stream.wavepalace.live/covers/late-night-house.jpg",
  "audioUrl": "https://stream.wavepalace.live/tracks/channel_abc123/track-1.mp3",
  "playlist": [
    "https://stream.wavepalace.live/tracks/channel_abc123/track-1.mp3",
    "https://stream.wavepalace.live/tracks/channel_abc123/track-2.mp3"
  ],
  "vrchatPlaybackUrl": "https://stream.wavepalace.live/muxed/late-night-house.mp4",
  "externalLinks": [{ "label": "Listen elsewhere", "url": "https://example.com" }],
  "rightsStatus": "owned_or_cleared",
  "isPublished": true
}
```

**Field notes:**
- `playlist` — ordered list of MP3 URLs; the web player cycles through these automatically, looping back to index 0 after the last track
- `audioUrl` — always equals `playlist[0]`; retained for backwards compatibility
- `coverImageUrl` — static channel art displayed as the web player background
- `vrchatPlaybackUrl` — pre-muxed static MP4 (cover image + audio combined), uploaded to R2, single direct URL for VRChat video players
- `externalLinks` are attribution only and are never playback sources

## Mux endpoints (internal/admin — no auth for MVP)

These endpoints require R2 credentials to be set on the server
(`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`).
They are not exposed in the public frontend. Call them via the Render shell
or a direct API call when you need to produce muxed MP4s.

### POST /api/channels/{slug}/mux

Downloads the channel's `coverImageUrl` and `audioUrl`, runs FFmpeg to mux
them into a single MP4, uploads the result to R2 at
`muxed/{channel_id}/{slug}.mp4`, and returns the public URL.

Response `200`:
```json
{
  "slug": "late-night-house",
  "vrchatPlaybackUrl": "https://stream.wavepalace.live/muxed/channel_late_night_house/late-night-house.mp4"
}
```

- `404` — channel slug not found.
- `500` — FFmpeg failure or R2 upload error (detail includes the error message).

### POST /api/mux/all

Runs the mux job for every published channel. Failures per channel are
recorded but do not abort the run.

Response `200`:
```json
{
  "results": {
    "late-night-house": "https://stream.wavepalace.live/muxed/channel_late_night_house/late-night-house.mp4",
    "afro-future-lounge": "https://stream.wavepalace.live/muxed/channel_afro_future_lounge/afro-future-lounge.mp4",
    "neon-afterhours": "ERROR: FFmpeg failed ..."
  }
}
```

## Error states

- Missing channel → `404`.
- Backend unreachable → the frontend shows a friendly recoverable message
  (directory and detail page both handle this).
- Media fails to load in the player → the player shows an inline error card.
