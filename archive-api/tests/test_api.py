import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.repositories.archive_repo import ArchiveRepository
from app.services.archive_svc import ArchiveService
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.contracts import ArchiveStatus


@pytest.mark.asyncio
async def test_upload_archive_success(mocker):
    """Test successful archive upload (returns 202 Accepted)."""

    app.state.s3_client = MagicMock()
    mocker.patch.object(ArchiveRepository, "create_archive", new_callable=AsyncMock)
    mocker.patch.object(AsyncSession, "commit", new_callable=AsyncMock)
    mocker.patch.object(
        ArchiveService, "process_archive_background", new_callable=AsyncMock
    )
    fake_zip_content = b"PK\x03\x04...fake_zip_data..."
    files = {"file": ("test_archive.zip", fake_zip_content, "application/zip")}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.post("/upload-archives/", files=files)

    assert response.status_code == 202
    data = response.json()
    assert data["filename"] == "test_archive.zip"
    assert data["status"] == "pending"
    assert "archive_id" in data


@pytest.mark.asyncio
async def test_get_archive_status_success(mocker):
    """Test retrieving archive status (returns 200 OK)."""

    app.state.s3_client = MagicMock()
    fake_archive = MagicMock()
    fake_archive.id = "fake-uuid-123"
    fake_archive.status = ArchiveStatus.COMPLETED
    fake_archive.s3_object_name = "fake-uuid-123_test_archive.zip"
    fake_archive.error_message = None
    fake_archive.extracted_files = []

    mocker.patch.object(
        ArchiveRepository,
        "get_archive_by_id",
        return_value=fake_archive,
        new_callable=AsyncMock,
    )

    mocker.patch.object(
        ArchiveService,
        "get_full_s3_url",
        return_value="http://fake-minio/archives/fake.zip",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        response = await ac.get("/archives/fake-uuid-123")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["archive_id"] == "fake-uuid-123"
    assert data["s3_url"] == "http://fake-minio/archives/fake.zip"
