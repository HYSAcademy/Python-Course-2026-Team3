import aioboto3
from contextlib import asynccontextmanager
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logger import logger

@asynccontextmanager
async def get_s3_client():
    """Single entry point for creating the S3 client (Infrastructure Layer)."""
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
    ) as client:
        yield client

async def ensure_bucket_exists(client) -> None:
    """Function for bucket verification and creation ."""
    bucket_name = settings.minio_bucket_name
    try:
        await client.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket '{bucket_name}' already exists.")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404":
            logger.info(f"Bucket '{bucket_name}' not found. Creating.")
            await client.create_bucket(Bucket=bucket_name)
        else:
            logger.error(f"Critical S3/MinIO access error: {e}")
            raise e