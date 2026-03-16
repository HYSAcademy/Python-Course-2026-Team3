import re
import aioboto3
import uuid
from pathlib import Path
from typing import BinaryIO
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logger import logger 
from app.schemas.contracts import S3UploadResult

class S3Service:
    def __init__(self):
        self.session = aioboto3.Session()
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self.s3_config = {
            "endpoint_url": settings.MINIO_ENDPOINT,
            "aws_access_key_id": settings.MINIO_ROOT_USER,
            "aws_secret_access_key": settings.MINIO_ROOT_PASSWORD,
        }

    
    def _sanitize_object_name(self, filename: str) -> str:
        """
        Sanitizes filename by removing dangerous characters and paths
        """
        clean_name = Path(filename).name
        clean_name = re.sub(r'[^a-zA-Z0-9.\-_]', '_', clean_name)
        
        if not clean_name or clean_name == "_":
            clean_name = "unnamed_archive.zip"
        unique_id = uuid.uuid4().hex[:8] 
        return f"{unique_id}_{clean_name}"

    async def upload_archive(self, file_obj: BinaryIO, object_name: str) -> S3UploadResult:
        """Asynchronously uploads raw archive to MinIO"""

        safe_object_name = self._sanitize_object_name(object_name)
        logger.info(f"Initiating upload of {safe_object_name} to bucket {self.bucket_name}.")
        
        async with self.session.client("s3", **self.s3_config) as s3_client:
            try:
                await s3_client.upload_fileobj(file_obj, self.bucket_name, safe_object_name)
                
                file_url = f"{settings.MINIO_ENDPOINT}/{self.bucket_name}/{safe_object_name}"
                logger.info(f"File successfully uploaded to S3: {file_url}")
                
                return S3UploadResult(
                    file_url=file_url,
                    bucket_name=self.bucket_name,
                    object_name=safe_object_name
                )
            except ClientError as e:
                logger.error(f"S3 upload failed: {e}")
                raise RuntimeError(f"Failed to upload {safe_object_name} to S3")

    async def delete_file(self, object_name: str) -> None:
        """"Deletes file (rollback on DB write failure)"""
        async with self.session.client("s3", **self.s3_config) as s3_client:
            try:
                await s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
                logger.info(f"File {object_name} successfully deleted from S3 (Transaction rollback)")
            except ClientError as e:
                logger.error(f"S3 deletion error: {e}")