from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class ArchiveStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ArchiveUploadResponse(BaseModel):
    archive_id: str
    filename: str
    status: ArchiveStatus
    message: str

class ExtractedFileSchema(BaseModel):
    file_name: str
    size_bytes: int

class ArchiveDetailResponse(BaseModel):
    archive_id: str
    status: ArchiveStatus
    error_message: Optional[str] = None
    extracted_files: List[ExtractedFileSchema] = []

class ParsedDocument(BaseModel):
    original_filename: str
    content: str
    file_size: int

class S3UploadResult(BaseModel):
    file_url: str
    bucket_name: str
    object_name: str