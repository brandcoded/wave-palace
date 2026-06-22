"""Authentication service — user identity, sessions, magic links, passwords (Slice 10)."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException

from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    BOOTSTRAP_ADMIN_ID,
    EmailLoginTokenDocument,
    SessionDocument,
    UserDocument,
)

logger = logging.getLogger("wavepalace.auth_service")

_EMAIL_TOKEN_TTL_MINUTES = 15
_SESSION_TTL_DAYS = 30


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    import bcrypt
    return bcrypt.checkpw(plain.encode(), hashed.encode())


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        settings=None,
    ) -> None:
        self._users = user_repo
        self._sessions = session_repo
        self._settings = settings

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    async def get_or_create_bootstrap_admin(self) -> UserDocument:
        user = await self._users.get(BOOTSTRAP_ADMIN_ID)
        if user:
            return user
        now = datetime.now(timezone.utc)
        user = UserDocument(
            id=BOOTSTRAP_ADMIN_ID,
            email="admin@wavepalace.local",
            display_name="Admin",
            roles=["admin"],
            created_at=now,
            is_active=True,
        )
        return await self._users.upsert(user)

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def issue_session(self, user: UserDocument) -> str:
        """Create a new session and return the opaque session ID."""
        now = datetime.now(timezone.utc)
        session = SessionDocument(
            id=str(uuid.uuid4()),
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(days=_SESSION_TTL_DAYS),
        )
        await self._sessions.create(session)
        await self._users.update(
            user.id, {"last_login_at": now.isoformat()}
        )
        return session.id

    async def get_user_by_session(self, session_id: str) -> Optional[UserDocument]:
        session = await self._sessions.get(session_id)
        if not session:
            return None
        if session.revoked:
            return None
        if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return None
        return await self._users.get(session.user_id)

    async def revoke_session(self, session_id: str) -> None:
        await self._sessions.revoke(session_id)

    # ------------------------------------------------------------------
    # Discord OAuth
    # ------------------------------------------------------------------

    async def find_or_create_by_discord(
        self,
        discord_user_id: str,
        discord_username: str,
        avatar_url: Optional[str] = None,
    ) -> UserDocument:
        user = await self._users.get_by_discord_id(discord_user_id)
        if user:
            await self._users.update(user.id, {"last_login_at": datetime.now(timezone.utc).isoformat()})
            return user
        now = datetime.now(timezone.utc)
        user = UserDocument(
            id=str(uuid.uuid4()),
            display_name=discord_username,
            discord_user_id=discord_user_id,
            avatar_url=avatar_url,
            roles=[],
            created_at=now,
        )
        return await self._users.create(user)

    # ------------------------------------------------------------------
    # Email magic link
    # ------------------------------------------------------------------

    async def find_or_create_by_email(self, email: str) -> UserDocument:
        user = await self._users.get_by_email(email)
        if user:
            return user
        now = datetime.now(timezone.utc)
        user = UserDocument(
            id=str(uuid.uuid4()),
            email=email,
            email_verified=False,
            display_name=email.split("@")[0],
            roles=[],
            created_at=now,
        )
        return await self._users.create(user)

    async def issue_email_token(self, email: str, verify_url_base: str) -> None:
        """Create a magic-link token and send the email. Always succeeds silently."""
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        now = datetime.now(timezone.utc)
        doc = EmailLoginTokenDocument(
            id=str(uuid.uuid4()),
            token_hash=token_hash,
            email=email,
            expires_at=now + timedelta(minutes=_EMAIL_TOKEN_TTL_MINUTES),
        )
        await self._sessions.create_email_token(doc)
        verify_url = f"{verify_url_base.rstrip('/')}/api/auth/email/verify?token={token}"
        await asyncio.ensure_future(
            self._send_magic_link_email(email, verify_url)
        )

    async def verify_email_token(self, token: str) -> UserDocument:
        token_hash = _hash_token(token)
        doc = await self._sessions.get_email_token_by_hash(token_hash)
        if not doc:
            raise HTTPException(status_code=400, detail="Invalid or expired login link")
        if doc.consumed:
            raise HTTPException(status_code=400, detail="Login link already used")
        now = datetime.now(timezone.utc)
        expires = doc.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            raise HTTPException(status_code=400, detail="Login link has expired")
        await self._sessions.consume_email_token(doc.id)
        user = await self.find_or_create_by_email(doc.email)
        await self._users.update(user.id, {"email_verified": True})
        return await self._users.get(user.id) or user

    async def _send_magic_link_email(self, email: str, verify_url: str) -> None:
        api_key = (self._settings and getattr(self._settings, "resend_api_key", None)) or os.getenv("RESEND_API_KEY")
        if not api_key:
            logger.warning("RESEND_API_KEY not set — magic link for %s: %s", email, verify_url)
            return
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": "noreply@wavepalace.live",
                        "to": [email],
                        "subject": "Sign in to WavePalace",
                        "html": (
                            f"<p>Click the link below to sign in to WavePalace. "
                            f"This link expires in {_EMAIL_TOKEN_TTL_MINUTES} minutes.</p>"
                            f"<p><a href='{verify_url}'>Sign in to WavePalace</a></p>"
                            f"<p>If you didn't request this, you can ignore this email.</p>"
                        ),
                    },
                )
        except Exception:
            logger.exception("Failed to send magic link email to %s", email)

    # ------------------------------------------------------------------
    # Password auth
    # ------------------------------------------------------------------

    async def register(
        self, email: str, password: str, display_name: str
    ) -> UserDocument:
        existing = await self._users.get_by_email(email)
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        now = datetime.now(timezone.utc)
        user = UserDocument(
            id=str(uuid.uuid4()),
            email=email,
            display_name=display_name,
            password_hash=_hash_password(password),
            roles=[],
            created_at=now,
        )
        return await self._users.create(user)

    async def password_login(self, email: str, password: str) -> UserDocument:
        user = await self._users.get_by_email(email)
        if not user or not user.password_hash:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not _verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated")
        return user
