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
  "audioUrl": "https://stream.wavepalace.live/tracks/channel_abc123/track.mp3",
  "vrchatPlaybackUrl": "https://stream.wavepalace.live/muxed/late-night-house.mp4",
  "externalLinks": [{ "label": "Listen elsewhere", "url": "https://example.com" }],
  "rightsStatus": "owned_or_cleared",
  "isPublished": true
}
```

**Field notes:**
- `audioUrl` — the audio stream used by the web player (MP3 on Cloudflare R2)
- `coverImageUrl` — static channel art displayed as the web player background
- `vrchatPlaybackUrl` — pre-muxed static MP4 (cover image + audio combined), uploaded to R2, single direct URL for VRChat video players
- `visualLoopUrl` and `webPlaybackUrl` removed in MVP — replaced by `audioUrl` + `coverImageUrl`
- `externalLinks` are attribution only and are never playback sources

## Error states

- Missing channel → `404`.
- Backend unreachable → the frontend shows a friendly recoverable message
  (directory and detail page both handle this).
- Media fails to load in the player → the player shows an inline error card.
