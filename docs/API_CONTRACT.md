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
  "genre": ["House"],
  "mood": ["Late Night"],
  "energy": ["Medium"],
  "theme": ["Lounge"],
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
  "isPublished": true,
  "streamingActive": false,
  "vrchatFallbackUrl": null
}
```

**Field notes:**
- `playlist` — ordered list of track objects (`url`, `title`, `artist`); the web player cycles through these automatically, looping back to index 0 after the last track
- `audioUrl` — always equals `playlist[0].url`; retained for backwards compatibility
- `coverImageUrl` — static channel art displayed as the web player background
- `vrchatPlaybackUrl` — resolved URL served to VRChat players; the public API always returns the correct resolved URL based on current routing tier (see below); admin schema stores `liveStreamUrl`, `streamingActive`, `vrchatFallbackUrl` separately
- `externalLinks` are attribution only and are never playback sources

**VRChat URL routing (three-tier, resolved server-side before public API response):**

```
1. liveStreamUrl set    → return liveStreamUrl  (external passthrough — creator's infra)
2. streamingActive true → return live/{slug}.ts  (WavePalace stream — VPS must be live)
3. default              → return vrchatFallbackUrl  (mux MP4 on R2)
```

**Streaming fields (Pre-Slice 4 add-on):**

| Field | Type | Notes |
|---|---|---|
| `streamingActive` | `bool` | Default `false`. When `true`, signals VRChat should use `vrchatFallbackUrl` (the live stream) instead of the muxed MP4. Set per-channel via `PATCH /api/admin/channels/{slug}` or in bulk via `POST /api/admin/channels/streaming/bulk`. |
| `vrchatFallbackUrl` | `string \| null` | The HLS/RTMP/TS live stream URL for VRChat (e.g. `https://…/live.m3u8`). Set by the admin; not overwritten by the mux service. |

**Planned field (not yet implemented):**

| Field | Type | Notes |
|---|---|---|
| `liveStreamUrl` | `string \| null` | Slice 3 add-on (External Stream Passthrough) · settable via `PATCH /api/admin/channels/{slug}` · when set, routes VRChat players directly to an external VRCDN/OBS stream URL · NOT YET BUILT |

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

## POST /api/admin/channels/{slug}/validate-urls

Admin-auth required (`wp_admin_token` cookie). Checks all playlist audio URLs and
`visualLoopUrl` for the channel and returns compatibility results.

**Response** — array of `URLCheckResult`:

```json
[
  {
    "url": "https://stream.wavepalace.live/tracks/channel_abc/track-1.mp3",
    "ok": true,
    "warnings": [],
    "checked_at": "2026-06-19T20:00:00Z"
  },
  {
    "url": "https://stream.wavepalace.live/channels/abc/loop.mp4",
    "ok": true,
    "warnings": [],
    "checked_at": "2026-06-19T20:00:00Z"
  }
]
```

`ok: false` → URL failed (not HTTPS, unreachable, HTTP 4xx/5xx).
`ok: true` with `warnings` → URL is reachable but has compatibility concerns
(e.g. `"Not MP4 — VRChat may reject this video"`).

Checks performed:
1. HTTPS scheme (no network call)
2. HEAD request (5 s timeout), falls back to GET on 405
3. Content-type sniff — flags `text/html`, non-MP4 video
4. R2 trusted host (`stream.wavepalace.live`) skips content-type check

---

## Sponsor endpoints (Slice 6)

### PATCH /api/admin/channels/{slug}/sponsor

Admin-auth required. Sets or clears the sponsor on a channel.

- Body: `Sponsor` object (see Channel schema below), or JSON `null` to clear.
- Response `200` — updated Channel object.
- `404` — channel not found.

**Sponsor object:**
```json
{
  "name": "Neon Drinks Co.",
  "logoUrl": "https://stream.wavepalace.live/sponsors/neon-logo.png",
  "text": "Brought to you by Neon Drinks",
  "clickUrl": "https://neondrinks.example.com",
  "placement": "lower_third",
  "startDate": "2026-07-01T00:00:00Z",
  "endDate": "2026-07-31T23:59:59Z",
  "isActive": true,
  "isFeatured": false,
  "impressionCount": 0,
  "clickCount": 0
}
```

`placement` values: `lower_third`, `bug`, `backdrop`.

### POST /api/channels/{slug}/sponsor/impression

Public. Records a sponsor impression. Rate-limited to once per IP per 30 minutes per channel.
No-ops when `sponsor` is null, `isActive` is false, or current time is outside `startDate`/`endDate` window.

- Response `200` — `{ "ok": true }`.

### POST /api/channels/{slug}/sponsor/click

Public. Increments `sponsor.clickCount`. No rate limit.
No-ops when `sponsor` is null, `isActive` is false, or outside date window.

- Response `200` — `{ "ok": true }`.

---

## Slice 9 — Code Capture + Follow Intent + Notification Stack

> **Not yet built.** These endpoints are planned for Slice 9. Document here for
> pre-implementation design review.

### POST /api/admin/codes

Admin-auth required (`wp_admin_token` cookie). Generates a 6-character
uppercase alphanumeric code for a channel or entity.

**Request:**
```json
{
  "channel_slug": "late-night-house",
  "entity_type": "channel",
  "entity_id": "abc123",
  "expires_at": null
}
```

`entity_type`: `"channel"` | `"artist"` | `"host"` | `"event"`
`expires_at`: ISO 8601 datetime or `null` (permanent)

**Response `201`:**
```json
{
  "code": "WAVE42",
  "channel_slug": "late-night-house",
  "entity_type": "channel",
  "entity_id": "abc123",
  "created_at": "2026-06-19T00:00:00Z",
  "expires_at": null,
  "active": true
}
```

**Errors:** `409` if collision (retry on server side before returning error).

---

### GET /api/codes/{code}

Public. Resolves a code to entity details for display on the `/follow/{code}`
page.

**Response `200`:**
```json
{
  "code": "WAVE42",
  "entity_type": "channel",
  "entity_id": "abc123",
  "display_name": "Late Night House",
  "host_name": "DJ Nova",
  "genre": "House",
  "mood": "Late Night",
  "cover_image_url": "https://stream.wavepalace.live/covers/late-night-house.jpg"
}
```

**Response `404`** — code not found, expired, or inactive:
```json
{ "detail": "This code is no longer active — tune in at wavepalace.live" }
```

---

### POST /api/codes/{code}/follow

Public. Submit a follow intent for the entity the code resolves to. Accepts
one notification channel per request.

**Discord follow:**
```json
{
  "channel": "discord",
  "discord_user_id": "123456789",
  "discord_username": "DJ Nova#1234",
  "vrchat_username": "VRCUSER_xyz"
}
```

**Email follow:**
```json
{
  "channel": "email",
  "email": "listener@example.com",
  "vrchat_username": "VRCUSER_xyz"
}
```

**Browser push follow:**
```json
{
  "channel": "browser_push",
  "push_subscription": { "endpoint": "...", "keys": { "p256dh": "...", "auth": "..." } },
  "vrchat_username": "VRCUSER_xyz"
}
```

`vrchat_username` is optional in all payloads — attribution/analytics only.

**Response `201`:**
```json
{ "follow_id": "...", "channel": "discord", "confirmed": true }
```

`confirmed`: `true` for Discord and browser_push; `false` for email until
double opt-in completes.

**Errors:** `404` (code inactive/expired), `409` (duplicate follow for same
identity + entity).

---

### GET /api/follows

Authenticated listener. Returns the caller's active follows. Auth resolved from
session cookie (Discord user ID or confirmed email).

**Response `200`:**
```json
[
  {
    "id": "...",
    "entity_type": "channel",
    "channel_slug": "late-night-house",
    "display_name": "Late Night House",
    "notification_channel": "discord",
    "confirmed": true,
    "created_at": "2026-06-19T00:00:00Z"
  }
]
```

---

### PATCH /api/follows/{id}

Authenticated listener. Update notification preferences for a follow.

**Request:**
```json
{ "notification_channel": "email" }
```

**Response `200`:** updated follow object (same shape as GET /api/follows item).

---

### DELETE /api/follows/{id}

Authenticated listener. Remove a follow (unfollow).

**Response `204`:** no body.

---

## Pre-Slice 4 add-on — Admin streaming controls

> **Not yet built.** Ships as a pre-Slice 4 add-on with no VPS dependency.
> Toggle infrastructure is built before the VPS is provisioned — activation
> requires only VPS provisioning + a database flag flip, no code deploy.

### PATCH /api/admin/channels/{slug}/streaming-mode

Admin-auth required. Sets streaming mode for a single channel.

**Request:**
```json
{ "streamingActive": true }
```

**Response `200`:**
```json
{
  "slug": "late-night-house",
  "streamingActive": true,
  "vrchatPlaybackUrl": "https://stream.wavepalace.live/live/late-night-house.ts",
  "vrchatFallbackUrl": "https://stream.wavepalace.live/muxed/channel_abc/late-night-house.mp4"
}
```

When `streamingActive: true` → VRChat players receive `live/{slug}.ts`.
When `streamingActive: false` → VRChat players receive `vrchatFallbackUrl` (mux MP4).

---

### POST /api/admin/channels/streaming-mode/bulk

Admin-auth required. Flips `streamingActive` on **all** channels at once.
Requires explicit confirmation to prevent accidental execution.

**Request:**
```json
{ "streamingActive": false, "confirm": true }
```

`confirm: true` is required — request without it returns `400`.

**Response `200`:**
```json
{
  "updated": 3,
  "streamingActive": false
}
```

Use case: emergency fallback when VPS goes down — one API call flips all channels to mux.

---

> **Existing endpoints updated at Slice 3:**
> - `POST /api/channels/{slug}/mux` — on completion, also writes `vrchatFallbackUrl` to the channel document
> - `POST /api/mux/all` — on completion, also writes `vrchatFallbackUrl` for all channels
