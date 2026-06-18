"""R2 (Cloudflare S3-compatible) upload repository.

Wraps boto3 so the rest of the application never imports it directly.
Only used by the mux service — not needed for read-only channel serving.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import Settings

logger = logging.getLogger("wavepalace.r2")


class R2Repository:
    """Upload files to a Cloudflare R2 bucket."""

    def __init__(self, settings: Settings) -> None:
        if not settings.r2_configured:
            raise RuntimeError(
                "R2 credentials not configured. Set R2_ACCOUNT_ID, "
                "R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY."
            )
        import boto3  # imported lazily so R2 absence never breaks channel serving

        self._bucket = settings.r2_bucket_name
        self._public_base = settings.r2_public_base_url.rstrip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )

    def upload_file(self, local_path: Path, r2_key: str, content_type: str = "video/mp4") -> str:
        """Upload *local_path* to *r2_key* and return the public URL.

        A short Cache-Control is set so that when a channel is re-muxed the
        Cloudflare edge picks up the new file within minutes instead of serving
        a stale copy indefinitely (objects with no Cache-Control got a long
        default edge TTL, which served outdated single-track MP4s).
        """
        logger.info("Uploading %s → s3://%s/%s", local_path, self._bucket, r2_key)
        self._client.upload_file(
            Filename=str(local_path),
            Bucket=self._bucket,
            Key=r2_key,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": "public, max-age=300",
            },
        )
        public_url = f"{self._public_base}/{r2_key}"
        logger.info("Upload complete: %s", public_url)
        return public_url
