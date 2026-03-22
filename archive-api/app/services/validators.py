import zipfile
import os

from fastapi import UploadFile

from app.core.config import settings
from app.core.logger import logger
from app.services.validation_service import IFileValidator, ValidationError

ALLOWED_CONTENT_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "application/x-tar",
    "application/gzip",
    "application/x-gzip",
}

ALLOWED_EXTENSIONS = {".zip", ".tar.gz", ".tgz"}


class SizeValidator(IFileValidator):
    """Rejects files that exceed the configured upload size limit."""

    async def validate(self, file: UploadFile) -> None:
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0) 

        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if file_size > max_bytes:
            raise ValidationError(
                f"File '{file.filename}' exceeds the maximum allowed size "
                f"of {settings.max_upload_size_mb} MB.",
                status_code=413, 
            )


class MimeTypeValidator(IFileValidator):
    """Rejects files with unsupported extensions or content types."""

    async def validate(self, file: UploadFile) -> None:
        filename = file.filename or ""

        if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise ValidationError(
                f"Unsupported file type '{filename}'. "
                f"Only .zip and .tar.gz are allowed.",
                status_code=415,
            )

        if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
            logger.warning(
                f"Suspicious content-type '{file.content_type}' "
                f"for file '{filename}'. Proceeding with extension check only."
            )


class SecurityValidator(IFileValidator):
    """
    Zip Bomb protection — checks compression ratio before full extraction.
    Only applies to .zip files.
    """

    async def validate(self, file: UploadFile) -> None:
        filename = file.filename or ""
        if not filename.endswith(".zip"):
            return

        max_extract_bytes = settings.max_extract_size_mb * 1024 * 1024

        try:
            with zipfile.ZipFile(file.file) as zf:
                total_uncompressed = sum(
                    info.file_size for info in zf.infolist()
                )
                if total_uncompressed > max_extract_bytes:
                    raise ValidationError(
                        f"Zip Bomb detected: '{filename}' would extract to "
                        f"{total_uncompressed // (1024 * 1024)} MB which exceeds "
                        f"the {settings.max_extract_size_mb} MB limit.",
                        status_code=400,
                    )
        except zipfile.BadZipFile:
            raise ValidationError(
                f"File '{filename}' is not a valid ZIP archive.",
                status_code=400,
            )