from contextlib import asynccontextmanager
from fastapi import FastAPI
import aioboto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import register_exception_handlers
from app.api.endpoints import router as archives_router


async def _ensure_bucket_exists(client) -> None:
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializing S3 client"""
    logger.info("Initializing S3 client")
    session = aioboto3.Session()
    
    async with session.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
    ) as client:
        
        await _ensure_bucket_exists(client)
            
        yield {"s3_client": client}
        
    logger.info("Server shutting down! S3 client closed")


app = FastAPI(title="Archive API", lifespan=lifespan)

app.include_router(archives_router)
register_exception_handlers(app)