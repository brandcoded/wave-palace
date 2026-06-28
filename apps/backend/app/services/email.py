"""Shared Resend email sender.

All outbound app email goes through send_email() so a Resend rejection
(unverified sending domain, sandbox/test-mode restriction, invalid key, or any
4xx/5xx) is logged with status + body instead of failing silently. Previously
each caller hand-rolled the POST and several never checked the response, so a
rejected send produced no email and no log.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger("wavepalace.email")

_RESEND_URL = "https://api.resend.com/emails"


def _api_key() -> Optional[str]:
    settings = get_settings()
    return getattr(settings, "resend_api_key", None) or os.getenv("RESEND_API_KEY")


def _from_email() -> str:
    settings = get_settings()
    return (
        getattr(settings, "resend_from_email", None)
        or os.getenv("RESEND_FROM_EMAIL")
        or "noreply@wavepalace.live"
    )


async def send_email(
    to: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
) -> bool:
    """Send one email via Resend. Returns True on success, False otherwise.

    On any non-2xx response, logs the Resend status code and body so silent
    delivery failures (unverified domain, sandbox mode, bad key) are
    diagnosable. Never raises — callers can treat the bool as best-effort.
    """
    api_key = _api_key()
    if not api_key:
        logger.warning(
            "RESEND_API_KEY not set — skipping email to %s (subject=%r)", to, subject
        )
        return False

    payload: dict = {"from": _from_email(), "to": [to], "subject": subject, "html": html}
    if text is not None:
        payload["text"] = text

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _RESEND_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code >= 400:
            logger.error(
                "Resend send failed %d for %s (subject=%r): %s",
                resp.status_code,
                to,
                subject,
                resp.text,
            )
            return False
        return True
    except Exception:
        logger.exception("Failed to send email to %s (subject=%r)", to, subject)
        return False
