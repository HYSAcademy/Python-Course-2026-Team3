from typing import Any
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logger import logger

class S3Service:
    def __init__(self, s3_client: Any):
        self.s3_client = s3_client
        self.bucket_name = settings.minio_bucket_name
        self.endpoint_url = settings.minio_endpoint

    async def get_text_file(self, object_name: str) -> str:
        """Downloads a file from MinIO and decodes it to a UTF-8 string."""
        logger.info(f"Downloading text file '{object_name}' from S3.")
        try:
            response = await self.s3_client.get_object(Bucket=self.bucket_name, Key=object_name)
            async with response["Body"] as stream:
                file_bytes = await stream.read()
                return file_bytes.decode("utf-8")
        except ClientError as e:
            logger.error(f"S3 download failed for {object_name}: {e}")
            raise RuntimeError(f"Failed to download {object_name} from S3")
        except UnicodeDecodeError as e:
            logger.error(f"File {object_name} is not valid UTF-8 text: {e}")
            raise RuntimeError(f"File {object_name} contains non-text data")