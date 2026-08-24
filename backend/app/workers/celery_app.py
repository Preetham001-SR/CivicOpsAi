from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "civicops",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    result_expires=3600,
    task_routes={
        "app.workers.tasks.intake.*": {"queue": "intake"},
        "app.workers.tasks.vision.*": {"queue": "vision"},
        "app.workers.tasks.speech.*": {"queue": "speech"},
        "app.workers.tasks.location.*": {"queue": "location"},
        "app.workers.tasks.rag.*": {"queue": "rag"},
        "app.workers.tasks.decision.*": {"queue": "decision"},
        "app.workers.tasks.verification.*": {"queue": "verification"},
        "app.workers.tasks.work_order.*": {"queue": "work_order"},
    },
    task_annotations={
        "*": {
            "rate_limit": "10/m",
        }
    },
)