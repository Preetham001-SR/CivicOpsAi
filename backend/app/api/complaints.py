from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import structlog
import tempfile
import os

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
    ReviewQueueItem,
    ReviewQueueStats,
)
from app.agents.pipeline import pipeline, ComplaintState
from app.core.config import settings
from app.core.observability import get_tracer
from app.services.minio import minio_client

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
        await db.commit()
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


@router.post("/complaints/upload", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint_upload(
    background_tasks: BackgroundTasks,
    text_description: str = Form(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str = Form(None),
    photo: UploadFile = File(None),
    audio: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    with tracer.start_as_current_span("api.create_complaint_upload") as span:
        photo_url = None
        audio_url = None
        
        # Upload photo to MinIO if provided
        if photo and photo.filename:
            try:
                file_ext = os.path.splitext(photo.filename)[1] or '.jpg'
                object_name = f"complaints/{uuid.uuid4()}/photo{file_ext}"
                content = await photo.read()
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                minio_client.fput_object(
                    bucket_name=settings.MINIO_BUCKET,
                    object_name=object_name,
                    file_path=tmp_path,
                    content_type=photo.content_type or 'image/jpeg'
                )
                os.unlink(tmp_path)
                photo_url = f"http://minio:9000/{settings.MINIO_BUCKET}/{object_name}"
            except Exception as e:
                logger.warning("photo_upload_failed", error=str(e))
        
        # Upload audio to MinIO if provided
        if audio and audio.filename:
            try:
                file_ext = os.path.splitext(audio.filename)[1] or '.wav'
                object_name = f"complaints/{uuid.uuid4()}/audio{file_ext}"
                content = await audio.read()
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                minio_client.fput_object(
                    bucket_name=settings.MINIO_BUCKET,
                    object_name=object_name,
                    file_path=tmp_path,
                    content_type=audio.content_type or 'audio/wav'
                )
                os.unlink(tmp_path)
                audio_url = f"http://minio:9000/{settings.MINIO_BUCKET}/{object_name}"
            except Exception as e:
                logger.warning("audio_upload_failed", error=str(e))
        
        # Create complaint record
        complaint = Complaint(
            text_description=text_description,
            photo_url=photo_url,
            audio_url=audio_url,
            latitude=latitude,
            longitude=longitude,
            address=address,
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
        
        logger.info("complaint_created_upload", complaint_id=str(complaint.id))
        
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


@router.get("/review/queue", response_model=list[ReviewQueueItem])
async def get_review_queue(
    tier: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get complaints awaiting human review."""
    query = select(Complaint).where(
        Complaint.status.in_([
            ComplaintStatus.AWAITING_REVIEW,
            ComplaintStatus.PROCESSING,
        ])
    ).order_by(Complaint.created_at.desc())
    
    if tier:
        if tier == "mandatory":
            query = query.where(Complaint.confidence_score < settings.CONFIDENCE_THRESHOLD_REVIEW)
        elif tier == "optional":
            query = query.where(
                Complaint.confidence_score >= settings.CONFIDENCE_THRESHOLD_REVIEW,
                Complaint.confidence_score < settings.CONFIDENCE_THRESHOLD_AUTO
            )
        elif tier == "auto":
            query = query.where(Complaint.confidence_score >= settings.CONFIDENCE_THRESHOLD_AUTO)
    
    if status:
        query = query.where(Complaint.status == status)
    
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    complaints = result.scalars().all()
    
    return [
        ReviewQueueItem(
            complaint_id=c.id,
            text_description=c.text_description,
            category=c.category.value if c.category else None,
            priority=c.priority.value if c.priority else None,
            confidence_score=c.confidence_score,
            review_tier=(
                "mandatory" if (c.confidence_score or 0) < settings.CONFIDENCE_THRESHOLD_REVIEW
                else "optional" if (c.confidence_score or 0) < settings.CONFIDENCE_THRESHOLD_AUTO
                else "auto"
            ),
            latitude=c.latitude,
            longitude=c.longitude,
            address=c.address,
            created_at=c.created_at,
            photo_url=c.photo_url,
            audio_url=c.audio_url,
        )
        for c in complaints
    ]


@router.get("/review/stats", response_model=ReviewQueueStats)
async def get_review_stats(db: AsyncSession = Depends(get_db)):
    """Get review queue statistics."""
    from sqlalchemy import func
    
    result = await db.execute(
        select(
            func.count(Complaint.id).label("total"),
            func.avg(Complaint.confidence_score).label("avg_confidence"),
        ).where(
            Complaint.status.in_([
                ComplaintStatus.AWAITING_REVIEW,
                ComplaintStatus.PROCESSING,
            ])
        )
    )
    row = result.one()
    
    mandatory = await db.execute(
        select(func.count(Complaint.id)).where(
            Complaint.status.in_([ComplaintStatus.AWAITING_REVIEW, ComplaintStatus.PROCESSING]),
            Complaint.confidence_score < settings.CONFIDENCE_THRESHOLD_REVIEW
        )
    )
    
    optional = await db.execute(
        select(func.count(Complaint.id)).where(
            Complaint.status.in_([ComplaintStatus.AWAITING_REVIEW, ComplaintStatus.PROCESSING]),
            Complaint.confidence_score >= settings.CONFIDENCE_THRESHOLD_REVIEW,
            Complaint.confidence_score < settings.CONFIDENCE_THRESHOLD_AUTO
        )
    )
    
    auto = await db.execute(
        select(func.count(Complaint.id)).where(
            Complaint.status.in_([ComplaintStatus.AWAITING_REVIEW, ComplaintStatus.PROCESSING]),
            Complaint.confidence_score >= settings.CONFIDENCE_THRESHOLD_AUTO
        )
    )
    
    return ReviewQueueStats(
        total_pending=row.total or 0,
        mandatory_review=mandatory.scalar() or 0,
        optional_review=optional.scalar() or 0,
        auto_processed=auto.scalar() or 0,
        avg_confidence=float(row.avg_confidence) if row.avg_confidence else None,
    )


@router.get("/review/next/{reviewer_id}", response_model=ReviewQueueItem)
async def get_next_review(
    reviewer_id: str,
    tier: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get the next complaint for a reviewer to process."""
    query = select(Complaint).where(
        Complaint.status.in_([
            ComplaintStatus.AWAITING_REVIEW,
            ComplaintStatus.PROCESSING,
        ])
    ).order_by(Complaint.created_at.asc())
    
    if tier:
        if tier == "mandatory":
            query = query.where(Complaint.confidence_score < settings.CONFIDENCE_THRESHOLD_REVIEW)
        elif tier == "optional":
            query = query.where(
                Complaint.confidence_score >= settings.CONFIDENCE_THRESHOLD_REVIEW,
                Complaint.confidence_score < settings.CONFIDENCE_THRESHOLD_AUTO
            )
    
    result = await db.execute(query.limit(1))
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="No complaints awaiting review")
    
    return ReviewQueueItem(
        complaint_id=complaint.id,
        text_description=complaint.text_description,
        category=complaint.category.value if complaint.category else None,
        priority=complaint.priority.value if complaint.priority else None,
        confidence_score=complaint.confidence_score,
        review_tier=(
            "mandatory" if (complaint.confidence_score or 0) < settings.CONFIDENCE_THRESHOLD_REVIEW
            else "optional" if (complaint.confidence_score or 0) < settings.CONFIDENCE_THRESHOLD_AUTO
            else "auto"
        ),
        latitude=complaint.latitude,
        longitude=complaint.longitude,
        address=complaint.address,
        created_at=complaint.created_at,
        photo_url=complaint.photo_url,
        audio_url=complaint.audio_url,
    )