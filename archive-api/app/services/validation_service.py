from abc import ABC, abstractmethod
from fastapi import UploadFile

from app.core.logger import logger


class ValidationError(Exception):
    """Raised when a file fails validation."""
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class IFileValidator(ABC):
    """Abstract base class for all file validators (Chain of Responsibility)."""

    @abstractmethod
    async def validate(self, file: UploadFile, file_bytes: bytes) -> None:
        """Raise ValidationError if validation fails."""
        ...


class ValidationService:
    """
    Runs a file through a chain of validators sequentially.
    Adding a new rule = creating a new IFileValidator subclass (OCP).
    """

    def __init__(self, validators: list[IFileValidator]) -> None:
        self._validators = validators

    async def validate(self, file: UploadFile, file_bytes: bytes) -> None:
        for validator in self._validators:
            logger.debug(f"Running {validator.__class__.__name__} on '{file.filename}'")
            await validator.validate(file, file_bytes)