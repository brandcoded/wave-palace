"""Delete all channels and re-seed exactly once. Run once to fix duplicates."""
from __future__ import annotations
import sys
import requests

API = "https://api.wavepalace.live"
SECRET = "garden-taste-glance"

KEEP = [
    {
        "title": "Late Night House",
        "description": "Deep house and midnight lounge energy for VRChat worlds.",
        "genre": "House", "mood": "Late Night", "energy": "Medium", "theme": "Lounge",
        "hostName": "DJ Skyy",
        "coverImageUrl": "https://stream.wavepalace.live/channels/channel_abc123/purple-sky.jpg",
        "visualLoopUrl": "https://stream.wavepalace.live/channels/channel_abc123/animated-115136.mp4",
        "audioUrl": "https://stream.wavepalace.live/tracks/channel_abc123/come-thru.mp3",
        "playlist": [
            {"url": "https://stream.wavepalace.live/tracks/channel_abc123/come-thru.mp3", "title": "Come Thru", "artist": "DJ Skyy"},
            {"url": "https://stream.wavepalace.live/tracks/channel_abc123/Day-Trips-4-82bpm.mp3", "title": "Day Trips", "artist": "DJ Skyy"},
            {"url": "https://stream.wavepalace.live/tracks/channel_abc123/happier-106bpm-mix-3-M1.mp3", "title": "Happier", "artist": "DJ Skyy"},
            {"url": "https://stream.wavepalace.live/tracks/channel_abc123/projections-Stems-Mix-3.mp3", "title": "Projections", "artist": "DJ Skyy"},
        ],
        "rightsStatus": "owned_or_cleared", "isPublished": True,
    },
    {
        "title": "Afro Future Lounge",
        "description": "Warm Afro house textures and futuristic lounge atmospheres.",
        "genre": "Afro House", "mood": "Warm", "energy": "Medium", "theme": "Futuristic Lounge",
        "hostName": "WavePalace Selects",
        "coverImageUrl": "https://stream.wavepalace.live/channels/channel_def456/view_apartment.jpg",
        "visualLoopUrl": "https://stream.wavepalace.live/channels/channel_def456/cloud-45959.mp4",
        "audioUrl": "https://stream.wavepalace.live/tracks/channel_def456/cant-explain-no-words-160bpm-1.mp3",
        "playlist": [
            {"url": "https://stream.wavepalace.live/tracks/channel_def456/cant-explain-no-words-160bpm-1.mp3", "title": "Can't Explain", "artist": "WavePalace Selects"},
        ],
        "rightsStatus": "owned_or_cleared", "isPublished": True,
    },
    {
        "title": "Neon Afterhours",
        "description": "Dark, high-energy electronic visuals for late VR parties.",
        "genre": "Electronic", "mood": "Dark", "energy": "High", "theme": "VR Party",
        "hostName": "Guest Host",
        "coverImageUrl": "https://stream.wavepalace.live/channels/channel_ghi789/moon_waves.jpeg",
        "visualLoopUrl": "https://stream.wavepalace.live/channels/channel_ghi789/cube-27033.mp4",
        "audioUrl": "https://stream.wavepalace.live/tracks/channel_ghi789/akira.mp3",
        "playlist": [
            {"url": "https://stream.wavepalace.live/tracks/channel_ghi789/akira.mp3", "title": "Akira", "artist": "Guest Host"},
        ],
        "rightsStatus": "owned_or_cleared", "isPublished": True,
    },
]

session = requests.Session()

print("Logging in...")
r = session.post(f"{API}/api/admin/login", json={"secret": SECRET})
if not r.ok:
    print(f"Login failed: {r.status_code}"); sys.exit(1)
print("  OK\n")

print("Fetching all channels...")
r = session.get(f"{API}/api/admin/channels")
channels = r.json()
print(f"  Found {len(channels)} channels\n")

print("Deleting all channels...")
for ch in channels:
    slug = ch.get("slug", "?")
    r = session.delete(f"{API}/api/admin/channels/{slug}")
    print(f"  {'✓' if r.ok else '✗'} Deleted {slug} ({r.status_code})")

print("\nRe-seeding 3 channels...")
for ch in KEEP:
    r = session.post(f"{API}/api/admin/channels", json=ch)
    slug = r.json().get("slug", "?") if r.ok else "?"
    print(f"  {'✓' if r.status_code == 201 else '✗'} {ch['title']} → {slug} ({r.status_code})")

print("\nDone.")
