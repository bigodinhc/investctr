"""
Supabase Storage integration for file uploads.
"""

import httpx

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def upload_file_to_storage(
    bucket: str,
    path: str,
    content: bytes,
    content_type: str = "application/pdf",
) -> str:
    """
    Upload a file to Supabase Storage.

    Args:
        bucket: Storage bucket name
        path: File path within the bucket
        content: File content as bytes
        content_type: MIME type of the file

    Returns:
        The storage path of the uploaded file

    Raises:
        Exception: If upload fails
    """
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ValueError("Supabase credentials not configured")

    url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{path}"

    headers = {
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": content_type,
        "x-upsert": "true",  # Overwrite if exists
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            content=content,
            headers=headers,
            timeout=60.0,
        )

        if response.status_code not in (200, 201):
            logger.error(
                "storage_upload_failed",
                bucket=bucket,
                path=path,
                status_code=response.status_code,
                response=response.text,
            )
            raise Exception(f"Storage upload failed: {response.text}")

        logger.info(
            "storage_upload_success",
            bucket=bucket,
            path=path,
            size=len(content),
        )

        return path


async def delete_file_from_storage(bucket: str, path: str) -> None:
    """
    Delete a file from Supabase Storage.

    Args:
        bucket: Storage bucket name
        path: File path within the bucket
    """
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ValueError("Supabase credentials not configured")

    url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{path}"

    headers = {
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            url,
            headers=headers,
            timeout=30.0,
        )

        if response.status_code not in (200, 204):
            logger.warning(
                "storage_delete_failed",
                bucket=bucket,
                path=path,
                status_code=response.status_code,
            )
        else:
            logger.info(
                "storage_delete_success",
                bucket=bucket,
                path=path,
            )


async def get_file_from_storage(bucket: str, path: str) -> bytes:
    """
    Download a file from Supabase Storage.

    Args:
        bucket: Storage bucket name
        path: File path within the bucket

    Returns:
        File content as bytes

    Raises:
        Exception: If download fails
    """
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ValueError("Supabase credentials not configured")

    url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{path}"

    headers = {
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            timeout=60.0,
        )

        if response.status_code != 200:
            logger.error(
                "storage_download_failed",
                bucket=bucket,
                path=path,
                status_code=response.status_code,
            )
            raise Exception(f"Storage download failed: {response.text}")

        return response.content
