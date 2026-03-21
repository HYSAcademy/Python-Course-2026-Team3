import zipfile
import tarfile
from typing import Generator, IO, Protocol
from pathlib import Path

from app.core.logger import logger
from app.schemas.contracts import ParsedDocument
from app.core.config import settings

MAX_FILE_SIZE_BYTES = settings.max_extract_size_mb * 1024 * 1024

ALLOWED_TEXT_EXTENSIONS = {
    ".txt",
    ".csv",
    ".json",
    ".md",
    ".xml",
    ".html",
    ".py",
    ".js",
    ".css",
    ".log",
}


class IExtractor(Protocol):
    """Interface for all archive extractors. All new formats must adhere to it."""

    def extract(self, file_obj: IO) -> Generator[ParsedDocument, None, None]: ...


class ZipExtractor:
    """ "Extractor for secure reading of .zip files."""

    def extract(self, file_obj: IO) -> Generator[ParsedDocument, None, None]:
        with zipfile.ZipFile(file_obj, "r") as z:
            for info in z.infolist():
                if info.is_dir():
                    continue

                if ".." in info.filename or info.filename.startswith("/"):
                    logger.warning(f"Path Traversal blocked: {info.filename}")
                    continue

                if info.file_size > MAX_FILE_SIZE_BYTES:
                    logger.error(
                        f"File {info.filename} is too large ({info.file_size} bytes). Skipping."
                    )
                    continue

                file_extension = Path(info.filename).suffix.lower()
                if file_extension not in ALLOWED_TEXT_EXTENSIONS:
                    logger.info(
                        f"Skipping non-text file based on extension: {info.filename}"
                    )
                    continue

                with z.open(info) as f:
                    content = f.read().decode("utf-8", errors="replace")
                    yield ParsedDocument(
                        original_filename=info.filename,
                        content=content,
                        file_size=info.file_size,
                    )


class TarExtractor:
    """Extractor for secure reading of .tar.gz files"""

    def extract(self, file_obj: IO) -> Generator[ParsedDocument, None, None]:
        with tarfile.open(fileobj=file_obj, mode="r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue

                if ".." in member.name or member.name.startswith("/"):
                    logger.warning(f"Path Traversal blocked: {member.name}")
                    continue

                if member.size > MAX_FILE_SIZE_BYTES:
                    logger.error(
                        f"File {member.name} is too large ({member.size} bytes). Skipping."
                    )
                    continue

                file_extension = Path(member.name).suffix.lower()
                if file_extension not in ALLOWED_TEXT_EXTENSIONS:
                    logger.info(
                        f"Skipping non-text file based on extension: {member.name}"
                    )
                    continue

                f = tar.extractfile(member)
                if f is not None:
                    content = f.read().decode("utf-8", errors="replace")
                    yield ParsedDocument(
                        original_filename=member.name,
                        content=content,
                        file_size=member.size,
                    )


class ExtractorFactory:
    """ "Factory that determines which extractor to instantiate based on the file extension."""

    @staticmethod
    def get_extractor(filename: str) -> IExtractor:
        if filename.endswith(".zip"):
            logger.info(f"Factory created ZipExtractor for {filename}")
            return ZipExtractor()
        elif filename.endswith(".tar.gz") or filename.endswith(".tgz"):
            logger.info(f"Factory created TarExtractor for {filename}")
            return TarExtractor()
        else:
            logger.error(f"Attempted to unpack an unsupported format: {filename}")
            raise ValueError(
                f"Unsupported format for {filename}. Only .zip and .tar.gz are allowed."
            )
