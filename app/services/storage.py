import json
import uuid
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.core.config import Settings


class StorageService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_root_user,
            aws_secret_access_key=settings.minio_root_password,
        )

    def upload_avatar(
        self,
        *,
        user_id: int,
        content: bytes,
        filename: str | None,
        content_type: str,
    ) -> str:
        self._ensure_bucket()
        key = self._build_avatar_key(user_id, filename)
        self._client.put_object(
            Bucket=self._settings.minio_bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        return self._build_public_url(key)

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._settings.minio_bucket)
        except ClientError as exc:
            error_code = _error_code(exc)
            if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            self._client.create_bucket(Bucket=self._settings.minio_bucket)
        self._ensure_public_avatar_policy()

    def _ensure_public_avatar_policy(self) -> None:
        bucket = self._settings.minio_bucket
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket}/avatars/*"],
                }
            ],
        }
        self._client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))

    @staticmethod
    def _build_avatar_key(user_id: int, filename: str | None) -> str:
        suffix = Path(filename or "").suffix.lower() or ".bin"
        return f"avatars/{user_id}/{uuid.uuid4().hex}{suffix}"

    def _build_public_url(self, key: str) -> str:
        endpoint = self._settings.minio_public_endpoint or self._settings.minio_endpoint
        return f"{endpoint.rstrip('/')}/{self._settings.minio_bucket}/{key}"


def _error_code(exc: ClientError) -> str:
    response: dict[str, Any] = exc.response
    error = response.get("Error", {})
    return str(error.get("Code", ""))
