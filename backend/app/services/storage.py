from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from typing import BinaryIO
from datetime import timedelta
from io import BytesIO

from minio import Minio
import boto3
from botocore.response import StreamingBody

from app.settings import settings
from typing import Protocol


class StreamLike(Protocol):
    """
    Any object that has a .read(int) -> bytes method can be treated as a StreamLike.
    """

    def read(self, amt: int = -1) -> bytes: ...


# ============================
# 🔹 BASE INTERFACE
# ============================


class StorageProvider(ABC):
    @abstractmethod
    async def upload(self, file_bytes: bytes, filename: str) -> str:
        """Upload file and return object key"""
        raise NotImplementedError

    @abstractmethod
    async def download_bytes(self, key: str) -> bytes:
        """Download entire file into memory"""
        raise NotImplementedError

    @abstractmethod
    async def download_stream(self, key: str) -> BinaryIO:
        """Download file as stream (for large files)"""
        raise NotImplementedError

    @abstractmethod
    async def get_url(self, key: str) -> str:
        """Generate accessible URL (presigned or public)"""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete object"""
        raise NotImplementedError


# ============================
# 🔹 MINIO IMPLEMENTATION
# ============================


class MinIOStorage(StorageProvider):
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self.bucket = bucket

        # Ensure bucket exists
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    async def upload(self, file_bytes: bytes, filename: str) -> str:
        ext: str = filename.split(".")[-1]
        key: str = f"{uuid.uuid4()}.{ext}"

        data = BytesIO(file_bytes)

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=key,
            data=data,
            length=len(file_bytes),
            content_type="application/octet-stream",
        )

        return key

    async def download_stream(self, key: str) -> StreamLike:
        # Returns streaming HTTP response (must be closed by caller)
        return self.client.get_object(self.bucket, key)

    async def download_bytes(self, key: str) -> bytes:
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def get_url(self, key: str) -> str:
        return self.client.presigned_get_object(
            self.bucket,
            key,
            expires=timedelta(days=1),
        )

    async def delete(self, key: str) -> None:
        self.client.remove_object(self.bucket, key)


# ============================
# 🔹 S3 IMPLEMENTATION
# ============================


class S3Storage(StorageProvider):
    def __init__(
        self,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        self.bucket = bucket

        self.client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    async def upload(self, file_bytes: bytes, filename: str) -> str:
        ext: str = filename.split(".")[-1]
        key: str = f"{uuid.uuid4()}.{ext}"

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=file_bytes,
            ContentType="application/octet-stream",
        )

        return key

    async def download_stream(self, key: str) -> BinaryIO:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"]  # StreamingBody

    async def download_bytes(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        body: StreamingBody = response["Body"]
        return body.read()

    async def get_url(self, key: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=3600,
        )

    async def delete(self, key: str) -> None:
        self.client.delete_object(
            Bucket=self.bucket,
            Key=key,
        )


# ============================
# 🔹 FACTORY
# ============================


def get_storage() -> StorageProvider:
    print(f"Using storage provider: {settings.storage_provider}")

    if settings.storage_provider == "minio":
        return MinIOStorage(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
            secure=False,
        )

    elif settings.storage_provider == "s3":
        return S3Storage(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
        )

    else:
        raise ValueError(f"Unsupported storage provider: {settings.storage_provider}")
