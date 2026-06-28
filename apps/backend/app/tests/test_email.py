"""Tests for the shared Resend email helper — response checking + logging.

The bug these guard against: a Resend rejection (unverified domain, sandbox
mode, bad key, any 4xx/5xx) must NOT fail silently — it must return False and
log the status + body so it's diagnosable.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
import respx

from app.services.email import send_email


def test_send_email_success(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test_key")
    with respx.mock:
        route = respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(200, json={"id": "abc"})
        )
        ok = asyncio.run(send_email("user@example.com", "Subject", "<p>hi</p>"))
    assert ok is True
    assert route.called


def test_send_email_non_2xx_returns_false_and_logs(monkeypatch, caplog):
    monkeypatch.setenv("RESEND_API_KEY", "test_key")
    with respx.mock:
        respx.post("https://api.resend.com/emails").mock(
            return_value=httpx.Response(403, text='{"message":"domain not verified"}')
        )
        with caplog.at_level(logging.ERROR, logger="wavepalace.email"):
            ok = asyncio.run(send_email("user@example.com", "Subject", "<p>hi</p>"))
    assert ok is False
    assert any("Resend send failed 403" in r.getMessage() for r in caplog.records)
    assert any("domain not verified" in r.getMessage() for r in caplog.records)


def test_send_email_no_key_returns_false(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    # No HTTP mock needed — it must short-circuit before any request.
    ok = asyncio.run(send_email("user@example.com", "Subject", "<p>hi</p>"))
    assert ok is False
