"""Email templates for Slice 13 notification delivery.

Each function returns (subject, html, text) for use with Resend.
"""

from __future__ import annotations


def new_tracks_email(
    channel_name: str,
    tracks: list[dict],
    channel_url: str,
    vrchat_url: str | None,
    unsubscribe_url: str,
) -> tuple[str, str, str]:
    subject = f"New tracks added to {channel_name} on WavePalace"

    track_lines_html = "".join(
        f"<li><strong>{t.get('title', 'Untitled')}</strong>"
        f"{' — ' + t['artist'] if t.get('artist') else ''}</li>"
        for t in tracks
    )
    track_lines_text = "\n".join(
        f"  • {t.get('title', 'Untitled')}{' — ' + t['artist'] if t.get('artist') else ''}"
        for t in tracks
    )
    vrchat_block_html = (
        f'<p><a href="{vrchat_url}">Open in VRChat</a></p>' if vrchat_url else ""
    )
    vrchat_block_text = f"\nVRChat: {vrchat_url}" if vrchat_url else ""

    html = f"""
<div style="font-family:sans-serif;max-width:600px;margin:auto;color:#eee;background:#111;padding:32px;border-radius:12px;">
  <h2 style="color:#a78bfa;">New tracks on {channel_name}</h2>
  <ul>{track_lines_html}</ul>
  <p><a href="{channel_url}" style="color:#a78bfa;">Listen now on WavePalace</a></p>
  {vrchat_block_html}
  <hr style="border-color:#333;margin-top:32px;"/>
  <p style="font-size:12px;color:#666;">
    <a href="{unsubscribe_url}" style="color:#666;">Unsubscribe</a>
  </p>
</div>
"""

    text = f"""New tracks added to {channel_name}:

{track_lines_text}

Listen: {channel_url}{vrchat_block_text}

Unsubscribe: {unsubscribe_url}
"""
    return subject, html.strip(), text.strip()


def channel_live_email(
    channel_name: str,
    channel_url: str,
    vrchat_url: str | None,
    unsubscribe_url: str,
) -> tuple[str, str, str]:
    subject = f"{channel_name} is live on WavePalace"

    vrchat_block_html = (
        f'<p><a href="{vrchat_url}">Open in VRChat</a></p>' if vrchat_url else ""
    )
    vrchat_block_text = f"\nVRChat: {vrchat_url}" if vrchat_url else ""

    html = f"""
<div style="font-family:sans-serif;max-width:600px;margin:auto;color:#eee;background:#111;padding:32px;border-radius:12px;">
  <h2 style="color:#a78bfa;">{channel_name} is live!</h2>
  <p><a href="{channel_url}" style="color:#a78bfa;">Tune in now</a></p>
  {vrchat_block_html}
  <hr style="border-color:#333;margin-top:32px;"/>
  <p style="font-size:12px;color:#666;">
    <a href="{unsubscribe_url}" style="color:#666;">Unsubscribe</a>
  </p>
</div>
"""

    text = f"""{channel_name} is live on WavePalace!

Tune in: {channel_url}{vrchat_block_text}

Unsubscribe: {unsubscribe_url}
"""
    return subject, html.strip(), text.strip()


def weekly_digest_email(
    recent_channels: list[str],
    followed_channels: list[dict],
    unsubscribe_url: str,
) -> tuple[str, str, str]:
    subject = "Your WavePalace weekly digest"

    recent_html = ""
    recent_text = ""
    if recent_channels:
        items = "".join(f"<li>{c}</li>" for c in recent_channels)
        recent_html = f"<h3>This week you listened to</h3><ul>{items}</ul>"
        recent_text = "This week you listened to:\n" + "\n".join(f"  • {c}" for c in recent_channels)

    channels_html = ""
    channels_text = ""
    if followed_channels:
        items = "".join(
            f"<li><a href=\"{c.get('url', '#')}\" style=\"color:#a78bfa;\">{c.get('name', 'Channel')}</a></li>"
            for c in followed_channels
        )
        channels_html = f"<h3>Channels you follow</h3><ul>{items}</ul>"
        channels_text = "Channels you follow:\n" + "\n".join(
            f"  • {c.get('name', 'Channel')} — {c.get('url', '')}" for c in followed_channels
        )

    html = f"""
<div style="font-family:sans-serif;max-width:600px;margin:auto;color:#eee;background:#111;padding:32px;border-radius:12px;">
  <h2 style="color:#a78bfa;">Your WavePalace weekly digest</h2>
  {recent_html}
  {channels_html}
  <hr style="border-color:#333;margin-top:32px;"/>
  <p style="font-size:12px;color:#666;">
    <a href="{unsubscribe_url}" style="color:#666;">Unsubscribe</a>
  </p>
</div>
"""

    text = f"""Your WavePalace weekly digest

{recent_text}

{channels_text}

Unsubscribe: {unsubscribe_url}
"""
    return subject, html.strip(), text.strip()
