import aioboto3
from contextlib import asynccontextmanager
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logger import logger

@asynccontextmanager
async def get_s3_client():
    """Single entry point for creating the S3 client."""
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
    ) as client:
        yield client