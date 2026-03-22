from fastapi import (
    APIRouter,
    UploadFile,
    File,
    BackgroundTasks,
    Request,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.services.archive_svc import ArchiveService
from app.services.validation_service import ValidationService, ValidationError
from app.services.validators import SizeValidator, MimeTypeValidator, SecurityValidator
from app.db.database import get_db
from app.models.archive import Archive
from app.repositories.archive_repo import ArchiveRepository
from app.schemas.contracts import (
    ArchiveStatus,
    ArchiveUploadResponse,
    ArchiveDetailResponse,
)

router = APIRouter(tags=["Archives"])


@router.post(
    "/upload-archives/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ArchiveUploadResponse,
)
async def upload_archive_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()

    validation_service = ValidationService(validators=[
        SizeValidator(),
        MimeTypeValidator(),
        SecurityValidator(),
    ])

    try:
        await validation_service.validate(file, file_bytes)
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    archive_id, s3_object_name = ArchiveService.generate_archive_metadata(file.filename)

    repo = ArchiveRepository(session)
    new_archive = Archive(
        id=archive_id,
        filename=file.filename,
        s3_object_name=s3_object_name,
        status=ArchiveStatus.PENDING,
    )
    await repo.create_archive(new_archive)
    await session.commit()

    s3_client = request.app.state.s3_client
    archive_svc = ArchiveService(s3_client=s3_client)

    background_tasks.add_task(
        archive_svc.process_archive_background,
        archive_id=archive_id,
        filename=file.filename,
        file_bytes=file_bytes,
        s3_object_name=s3_object_name,
    )

    return ArchiveUploadResponse(
        archive_id=archive_id,
        filename=file.filename,
        status=ArchiveStatus.PENDING,
        message="Archive is being processed in the background.",
    )


@router.get("/archives/{archive_id}", response_model=ArchiveDetailResponse)
async def get_archive_status(
    archive_id: str, request: Request, session: AsyncSession = Depends(get_db)
):
    """
    Returns archive processing status.
    If COMPLETED — returns list of files.
    If FAILED — returns error reason.
    """
    repo = ArchiveRepository(session)
    archive = await repo.get_archive_by_id(archive_id)

    if not archive:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archive with ID {archive_id} not found.",
        )

    s3_client = request.app.state.s3_client
    archive_svc = ArchiveService(s3_client=s3_client)
    full_s3_url = archive_svc.get_full_s3_url(archive.s3_object_name)

    return ArchiveDetailResponse(
        archive_id=archive.id,
        status=archive.status,
        s3_url=full_s3_url,
        error_message=(
            archive.error_message if archive.status == ArchiveStatus.FAILED else None
        ),
        extracted_files=(
            archive.extracted_files if archive.status == ArchiveStatus.COMPLETED else []
        ),
    )