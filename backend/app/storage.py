"""S3-compatible object storage client (MinIO locally, S3 in prod)."""
from __future__ import annotations
import os

import boto3
from botocore.client import Config

S3_BUCKET = os.environ["S3_BUCKET"]
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL")  # set for MinIO, unset for real AWS S3
# Endpoint used only when *generating* presigned URLs — these are handed to the
# browser, which cannot resolve a Docker-internal hostname like `minio`. Falls
# back to S3_ENDPOINT_URL (e.g. real S3, which is publicly resolvable already).
S3_PUBLIC_ENDPOINT_URL = os.environ.get("S3_PUBLIC_ENDPOINT_URL", S3_ENDPOINT_URL)
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY_ID")
S3_SECRET_KEY = os.environ.get("S3_SECRET_ACCESS_KEY")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")

# MinIO (and most other S3-compatible endpoints) need path-style addressing —
# virtual-hosted-style bucket subdomains don't resolve for a custom endpoint.
# Real AWS S3 (no endpoint override) keeps boto3's default addressing.
_addressing_style = "path" if S3_ENDPOINT_URL else "auto"

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION,
    config=Config(signature_version="s3v4", s3={"addressing_style": _addressing_style}),
)

# Separate client used only for presigning — same credentials, browser-reachable endpoint.
s3_public = boto3.client(
    "s3",
    endpoint_url=S3_PUBLIC_ENDPOINT_URL,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION,
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "path" if S3_PUBLIC_ENDPOINT_URL else "auto"},
    ),
)


def ensure_bucket() -> None:
    try:
        s3.head_bucket(Bucket=S3_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=S3_BUCKET)


def put_object(key: str, body: bytes, content_type: str) -> None:
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body, ContentType=content_type)


def get_object(key: str) -> bytes:
    obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    return obj["Body"].read()


def presigned_get_url(key: str, expires_seconds: int = 3600) -> str:
    return s3_public.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires_seconds,
    )
