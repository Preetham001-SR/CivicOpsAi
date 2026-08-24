from app.workers.tasks.celery_tasks import (
    intake_task,
    vision_task,
    speech_task,
    location_task,
    rag_task,
    decision_task,
    verification_task,
    work_order_task,
)

__all__ = [
    "intake_task",
    "vision_task",
    "speech_task",
    "location_task",
    "rag_task",
    "decision_task",
    "verification_task",
    "work_order_task",
]