from pydantic import BaseModel, ConfigDict, Field
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

    model_config = ConfigDict(from_attributes=True)


class ArchiveDetailResponse(BaseModel):
    archive_id: str
    status: ArchiveStatus
    s3_url: Optional[str] = None
    error_message: Optional[str] = None
    extracted_files: List[ExtractedFileSchema] = []
    model_config = ConfigDict(from_attributes=True)


class ParsedDocument(BaseModel):
    original_filename: str
    content: str
    file_size: int


class S3UploadResult(BaseModel):
    file_url: str
    bucket_name: str
    object_name: str

class IndexCommandResponse(BaseModel):
    """Response for POST /archives/{id}/index (202 Accepted)"""
    archive_id: str
    message: str


class SearchQueryDTO(BaseModel):
    """
    Request body for POST /search.
    """
    query: str = Field(..., min_length=2, description="Search phrase (e.g., 'server configuration')")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return (maximum 100)")


class SearchResultItem(BaseModel):
    """A single found file with its weight"""
    archive_id: str
    filename: str
    s3_object_name: str
    score: float

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    """Full response for the search endpoint"""
    query: str
    results: List[SearchResultItem]
