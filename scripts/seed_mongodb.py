"""
One-time seed script — creates the 3 production channels in MongoDB via the
live admin API. Run this once after setting MONGODB_URI on Render.

Usage:
    python scripts/seed_mongodb.py \
        --api https://api.wavepalace.live \
        --secret YOUR_ADMIN_SECRET
"""

from __future__ import annotations

import argparse
import json
import sys

import requests

CHANNELS = [
    {
        "title": "Late Night House",
        "description": "Deep house and midnight lounge energy for VRChat worlds.",
        "genre": "House",
        "mood": "Late Night",
        "energy": "Medium",
        "theme": "Lounge",
        "hostName": "DJ Skyy",
        "coverImageUrl": "https://stream.wavepalace.live/channels/channel_abc123/purple-sky.jpg",
        "visualLoopUrl": "https://stream.wavepalace.live/channels/channel_abc123/animated-115136.mp4",
        "audioUrl": "https://stream.wavepalace.live/tracks/channel_abc123/come-thru.mp3",
        "playlist": [
            {"url": "https://stream.wavepalace.live/tracks/channel_abc123/come-thru.mp3",               "title": "Come Thru",    "artist": "DJ Skyy"},
            {"url": "https://stream.wavepalace.live/tracks/channel_abc123/Day-Trips-4-82bpm.mp3",       "title": "Day Trips",    "artist": "DJ Skyy"},
            {"url": "https://stream.wavepalace.live/tracks/channel_abc123/happier-106bpm-mix-3-M1.mp3", "title": "Happier",      "artist": "DJ Skyy"},
            {"url": "https://stream.wavepalace.live/tracks/channel_abc123/projections-Stems-Mix-3.mp3", "title": "Projections",  "artist": "DJ Skyy"},
        ],
        "rightsStatus": "owned_or_cleared",
        "isPublished": True,
    },
    {
        "title": "Afro Future Lounge",
        "description": "Warm Afro house textures and futuristic lounge atmospheres.",
        "genre": "Afro House",
        "mood": "Warm",
        "energy": "Medium",
        "theme": "Futuristic Lounge",
        "hostName": "WavePalace Selects",
        "coverImageUrl": "https://stream.wavepalace.live/channels/channel_def456/view_apartment.jpg",
        "visualLoopUrl": "https://stream.wavepalace.live/channels/channel_def456/cloud-45959.mp4",
        "audioUrl": "https://stream.wavepalace.live/tracks/channel_def456/cant-explain-no-words-160bpm-1.mp3",
        "playlist": [
            {"url": "https://stream.wavepalace.live/tracks/channel_def456/cant-explain-no-words-160bpm-1.mp3", "title": "Can't Explain", "artist": "WavePalace Selects"},
        ],
        "rightsStatus": "owned_or_cleared",
        "isPublished": True,
    },
    {
        "title": "Neon Afterhours",
        "description": "Dark, high-energy electronic visuals for late VR parties.",
        "genre": "Electronic",
        "mood": "Dark",
        "energy": "High",
        "theme": "VR Party",
        "hostName": "Guest Host",
        "coverImageUrl": "https://stream.wavepalace.live/channels/channel_ghi789/moon_waves.jpeg",
        "visualLoopUrl": "https://stream.wavepalace.live/channels/channel_ghi789/cube-27033.mp4",
        "audioUrl": "https://stream.wavepalace.live/tracks/channel_ghi789/akira.mp3",
        "playlist": [
            {"url": "https://stream.wavepalace.live/tracks/channel_ghi789/akira.mp3", "title": "Akira", "artist": "Guest Host"},
        ],
        "rightsStatus": "owned_or_cleared",
        "isPublished": True,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed WavePalace channels into MongoDB")
    parser.add_argument("--api", default="https://api.wavepalace.live", help="Backend base URL")
    parser.add_argument("--secret", required=True, help="ADMIN_SECRET value from Render")
    args = parser.parse_args()

    base = args.api.rstrip("/")
    session = requests.Session()

    # --- Login ---
    print(f"Logging in to {base} ...")
    r = session.post(f"{base}/api/admin/login", json={"secret": args.secret})
    if r.status_code != 200:
        print(f"  Login failed: {r.status_code} {r.text}")
        sys.exit(1)
    print("  Login successful.\n")

    # --- Create channels ---
    created = 0
    for ch in CHANNELS:
        print(f"Creating: {ch['title']} ...")
        r = session.post(f"{base}/api/admin/channels", json=ch)
        if r.status_code == 201:
            slug = r.json().get("slug", "?")
            print(f"  ✓ Created — slug: {slug}")
            created += 1
        elif r.status_code == 409:
            print(f"  — Already exists, skipping.")
        else:
            print(f"  ✗ Failed: {r.status_code}")
            print(f"    {r.text[:200]}")

    print(f"\nDone — {created}/{len(CHANNELS)} channels created.")


if __name__ == "__main__":
    main()
