from typing import Dict, Any, Optional
import uuid
from pydantic import BaseModel, field_validator, Field
from app.agents.base import BaseAgent, AgentResult
from app.db.models import AgentType
from app.services.minio import minio_client
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import httpx
import magic
import io

logger = structlog.get_logger()


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/mp3", "audio/mpeg", "audio/ogg", "audio/webm", "audio/m4a"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class IntakeInput(BaseModel):
    text_description: Optional[str] = Field(default=None, max_length=5000)
    photo_url: Optional[str] = None
    audio_url: Optional[str] = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: Optional[str] = Field(default=None, max_length=500)

    @field_validator('photo_url', 'audio_url', mode='before')
    @classmethod
    def validate_urls(cls, v):
        if v is not None and str(v).strip() == "":
            return None
        # Validate URL format if provided
        if v is not None:
            from pydantic import HttpUrl
            try:
                HttpUrl(v)  # Validate format
            except Exception:
                raise ValueError(f"Invalid URL format: {v}")
        return v


class IntakeOutput(BaseModel):
    complaint_id: uuid.UUID
    photo_stored: bool = False
    audio_stored: bool = False
    photo_object_name: Optional[str] = None
    audio_object_name: Optional[str] = None
    photo_url: Optional[str] = None
    audio_url: Optional[str] = None
    validation_errors: list[str] = Field(default_factory=list)


class IntakeAgent(BaseAgent[IntakeInput, IntakeOutput]):
    def __init__(self):
        super().__init__(AgentType.INTAKE)

    async def _validate_and_download(self, url: str, allowed_types: set, max_size: int) -> tuple[bytes, str]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            content = response.content
            if len(content) > max_size:
                raise ValueError(f"File size {len(content)} exceeds maximum {max_size}")
            
            mime_type = magic.from_buffer(content, mime=True)
            if mime_type not in allowed_types:
                raise ValueError(f"Unsupported file type: {mime_type}. Allowed: {allowed_types}")
            
            return content, mime_type

    async def _upload_to_minio(self, content: bytes, object_name: str, content_type: str) -> str:
        try:
            minio_client.upload_bytes(object_name, content, content_type)
            return f"http://minio:9000/{minio_client.bucket}/{object_name}"
        except Exception as e:
            logger.error("minio_upload_failed", object_name=object_name, error=str(e))
            raise

    async def process(
        self,
        input_data: IntakeInput,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        trace_id: str,
    ) -> AgentResult[IntakeOutput]:
        validation_errors = []
        photo_stored = False
        audio_stored = False
        photo_object_name = None
        audio_object_name = None
        photo_url = None
        audio_url = None

        if input_data.photo_url:
            try:
                photo_object_name = f"complaints/{complaint_id}/photo"
                content, mime_type = await self._validate_and_download(
                    str(input_data.photo_url), ALLOWED_IMAGE_TYPES, MAX_FILE_SIZE
                )
                
                ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(mime_type, ".jpg")
                photo_object_name += ext
                
                photo_url = await self._upload_to_minio(content, photo_object_name, mime_type)
                photo_stored = True
                logger.info("photo_processed", complaint_id=str(complaint_id), object_name=photo_object_name, size=len(content))
            except Exception as e:
                error_msg = f"Photo processing failed: {str(e)}"
                validation_errors.append(error_msg)
                logger.warning("photo_processing_failed", complaint_id=str(complaint_id), error=str(e))

        if input_data.audio_url:
            try:
                audio_object_name = f"complaints/{complaint_id}/audio"
                content, mime_type = await self._validate_and_download(
                    str(input_data.audio_url), ALLOWED_AUDIO_TYPES, MAX_FILE_SIZE
                )
                
                ext = {
                    "audio/wav": ".wav", "audio/mp3": ".mp3", "audio/mpeg": ".mp3",
                    "audio/ogg": ".ogg", "audio/webm": ".webm", "audio/m4a": ".m4a"
                }.get(mime_type, ".wav")
                audio_object_name += ext
                
                audio_url = await self._upload_to_minio(content, audio_object_name, mime_type)
                audio_stored = True
                logger.info("audio_processed", complaint_id=str(complaint_id), object_name=audio_object_name, size=len(content))
            except Exception as e:
                error_msg = f"Audio processing failed: {str(e)}"
                validation_errors.append(error_msg)
                logger.warning("audio_processing_failed", complaint_id=str(complaint_id), error=str(e))

        output = IntakeOutput(
            complaint_id=complaint_id,
            photo_stored=photo_stored,
            audio_stored=audio_stored,
            photo_object_name=photo_object_name,
            audio_object_name=audio_object_name,
            photo_url=photo_url,
            audio_url=audio_url,
            validation_errors=validation_errors,
        )

        return AgentResult(success=True, output=output)