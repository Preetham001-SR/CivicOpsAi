import uuid
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.agents.intake import IntakeAgent, IntakeInput
from app.agents.vision import VisionAgent, VisionInput
from app.agents.speech import SpeechAgent, SpeechInput
from app.agents.location import LocationAgent, LocationInput
from app.agents.rag import RagAgent, RagInput
from app.agents.decision import DecisionAgent, DecisionInput
from app.agents.verification import VerificationAgent, VerificationInput
from app.agents.work_order import WorkOrderAgent, WorkOrderInput
from app.agents.pipeline import ComplaintState
from app.db.models import ComplaintCategory, PriorityLevel

logger = structlog.get_logger()


async def _get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        return session


@shared_task(bind=True, name="app.workers.tasks.intake.intake_task", max_retries=3, default_retry_delay=60)
def intake_task(self, complaint_id: str, text_description: str = None, photo_url: str = None, audio_url: str = None, latitude: float = None, longitude: float = None, address: str = None, trace_id: str = None):
    import asyncio
    
    async def _execute():
        async with AsyncSessionLocal() as db:
            agent = IntakeAgent()
            input_data = IntakeInput(
                text_description=text_description,
                photo_url=photo_url,
                audio_url=audio_url,
                latitude=latitude,
                longitude=longitude,
                address=address,
            )
            result = await agent.execute(input_data, db, uuid.UUID(complaint_id), trace_id or str(uuid.uuid4()))
            return result.success, result.output.model_dump() if result.output else None, result.error
    
    try:
        return asyncio.run(_execute())
    except Exception as e:
        logger.error("intake_task_failed", complaint_id=complaint_id, error=str(e))
        raise self.retry(exc=e)


@shared_task(bind=True, name="app.workers.tasks.vision.vision_task", max_retries=3, default_retry_delay=60)
def vision_task(self, complaint_id: str, photo_url: str = None, trace_id: str = None):
    import asyncio
    
    async def _execute():
        async with AsyncSessionLocal() as db:
            agent = VisionAgent()
            input_data = VisionInput(
                photo_url=photo_url,
                complaint_id=complaint_id,
            )
            result = await agent.execute(input_data, db, uuid.UUID(complaint_id), trace_id or str(uuid.uuid4()))
            return result.success, result.output.model_dump() if result.output else None, result.error
    
    try:
        return asyncio.run(_execute())
    except Exception as e:
        logger.error("vision_task_failed", complaint_id=complaint_id, error=str(e))
        raise self.retry(exc=e)


@shared_task(bind=True, name="app.workers.tasks.speech.speech_task", max_retries=3, default_retry_delay=60)
def speech_task(self, complaint_id: str, audio_url: str = None, trace_id: str = None):
    import asyncio
    
    async def _execute():
        async with AsyncSessionLocal() as db:
            agent = SpeechAgent()
            input_data = SpeechInput(
                audio_url=audio_url,
                complaint_id=complaint_id,
            )
            result = await agent.execute(input_data, db, uuid.UUID(complaint_id), trace_id or str(uuid.uuid4()))
            return result.success, result.output.model_dump() if result.output else None, result.error
    
    try:
        return asyncio.run(_execute())
    except Exception as e:
        logger.error("speech_task_failed", complaint_id=complaint_id, error=str(e))
        raise self.retry(exc=e)


@shared_task(bind=True, name="app.workers.tasks.location.location_task", max_retries=3, default_retry_delay=60)
def location_task(self, complaint_id: str, latitude: float, longitude: float, address: str = None, trace_id: str = None):
    import asyncio
    
    async def _execute():
        async with AsyncSessionLocal() as db:
            agent = LocationAgent()
            input_data = LocationInput(
                latitude=latitude,
                longitude=longitude,
                address=address,
                complaint_id=complaint_id,
            )
            result = await agent.execute(input_data, db, uuid.UUID(complaint_id), trace_id or str(uuid.uuid4()))
            return result.success, result.output.model_dump() if result.output else None, result.error
    
    try:
        return asyncio.run(_execute())
    except Exception as e:
        logger.error("location_task_failed", complaint_id=complaint_id, error=str(e))
        raise self.retry(exc=e)


@shared_task(bind=True, name="app.workers.tasks.rag.rag_task", max_retries=3, default_retry_delay=60)
def rag_task(self, complaint_id: str, category: str = None, text_description: str = None, vision_analysis: dict = None, speech_transcript: str = None, location_details: dict = None, trace_id: str = None):
    import asyncio
    
    async def _execute():
        async with AsyncSessionLocal() as db:
            agent = RagAgent()
            cat = ComplaintCategory(category) if category else None
            input_data = RagInput(
                category=cat,
                text_description=text_description,
                vision_analysis=vision_analysis,
                speech_transcript=speech_transcript,
                location_details=location_details,
                complaint_id=complaint_id,
            )
            result = await agent.execute(input_data, db, uuid.UUID(complaint_id), trace_id or str(uuid.uuid4()))
            return result.success, result.output.model_dump() if result.output else None, result.error
    
    try:
        return asyncio.run(_execute())
    except Exception as e:
        logger.error("rag_task_failed", complaint_id=complaint_id, error=str(e))
        raise self.retry(exc=e)


