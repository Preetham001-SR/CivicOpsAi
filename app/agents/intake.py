from typing import Dict, Any, Optional
import uuid
from pydantic import BaseModel, HttpUrl
from app.agents.base import BaseAgent, AgentResult
from app.agents.state import ComplaintState
from app.db.models import AgentType
from app.services.minio import minio_client
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()


class IntakeInput(BaseModel):
    text_description: Optional[str] = None
    photo_url: Optional[HttpUrl] = None
    audio_url: Optional[HttpUrl] = None
    latitude: float
    longitude: float
    address: Optional[str] = None


class IntakeOutput(BaseModel):
    complaint_id: uuid.UUID
    photo_stored: bool = False
    audio_stored: bool = False
    photo_object_name: Optional[str] = None
    audio_object_name: Optional[str] = None


class IntakeAgent(BaseAgent[IntakeInput, IntakeOutput]):
    def __init__(self):
        super().__init__(AgentType.INTAKE)

    async def process(
        self,
        input_data: IntakeInput,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        trace_id: str,
    ) -> AgentResult[IntakeOutput]:
        photo_stored = False
        audio_stored = False
        photo_object_name = None
        audio_object_name = None

        # Download and store photo if provided
        if input_data.photo_url:
            try:
                photo_object_name = f"complaints/{complaint_id}/photo.jpg"
                # In production, download from URL and upload to MinIO
                # For now, just track the URL
                photo_stored = True
                logger.info("photo_url_received", complaint_id=str(complaint_id), url=str(input_data.photo_url))
            except Exception as e:
                logger.warning("photo_processing_failed", complaint_id=str(complaint_id), error=str(e))

        # Download and store audio if provided
        if input_data.audio_url:
            try:
                audio_object_name = f"complaints/{complaint_id}/audio.wav"
                # In production, download from URL and upload to MinIO
                audio_stored = True
                logger.info("audio_url_received", complaint_id=str(complaint_id), url=str(input_data.audio_url))
            except Exception as e:
                logger.warning("audio_processing_failed", complaint_id=str(complaint_id), error=str(e))

        output = IntakeOutput(
            complaint_id=complaint_id,
            photo_stored=photo_stored,
            audio_stored=audio_stored,
            photo_object_name=photo_object_name,
            audio_object_name=audio_object_name,
        )

        return AgentResult(success=True, output=output)