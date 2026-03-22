from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    worker_max_tasks_per_child=50,
    worker_max_memory_per_child=512000, 
    task_acks_late=True,  
    worker_prefetch_multiplier=1,
)