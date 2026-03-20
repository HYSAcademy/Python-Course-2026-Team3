from typing import Any, BinaryIO
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logger import logger


class S3Service:
    def __init__(self, s3_client: Any):
        self.s3_client = s3_client
        self.bucket_name = settings.minio_bucket_name
        self.endpoint_url = settings.minio_endpoint

    async def upload_archive(self, file_obj: BinaryIO, object_name: str) -> None:
        """Asynchronously uploads raw archive to MinIO"""
        logger.info(
            f"Initiating upload of '{object_name}' to bucket '{self.bucket_name}'."
        )

        try:
            await self.s3_client.upload_fileobj(file_obj, self.bucket_name, object_name)
            logger.info(f"File successfully uploaded to S3: {object_name}")
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise RuntimeError(f"Failed to upload {object_name} to S3")

    async def delete_file(self, object_name: str) -> None:
        """Deletes file (rollback on DB write failure)"""
        try:
            await self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info(
                f"File '{object_name}' successfully deleted from S3 (Transaction rollback)."
            )
        except ClientError as e:
            logger.error(f"S3 deletion error: {e}")
