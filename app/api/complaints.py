from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import structlog

from app.db.session import get_db
from app.db.models import Complaint, ComplaintStatus, AgentLog, HumanReview, WorkOrder
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintResponse,
    ComplaintUpdate,
    AgentLogResponse,
    HumanReviewCreate,
    HumanReviewResponse,
    WorkOrderResponse,
    HealthResponse,
)
from app.agents.pipeline import pipeline, ComplaintState
from app.core.config import settings
from app.core.observability import get_tracer

logger = structlog.get_logger()
tracer = get_tracer(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    # Check database
    db_status = "healthy"
    try:
        await db.execute(select(1))
    except Exception:
        db_status = "unhealthy"
    
    # Check redis
    redis_status = "healthy"
    try:
        from app.workers.celery_app import celery_app
        celery_app.control.ping(timeout=1)
    except Exception:
        redis_status = "unhealthy"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded",
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        database=db_status,
        redis=redis_status,
    )


@router.post("/complaints", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    complaint_data: ComplaintCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    with tracer.start_as_current_span("api.create_complaint") as span:
        # Create complaint record
        complaint = Complaint(
            text_description=complaint_data.text_description,
            photo_url=str(complaint_data.photo_url) if complaint_data.photo_url else None,
            audio_url=str(complaint_data.audio_url) if complaint_data.audio_url else None,
            latitude=complaint_data.latitude,
            longitude=complaint_data.longitude,
            address=complaint_data.address,
            status=ComplaintStatus.PENDING,
        )
        
        db.add(complaint)
        await db.flush()
        await db.refresh(complaint)
        
        span.set_attribute("complaint_id", str(complaint.id))
        
        # Prepare initial state for pipeline
        initial_state = ComplaintState(
            complaint_id=complaint.id,
            text_description=complaint.text_description,
            photo_url=complaint.photo_url,
            audio_url=complaint.audio_url,
            latitude=complaint.latitude,
            longitude=complaint.longitude,
            address=complaint.address,
            vision_analysis=None,
            speech_transcript=None,
            location_details=None,
            rag_context=None,
            rag_sources=[],
            decision=None,
            verification=None,
            confidence_score=None,
            requires_human_review=False,
            human_review_decision=None,
            human_review_notes=None,
            human_review_modified_data=None,
            work_order=None,
            work_order_id=None,
            status="pending",
            errors=[],
            current_agent=None,
            trace_id=str(uuid.uuid4()),
        )
        
        # Run pipeline in background
        background_tasks.add_task(run_pipeline_background, initial_state)
        
        logger.info("complaint_created", complaint_id=str(complaint.id))
        
        return ComplaintResponse.model_validate(complaint)


async def run_pipeline_background(initial_state: ComplaintState):
    try:
        await pipeline.run(initial_state)
        logger.info("pipeline_completed", complaint_id=str(initial_state["complaint_id"]))
    except Exception as e:
        logger.error("pipeline_failed", complaint_id=str(initial_state["complaint_id"]), error=str(e))


@router.get("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(complaint_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    return ComplaintResponse.model_validate(complaint)


@router.get("/complaints/{complaint_id}/logs", response_model=list[AgentLogResponse])
async def get_complaint_logs(complaint_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentLog)
        .where(AgentLog.complaint_id == complaint_id)
        .order_by(AgentLog.created_at)
    )
    logs = result.scalars().all()
    
    return [AgentLogResponse.model_validate(log) for log in logs]


@router.get("/complaints/{complaint_id}/reviews", response_model=list[HumanReviewResponse])
async def get_complaint_reviews(complaint_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HumanReview)
        .where(HumanReview.complaint_id == complaint_id)
        .order_by(HumanReview.created_at)
    )
    reviews = result.scalars().all()
    
    return [HumanReviewResponse.model_validate(review) for review in reviews]


@router.post("/complaints/{complaint_id}/reviews", response_model=HumanReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_human_review(
    complaint_id: uuid.UUID,
    review_data: HumanReviewCreate,
    db: AsyncSession = Depends(get_db),
):
    # Verify complaint exists and is in review state
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    if complaint.status not in [ComplaintStatus.AWAITING_REVIEW, ComplaintStatus.PROCESSING]:
        raise HTTPException(status_code=400, detail="Complaint is not awaiting review")
    
    review = HumanReview(
        complaint_id=complaint_id,
        reviewer_id=review_data.reviewer_id,
        decision=review_data.decision,
        notes=review_data.notes,
        modified_data=review_data.modified_data,
    )
    
    db.add(review)
    
    # Update complaint status
    if review_data.decision == "approve":
        complaint.status = ComplaintStatus.APPROVED
    elif review_data.decision == "reject":
        complaint.status = ComplaintStatus.REJECTED
    elif review_data.decision == "modify":
        complaint.status = ComplaintStatus.PROCESSING
        # Apply modifications
        if review_data.modified_data:
            complaint.decision = review_data.modified_data
    
    from datetime import datetime
    review.completed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(review)
    
    logger.info("human_review_created", complaint_id=str(complaint_id), decision=review_data.decision)
    
    return HumanReviewResponse.model_validate(review)


@router.get("/complaints/{complaint_id}/work-order", response_model=WorkOrderResponse)
async def get_work_order(complaint_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkOrder).where(WorkOrder.complaint_id == complaint_id)
    )
    work_order = result.scalar_one_or_none()
    
    if not work_order:
        raise HTTPException(status_code=404, detail="Work order not found")
    
    return WorkOrderResponse.model_validate(work_order)


@router.patch("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(
    complaint_id: uuid.UUID,
    update_data: ComplaintUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(complaint, field, value)
    
    await db.commit()
    await db.refresh(complaint)
    
    return ComplaintResponse.model_validate(complaint)