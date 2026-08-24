from pydantic import BaseModel, Field, field_validator, HttpUrl
from typing import Optional, Literal
from datetime import datetime
import uuid


class ComplaintBase(BaseModel):
    text_description: Optional[str] = Field(default=None, max_length=5000, description="Citizen's text description of the issue")
    photo_url: Optional[HttpUrl] = Field(default=None, description="URL to uploaded photo")
    audio_url: Optional[HttpUrl] = Field(default=None, description="URL to uploaded audio recording")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude of the issue")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude of the issue")
    address: Optional[str] = Field(default=None, max_length=500, description="Human-readable address")


class ComplaintCreate(ComplaintBase):
    @field_validator('photo_url', 'audio_url', mode='before')
    @classmethod
    def validate_urls(cls, v):
        if v is not None and str(v).strip() == "":
            return None
        return v


class ComplaintUpdate(BaseModel):
    status: Optional[Literal["pending", "processing", "awaiting_review", "approved", "rejected", "completed"]] = None
    category: Optional[Literal["pothole", "broken_sign", "damaged_property", "graffiti", "streetlight_outage", "sidewalk_damage", "traffic_signal", "drainage_issue", "other"]] = None
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None
    vision_analysis: Optional[dict] = None
    speech_transcript: Optional[str] = None
    location_details: Optional[dict] = None
    rag_context: Optional[dict] = None
    decision: Optional[dict] = None
    verification: Optional[dict] = None
    confidence_score: Optional[float] = Field(default=None, ge=0, le=1)
    work_order_id: Optional[str] = None
    work_order_data: Optional[dict] = None


class ComplaintResponse(ComplaintBase):
    id: uuid.UUID
    status: Literal["pending", "processing", "awaiting_review", "approved", "rejected", "completed"]
    category: Optional[Literal["pothole", "broken_sign", "damaged_property", "graffiti", "streetlight_outage", "sidewalk_damage", "traffic_signal", "drainage_issue", "other"]] = None
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None
    vision_analysis: Optional[dict] = None
    speech_transcript: Optional[str] = None
    location_details: Optional[dict] = None
    rag_context: Optional[dict] = None
    decision: Optional[dict] = None
    verification: Optional[dict] = None
    confidence_score: Optional[float] = None
    work_order_id: Optional[str] = None
    work_order_data: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentLogResponse(BaseModel):
    id: uuid.UUID
    complaint_id: uuid.UUID
    agent_type: Literal["intake", "vision", "speech", "location", "rag", "decision", "verification", "human_review"]
    input_data: dict
    output_data: dict
    execution_time_ms: int
    error: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class HumanReviewCreate(BaseModel):
    reviewer_id: str = Field(..., min_length=1, max_length=100)
    decision: Literal["approve", "reject", "modify"] = Field(...)
    notes: Optional[str] = Field(default=None, max_length=2000)
    modified_data: Optional[dict] = None


class HumanReviewResponse(BaseModel):
    id: uuid.UUID
    complaint_id: uuid.UUID
    reviewer_id: str
    decision: Literal["approve", "reject", "modify"]
    notes: Optional[str] = None
    modified_data: Optional[dict] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkOrderCreate(BaseModel):
    complaint_id: uuid.UUID
    work_order_number: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    category: Literal["pothole", "broken_sign", "damaged_property", "graffiti", "streetlight_outage", "sidewalk_damage", "traffic_signal", "drainage_issue", "other"]
    priority: Literal["low", "medium", "high", "critical"]
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = Field(default=None, max_length=500)
    assigned_department: Optional[str] = Field(default=None, max_length=200)
    estimated_cost: Optional[float] = Field(default=None, ge=0)
    estimated_duration_days: Optional[int] = Field(default=None, ge=0)


class WorkOrderResponse(BaseModel):
    id: uuid.UUID
    complaint_id: uuid.UUID
    work_order_number: str
    title: str
    description: str
    category: Literal["pothole", "broken_sign", "damaged_property", "graffiti", "streetlight_outage", "sidewalk_damage", "traffic_signal", "drainage_issue", "other"]
    priority: Literal["low", "medium", "high", "critical"]
    latitude: float
    longitude: float
    address: Optional[str] = None
    assigned_department: Optional[str] = None
    estimated_cost: Optional[float] = None
    estimated_duration_days: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    redis: str


class ReviewQueueItem(BaseModel):
    complaint_id: uuid.UUID
    text_description: Optional[str]
    category: Optional[str]
    priority: Optional[str]
    confidence_score: Optional[float]
    review_tier: str
    latitude: float
    longitude: float
    address: Optional[str]
    created_at: datetime
    photo_url: Optional[str]
    audio_url: Optional[str]

    class Config:
        from_attributes = True


class ReviewQueueStats(BaseModel):
    total_pending: int
    mandatory_review: int
    optional_review: int
    auto_processed: int
    avg_confidence: Optional[float]

    class Config:
        from_attributes = True