@shared_task(bind=True, name="app.workers.tasks.decision.decision_task", max_retries=3, default_retry_delay=60)
def decision_task(self, complaint_id: str, category: str = None, vision_analysis: dict = None, speech_transcript: str = None, location_details: dict = None, rag_context: dict = None, trace_id: str = None):
    import asyncio
    
    async def _execute():
        async with AsyncSessionLocal() as db:
            agent = DecisionAgent()
            cat = ComplaintCategory(category) if category else None
            input_data = DecisionInput(
                category=cat,
                vision_analysis=vision_analysis,
                speech_transcript=speech_transcript,
                location_details=location_details,
                rag_context=rag_context,
                complaint_id=complaint_id,
            )
            result = await agent.execute(input_data, db, uuid.UUID(complaint_id), trace_id or str(uuid.uuid4()))
            return result.success, result.output.model_dump() if result.output else None, result.error
    
    try:
        return asyncio.run(_execute())
    except Exception as e:
        logger.error("decision_task_failed", complaint_id=complaint_id, error=str(e))
        raise self.retry(exc=e)


@shared_task(bind=True, name="app.workers.tasks.verification.verification_task", max_retries=3, default_retry_delay=60)
def verification_task(self, complaint_id: str, category: str, priority: str, vision_analysis: dict = None, speech_transcript: str = None, location_details: dict = None, rag_context: dict = None, decision: dict = None, trace_id: str = None):
    import asyncio
    
    async def _execute():
        async with AsyncSessionLocal() as db:
            agent = VerificationAgent()
            cat = ComplaintCategory(category)
            pri = PriorityLevel(priority)
            input_data = VerificationInput(
                category=cat,
                priority=pri,
                vision_analysis=vision_analysis,
                speech_transcript=speech_transcript,
                location_details=location_details,
                rag_context=rag_context,
                decision=decision,
                complaint_id=complaint_id,
            )
            result = await agent.execute(input_data, db, uuid.UUID(complaint_id), trace_id or str(uuid.uuid4()))
            return result.success, result.output.model_dump() if result.output else None, result.error
    
    try:
        return asyncio.run(_execute())
    except Exception as e:
        logger.error("verification_task_failed", complaint_id=complaint_id, error=str(e))
        raise self.retry(exc=e)


@shared_task(bind=True, name="app.workers.tasks.work_order.work_order_task", max_retries=3, default_retry_delay=60)
def work_order_task(self, complaint_id: str, category: str, priority: str, latitude: float, longitude: float, address: str = None, vision_analysis: dict = None, speech_transcript: str = None, location_details: dict = None, decision: dict = None, verification: dict = None, human_review_modified_data: dict = None, trace_id: str = None):
    import asyncio
    
    async def _execute():
        async with AsyncSessionLocal() as db:
            agent = WorkOrderAgent()
            cat = ComplaintCategory(category)
            pri = PriorityLevel(priority)
            input_data = WorkOrderInput(
                complaint_id=complaint_id,
                category=cat,
                priority=pri,
                latitude=latitude,
                longitude=longitude,
                address=address,
                vision_analysis=vision_analysis,
                speech_transcript=speech_transcript,
                location_details=location_details,
                decision=decision,
                verification=verification,
                human_review_modified_data=human_review_modified_data,
            )
            result = await agent.execute(input_data, db, uuid.UUID(complaint_id), trace_id or str(uuid.uuid4()))
            return result.success, result.output.model_dump() if result.output else None, result.error
    
    try:
        return asyncio.run(_execute())
    except Exception as e:
        logger.error("work_order_task_failed", complaint_id=complaint_id, error=str(e))
        raise self.retry(exc=e)


@shared_task(bind=True, name="app.workers.tasks.pipeline.run_pipeline_task", max_retries=1, default_retry_delay=300)
def run_pipeline_task(self, initial_state: dict):
    import asyncio
    from app.agents.pipeline import pipeline
    
    async def _execute():
        state = ComplaintState(**initial_state)
        return await pipeline.run(state)
    
    try:
        return asyncio.run(_execute())
    except Exception as e:
        logger.error("pipeline_task_failed", complaint_id=initial_state.get("complaint_id"), error=str(e))
        raise self.retry(exc=e)