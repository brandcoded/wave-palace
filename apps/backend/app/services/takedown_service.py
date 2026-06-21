"""Service layer for DMCA takedown requests."""

from __future__ import annotations

import asyncio
import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText

from app.repositories.takedown_repository import TakedownRepository
from app.schemas.takedown import (
    TakedownDocument,
    TakedownStatusUpdate,
    TakedownSubmitRequest,
    TakedownSubmitResponse,
)

logger = logging.getLogger("wavepalace.takedowns")


def _build_email_body(doc: TakedownDocument) -> str:
    lines = [
        "New DMCA / Copyright Takedown Request",
        "=" * 40,
        f"Submitted:        {doc.submitted_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"Claimant:         {doc.claimant_name}",
        f"Organization:     {doc.organization or '—'}",
        f"Email:            {doc.email}",
        f"Role:             {doc.role}",
        "",
        f"Infringing URL:   {doc.infringing_url}",
        "",
        "Description of work:",
        doc.description,
        "",
        "Proof of ownership:",
        doc.proof or "—",
        "",
        f"Good-faith statement: {'Yes' if doc.good_faith else 'No'}",
        f"Accuracy statement:   {'Yes' if doc.accuracy else 'No'}",
        "",
        f"Review at: /admin/takedowns",
    ]
    return "\n".join(lines)


def _send_email_sync(
    admin_email: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    subject: str,
    body: str,
) -> None:
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = admin_email
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [admin_email], msg.as_string())


class TakedownService:
    def __init__(self, repository: TakedownRepository, settings=None) -> None:
        self._repo = repository
        self._settings = settings

    async def submit(self, req: TakedownSubmitRequest) -> TakedownSubmitResponse:
        doc = TakedownDocument(
            id=str(uuid.uuid4()),
            submitted_at=datetime.now(tz=timezone.utc),
            **req.model_dump(),
        )
        await self._repo.create(doc)

        # Best-effort admin email — never blocks the response.
        asyncio.ensure_future(self._notify(doc))

        return TakedownSubmitResponse(id=doc.id, submitted_at=doc.submitted_at)

    async def list_all(self) -> list[TakedownDocument]:
        return await self._repo.list_all()

    async def get(self, takedown_id: str) -> TakedownDocument | None:
        return await self._repo.get(takedown_id)

    async def update_status(
        self, takedown_id: str, update: TakedownStatusUpdate
    ) -> TakedownDocument | None:
        return await self._repo.update_status(
            takedown_id, update.status, update.notes
        )

    async def _notify(self, doc: TakedownDocument) -> None:
        s = self._settings
        if not s:
            return
        admin_email = getattr(s, "admin_email", None)
        smtp_host = getattr(s, "smtp_host", None)
        smtp_user = getattr(s, "smtp_user", None)
        smtp_pass = getattr(s, "smtp_pass", None)

        if not (admin_email and smtp_host and smtp_user and smtp_pass):
            logger.debug("SMTP not configured — skipping takedown notification email.")
            return

        smtp_port = getattr(s, "smtp_port", 587)
        subject = f"[WavePalace] New Takedown Request — {doc.claimant_name}"
        body = _build_email_body(doc)
        try:
            await asyncio.to_thread(
                _send_email_sync,
                admin_email,
                smtp_host,
                smtp_port,
                smtp_user,
                smtp_pass,
                subject,
                body,
            )
            logger.info("Takedown notification sent to %s", admin_email)
        except Exception:
            logger.exception("Failed to send takedown notification email.")
