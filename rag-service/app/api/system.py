from fastapi import APIRouter

router = APIRouter(tags=["System"])

@router.get("/health")
async def health_check():
    """Ендпоінт для Docker Healthcheck"""
    return {"status": "ok", "service": "rag-service"}