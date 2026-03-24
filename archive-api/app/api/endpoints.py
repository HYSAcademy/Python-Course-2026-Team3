from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Request,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.services.archive_svc import ArchiveService
from app.core.config import settings
from app.services.validation_service import ValidationService, ValidationError
from app.services.validators import SizeValidator, MimeTypeValidator, SecurityValidator
from app.db.database import get_db
from app.models.archive import Archive
from app.repositories.archive_repo import ArchiveRepository
from app.schemas.contracts import (
    ArchiveStatus,
    ArchiveUploadResponse,
    ArchiveDetailResponse,
    IndexCommandResponse,  
    SearchQueryDTO,
    SearchResponse,
)
from app.worker.tasks import process_archive_task

router = APIRouter(tags=["Archives"])
ALLOWED_EXTENSIONS = (".zip", ".tar.gz", ".tgz")


@router.post(
    "/upload-archives/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ArchiveUploadResponse,
)
async def upload_archive_endpoint(
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    """
    Accepts an archive, creates a record in the database, 
    streams it to S3, and enqueues a task in Celery for processing.
    """
    try:
        validator_svc = ValidationService(validators=[
            MimeTypeValidator(),
            SizeValidator(),
            SecurityValidator()
        ])
        
        await validator_svc.validate(file)
        
    except ValidationError as e:
        logger.warning(f"Validation failed for {file.filename}: {e}")
        status_code = getattr(e, 'status_code', status.HTTP_400_BAD_REQUEST)
        raise HTTPException(status_code=status_code, detail=str(e))
    
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
    
    try:
        await archive_svc.upload_stream_to_s3(s3_object_name, file)
        
    except Exception as e:
        logger.error(f"Error uploading archive {archive_id} to MinIO: {e}")
        await repo.update_status(archive_id, ArchiveStatus.FAILED, str(e))
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to securely upload file to object storage."
        )
    
    process_archive_task.delay(str(archive_id))
    
    logger.info(f"Archive {archive_id} successfully saved to S3. Task sent to Celery.")

    return ArchiveUploadResponse(
        archive_id=archive_id,
        filename=file.filename,
        status=ArchiveStatus.PENDING,
        message="Archive is successfully uploaded to S3 and queued for background processing.",
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
    
    full_s3_url = archive_svc.get_full_s3_url(archive.s3_object_name) if archive.s3_object_name else None

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

@router.post(
    "/archives/{archive_id}/index",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IndexCommandResponse
)
async def trigger_archive_indexing(
    archive_id: str,
    session: AsyncSession = Depends(get_db)
):
    """
    Manually triggers the background indexing process for an existing archive.
    """
    repo = ArchiveRepository(session)
    archive = await repo.get_archive_by_id(archive_id)

    if not archive:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archive with ID {archive_id} not found."
        )
    await repo.update_status(archive_id, ArchiveStatus.PROCESSING, error_message=None)
    await session.commit()
    process_archive_task.delay(str(archive_id))
    
    logger.info(f"[Manual Index] Triggered processing for Archive {archive_id}.")

    return IndexCommandResponse(
        archive_id=archive_id,
        message="Indexing task has been successfully enqueued.",
    )


@router.post(
    "/search",
    status_code=status.HTTP_200_OK,
    response_model=SearchResponse
)
async def search_documents(
    query_dto: SearchQueryDTO,
    request: Request,
    session: AsyncSession = Depends(get_db)
):
    """
    Performs an asynchronous Search using BM25 JSONB indexes.
    """
    repo = ArchiveRepository(session)
    s3_client = request.app.state.s3_client
    archive_svc = ArchiveService(s3_client=s3_client)

    search_results = await repo.search_bm25(query=query_dto.query, top_k=query_dto.top_k)
    for result in search_results:
        result.s3_object_name = archive_svc.get_full_s3_url(result.s3_object_name)

    return SearchResponse(
        query=query_dto.query,
        results=search_results
    )