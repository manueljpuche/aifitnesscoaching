from __future__ import annotations

import boto3
from botocore.config import Config as BotoConfig

from app.core.config import settings

_endpoint = (
    f"{'https' if settings.minio_secure else 'http'}://{settings.minio_endpoint}"
)

s3_client = boto3.client(
    "s3",
    endpoint_url=_endpoint,
    aws_access_key_id=settings.minio_access_key,
    aws_secret_access_key=settings.minio_secret_key,
    config=BotoConfig(signature_version="s3v4"),
    region_name="us-east-1",
)

BUCKETS = [
    settings.minio_bucket_progress_photos,
    settings.minio_bucket_pantry_scans,
    settings.minio_bucket_voice_notes,
    settings.minio_bucket_exports,
    settings.minio_bucket_barcode_scans,
]


def ensure_buckets() -> None:
    existing = {b["Name"] for b in (s3_client.list_buckets().get("Buckets") or [])}
    for bucket in BUCKETS:
        if bucket not in existing:
            try:
                s3_client.create_bucket(Bucket=bucket)
            except s3_client.exceptions.BucketAlreadyOwnedByYou:
                pass


def generate_presigned_url(bucket: str, key: str, expires_in: int = 900) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def upload_file(
    bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream"
) -> None:
    s3_client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
