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
    {
      "url": "https://stream.wavepalace.live/tracks/channel_abc123/track-1.mp3",
      "title": "Midnight Atrium",
      "artist": "DJ Skyy"
    },
    {
      "url": "https://stream.wavepalace.live/tracks/channel_abc123/track-2.mp3",
      "title": "Glass Elevator",
      "artist": "DJ Skyy"
    }
  ],
  "vrchatPlaybackUrl": "https://stream.wavepalace.live/muxed/late-night-house.mp4",
  "externalLinks": [{ "label": "Listen elsewhere", "url": "https://example.com" }],
  "rightsStatus": "owned_or_cleared",
  "isPublished": true
}
```

**Field notes:**
- `playlist` — ordered list of track objects (`url`, `title`, `artist`); the web player cycles through these automatically, looping back to index 0 after the last track
- `audioUrl` — always equals `playlist[0].url`; retained for backwards compatibility
- `coverImageUrl` — static channel art displayed as the web player background
- `vrchatPlaybackUrl` — pre-muxed static MP4 (cover image + audio combined), uploaded to R2, single direct URL for VRChat video players
- `externalLinks` are attribution only and are never playback sources

## Submission endpoints

Public endpoints for Slice 2 DJ / artist channel proposals. Submissions are
stored as pending review items; nothing is auto-published.

### GET /api/submission-options

Returns admin-managed option lists for the public submit form. Falls back to
seed values when MongoDB is unavailable or the collection is empty.

Response `200`:
```json
{
  "genre": ["House", "Afro House", "Electronic"],
  "mood": ["Late Night", "Warm", "Dark"],
  "energy": ["Low", "Medium", "High"],
  "theme": ["Lounge", "Futuristic Lounge", "VR Party"]
}
```

Response header: `Cache-Control: public, max-age=300`.

### POST /api/submissions/upload-image

Uploads an optional profile image or logo before the submission is posted.

- Body: `multipart/form-data`, field name `file`
- Accepted types: JPEG, PNG, WebP
- Max size: 5 MB
- Rate limit: 10 uploads per IP per hour

Response `200`:
```json
{
  "url": "https://stream.wavepalace.live/submissions/images/{uuid}.jpg"
}
```

- `400` — unsupported file type.
- `413` — file too large.
- `429` — rate limit exceeded.

### POST /api/submissions

Creates a pending channel proposal.

Request:
```json
{
  "submitter_name": "DJ Skyy",
  "contact_email": "skyy@example.com",
  "channel_title": "Afterhours Atrium",
  "profile_image_url": "https://stream.wavepalace.live/submissions/images/profile.jpg",
  "genre": ["House"],
  "mood": ["Late Night"],
  "energy": ["Medium"],
  "theme": ["Lounge"],
  "description": "A late-night channel proposal with cleared house music.",
  "sample_links": ["https://example.com/mix"],
  "rights_attestation": true,
  "notes": "Optional context for review."
}
```

Validation:
- `genre`, `mood`, `energy`, and `theme` require at least one value and every
  value must exist in `GET /api/submission-options`.
- `description` must be 20–500 characters.
- `sample_links` requires 1–5 URLs. These are attribution/review links only,
  never playback sources.
- `rights_attestation` must be `true`.

Response `201`:
```json
{
  "id": "78ec95c4-9e1d-4f57-95f9-e578c1d41035",
  "status": "pending",
  "submitted_at": "2026-06-19T18:00:00.000000",
  "message": "Thanks DJ Skyy — your submission is in review. We'll be in touch at skyy@example.com."
}
```

- `422` — invalid field, unknown option value, missing rights attestation, or
  malformed email/URL.
- `429` — rate limit exceeded.

## Mux endpoints (internal/admin — no auth for MVP)

These endpoints require R2 credentials to be set on the server
(`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`).
They are not exposed in the public frontend. Call them via the Render shell
or a direct API call when you need to produce muxed MP4s.

FFmpeg downloads the source files with a browser `User-Agent` (Cloudflare
blocks default Python/library agents), downscales the cover to a fixed
1280×720 canvas, and encodes a still-image H.264 video at 1 fps with AAC
audio and `+faststart`. The 720p downscale keeps memory/CPU bounded on
Render's free tier (a larger source cover previously OOM-killed the worker)
and is the most VRChat-compatible resolution.

### POST /api/channels/{slug}/mux

Muxes a single channel synchronously, uploads the result to R2 at
`muxed/{channel_id}/{slug}.mp4`, and returns the public URL. Suitable for
one-off re-muxing; a single channel completes in ~20s.

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

Starts a **background** job muxing every published channel and returns
immediately with `202 Accepted` — muxing the whole batch in one synchronous
request exceeds Render's HTTP timeout. Poll `GET /api/mux/status` for
progress.

Response `202`:
```json
{ "status": "accepted", "poll": "/api/mux/status" }
```

- `409` — a mux job is already running.

### GET /api/mux/status

Returns the state of the most recent `/api/mux/all` job (in-memory; reset on
each new run and on server restart).

Response `200`:
```json
{
  "running": false,
  "started_at": 1781761771.6,
  "finished_at": 1781761815.3,
  "channels": {
    "late-night-house": { "state": "done", "url": "https://stream.wavepalace.live/muxed/channel_late_night_house/late-night-house.mp4", "error": null },
    "afro-future-lounge": { "state": "done", "url": "https://stream.wavepalace.live/muxed/channel_afro_future_lounge/afro-future-lounge.mp4", "error": null },
    "neon-afterhours": { "state": "error", "url": null, "error": "FFmpeg timed out after 90s" }
  }
}
```

Per-channel `state` is one of `pending`, `running`, `done`, `error`.

## Error states

- Missing channel → `404`.
- Backend unreachable → the frontend shows a friendly recoverable message
  (directory and detail page both handle this).
- Media fails to load in the player → the player shows an inline error card.
