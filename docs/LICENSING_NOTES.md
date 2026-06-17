# Licensing & Rights Notes — WavePalace

**This MVP does not grant any music rights.** It is a publishing/playback shell.

- All media (audio + visuals) must be **owned, licensed, cleared, public-domain,
  or submitted with explicit permission** before being published on WavePalace.
- The seed channels use freely-usable placeholder sample video and placeholder
  images. They contain **no copyrighted music** and must be swapped for properly
  cleared media in production (edit `apps/backend/app/seed/channels.py` or the
  database).
- **Spotify, Apple Music, TIDAL, SoundCloud, YouTube, and Mixcloud links are
  external attribution links only** ("Listen elsewhere"). WavePalace never
  restreams or uses them as playback sources. The player uses `webPlaybackUrl`;
  the VRChat copy uses `vrchatPlaybackUrl`.
- **VRChat playback** depends on the media host, HTTPS, the player/world
  configuration, and VRChat's own settings. Compatibility is not guaranteed.

## Before public launch

Add a takedown / removal policy and a contact path for rights holders. Add a
rights attestation step to any submission flow (see Future Slice 1). Consider a
`rightsStatus` review workflow before a channel can be published.
