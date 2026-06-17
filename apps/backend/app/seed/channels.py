"""Seed channel data used in local seed mode and as a database fallback.

All media URLs are safe, freely-usable placeholder samples. Swap these for
owned/licensed/cleared media in production via this file or the database.
"""

# Public-domain / freely usable sample media (W3C + W3Schools samples +
# Picsum placeholder images). These contain no copyrighted music.
_BG_1 = "https://stream.wavepalace.live/channels/channel_abc123/purple-sky.jpg"
_BG_2 = "https://stream.wavepalace.live/channels/channel_def456/view_apartment.jpg"
_BG_3 = "https://stream.wavepalace.live/channels/channel_ghi789/moon_waves.jpeg"

_AUDIO_1 = "https://stream.wavepalace.live/tracks/channel_abc123/come-thru.mp3"
_AUDIO_2 = "https://stream.wavepalace.live/tracks/channel_def456/cant-explain-no-words-160bpm-1.mp3"
_AUDIO_3 = "https://stream.wavepalace.live/tracks/channel_ghi789/akira.mp3"

# Pre-muxed MP4s not yet uploaded — falling back to audio MP3s until muxed files are on R2.
_VRCHAT_1 = _AUDIO_1
_VRCHAT_2 = _AUDIO_2
_VRCHAT_3 = _AUDIO_3


SEED_CHANNELS: list[dict] = [
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
        "coverImageUrl": _BG_1,
        "audioUrl": _AUDIO_1,
        "vrchatPlaybackUrl": _VRCHAT_1,
        "externalLinks": [
            {"label": "Listen elsewhere", "url": "https://example.com/late-night-house"}
        ],
        "rightsStatus": "owned_or_cleared",
        "isPublished": True,
    },
    {
        "id": "channel_afro_future_lounge",
        "slug": "afro-future-lounge",
        "title": "Afro Future Lounge",
        "description": "Warm Afro house textures and futuristic lounge atmospheres.",
        "genre": "Afro House",
        "mood": "Warm",
        "energy": "Medium",
        "theme": "Futuristic Lounge",
        "hostName": "WavePalace Selects",
        "coverImageUrl": _BG_2,
        "audioUrl": _AUDIO_2,
        "vrchatPlaybackUrl": _VRCHAT_2,
        "externalLinks": [
            {"label": "Listen elsewhere", "url": "https://example.com/afro-future-lounge"}
        ],
        "rightsStatus": "owned_or_cleared",
        "isPublished": True,
    },
    {
        "id": "channel_neon_afterhours",
        "slug": "neon-afterhours",
        "title": "Neon Afterhours",
        "description": "Dark, high-energy electronic visuals for late VR parties.",
        "genre": "Electronic",
        "mood": "Dark",
        "energy": "High",
        "theme": "VR Party",
        "hostName": "Guest Host",
        "coverImageUrl": _BG_3,
        "audioUrl": _AUDIO_3,
        "vrchatPlaybackUrl": _VRCHAT_3,
        "externalLinks": [
            {"label": "Listen elsewhere", "url": "https://example.com/neon-afterhours"}
        ],
        "rightsStatus": "owned_or_cleared",
        "isPublished": True,
    },
    {
        # Intentionally unpublished — must never appear in the public API.
        "id": "channel_hidden_draft",
        "slug": "hidden-draft",
        "title": "Hidden Draft (Unpublished)",
        "description": "An in-progress channel that should not be publicly visible.",
        "genre": "House",
        "mood": "Late Night",
        "energy": "Low",
        "theme": "Lounge",
        "hostName": "WavePalace Selects",
        "coverImageUrl": "https://picsum.photos/seed/hiddendraft/1200/800",
        "audioUrl": _AUDIO_1,
        "vrchatPlaybackUrl": _VRCHAT_1,
        "externalLinks": [],
        "rightsStatus": "pending_review",
        "isPublished": False,
    },
]
