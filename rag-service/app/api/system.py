from fastapi import APIRouter

router = APIRouter(tags=["System"])

@router.get("/health")
async def health_check():
    """Health check endpoint to verify that the service is running."""
    return {"status": "ok", "service": "rag-service"}