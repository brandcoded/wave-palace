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

    def upload_file(
        self, local_path: Path, r2_key: str, content_type: str = "video/mp4",
        cache_control: str = "public, max-age=300"
    ) -> str:
        """Upload *local_path* to *r2_key* and return the public URL.

        cache_control sets the Cache-Control header. Muxed MP4s use 60s TTL
        so Cloudflare edge picks up updates quickly; other files use 5-min TTL.
        """
        logger.info("Uploading %s → s3://%s/%s", local_path, self._bucket, r2_key)
        self._client.upload_file(
            Filename=str(local_path),
            Bucket=self._bucket,
            Key=r2_key,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": cache_control,
            },
        )
        public_url = f"{self._public_base}/{r2_key}"
        logger.info("Upload complete: %s", public_url)
        return public_url

    async def upload_multipart_stream(
        self, file_obj, r2_key: str, content_type: str,
        cache_control: str = "public, max-age=300"
    ) -> str:
        """Stream *file_obj* to *r2_key* using S3 multipart upload.

        Reads in 8 MB chunks (safely above the 5 MB S3 minimum part size).
        Always calls abort_multipart_upload if the upload does not complete
        successfully to prevent orphaned parts in R2.
        """
        CHUNK = 8 * 1024 * 1024  # 8 MB

        logger.info("Starting multipart upload → s3://%s/%s", self._bucket, r2_key)
        resp = self._client.create_multipart_upload(
            Bucket=self._bucket,
            Key=r2_key,
            ContentType=content_type,
            CacheControl=cache_control,
        )
        upload_id = resp["UploadId"]
        parts: list[dict] = []
        completed = False
        try:
            part_number = 1
            while chunk := await file_obj.read(CHUNK):
                part = self._client.upload_part(
                    Bucket=self._bucket,
                    Key=r2_key,
                    UploadId=upload_id,
                    PartNumber=part_number,
                    Body=chunk,
                )
                parts.append({"ETag": part["ETag"], "PartNumber": part_number})
                part_number += 1
            self._client.complete_multipart_upload(
                Bucket=self._bucket,
                Key=r2_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            completed = True
        finally:
            if not completed:
                self._client.abort_multipart_upload(
                    Bucket=self._bucket,
                    Key=r2_key,
                    UploadId=upload_id,
                )

        public_url = f"{self._public_base}/{r2_key}"
        logger.info("Multipart upload complete: %s", public_url)
        return public_url

    def upload_bytes(
        self, data: bytes, r2_key: str, content_type: str,
        cache_control: str = "public, max-age=300"
    ) -> str:
        """Upload in-memory bytes to *r2_key* and return the public URL.

        cache_control sets the Cache-Control header (default 5-min TTL).
        """
        logger.info("Uploading bytes → s3://%s/%s", self._bucket, r2_key)
        self._client.put_object(
            Bucket=self._bucket,
            Key=r2_key,
            Body=data,
            ContentType=content_type,
            CacheControl=cache_control,
        )
        public_url = f"{self._public_base}/{r2_key}"
        logger.info("Upload complete: %s", public_url)
        return public_url
