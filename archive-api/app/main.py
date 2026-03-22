from contextlib import asynccontextmanager
from fastapi import FastAPI
import aioboto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import register_exception_handlers
from app.api.endpoints import router as archives_router
from app.core.s3 import get_s3_client, ensure_bucket_exists

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing S3 client")
    async with get_s3_client() as client:
        await ensure_bucket_exists(client)
        app.state.s3_client = client
        yield
    logger.info("Server shutting down! S3 client closed")


app = FastAPI(title="Archive API", lifespan=lifespan)

app.include_router(archives_router)
register_exception_handlers(app)
