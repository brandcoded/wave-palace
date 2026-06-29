# WavePalace Channel Renderer

Remotion-based video renderer that composites channel art, host info, now-playing data,
a frame-accurate audio visualizer, and follow-code CTA into a 1920×1080 MP4 for
VRChat video players.

## Quick start

```bash
cd apps/renderer
npm install

# Drop your media into public/:
#   audio.mp3          — audio track (drives waveform visualization)
#   channel-image.jpg  — cover art fallback
#   channel-loop.mp4   — looping background video (optional)

# Edit config/example.json with real channel data, then:
npm run render                        # renders with config/example.json
node scripts/render.mjs --config config/my-channel.json
```

## Studio (live preview)

```bash
npm start   # opens Remotion Studio at http://localhost:3000
```

## Config schema

| Field | Type | Description |
|---|---|---|
| `channelName` | string | e.g. "Late Night Lofi" |
| `hostName` | string | e.g. "Ty Skyy The DJ" |
| `songTitle` | string | Current track title |
| `artistName` | string | Current artist |
| `followCode` | string | Short follow code, e.g. "WVP6F2" |
| `siteUrl` | string | e.g. "wavepalace.live" |
| `socialHandle` | string | e.g. "@wavepalace" |
| `tags` | string[] | Mood tags shown in bottom bar |
| `loopMediaPath?` | string | Filename inside `public/` for loop video |
| `fallbackImagePath?` | string | Filename inside `public/` for cover image |
| `audioPath?` | string | Filename inside `public/` for audio (drives waveform) |
| `outputPath?` | string | Output path relative to renderer root |

## Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  LEFT PANEL (806px)          │  RIGHT PANEL (1114px)             │
│  gradient border             │  background #07050e               │
│  ┌──────────────────────┐    │  WavePalace logo           top-r │
│  │  video loop / image  │    │  NOW PLAYING badge               │
│  │  (cover, scrim)      │    │  Song title (large)              │
│  │                      │    │  Artist name (purple)            │
│  │  CHANNEL             │    │  ─── waveform (full-width) ───   │
│  │  Late Night Lofi     │    │  24/7 | Curated | Listen | ♡    │
│  │  Hosted by           │    │  ┌────────────┬──────────────┐   │
│  │  TY SKYY THE DJ      │    │  │ WVP6F2     │ wavepalace…  │   │
│  │  [tagline pill]      │    │  └────────────┴──────────────┘   │
│  └──────────────────────┘    │  IG TT FB YT @wavepalace  tags  │
└──────────────────────────────────────────────────────────────────┘
```

## Environment

- `FFMPEG_PATH` — path to ffmpeg binary (default: `ffmpeg`). On macOS with Homebrew: `/opt/homebrew/bin/ffmpeg`.
