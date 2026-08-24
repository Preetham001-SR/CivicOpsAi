import enum
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, DateTime, Enum, ForeignKey, Index, Float, JSON, ARRAY, TypeDecorator
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.session import Base


class VectorArray(TypeDecorator):
    impl = Vector
    cache_ok = True
    
    def __init__(self, dim: int = 384):
        super().__init__()
        self.impl = Vector(dim)
    
    def process_bind_param(self, value: Optional[List[float]], dialect) -> Optional[List[float]]:
        if value is None:
            return None
        return value
    
    def process_result_value(self, value: Optional[List[float]], dialect) -> Optional[List[float]]:
        if value is None:
            return None
        return list(value) if value else None


class ComplaintStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class ComplaintCategory(str, enum.Enum):
    POTHOLE = "pothole"
    BROKEN_SIGN = "broken_sign"
    DAMAGED_PROPERTY = "damaged_property"
    GRAFFITI = "graffiti"
    STREETLIGHT_OUTAGE = "streetlight_outage"
    SIDEWALK_DAMAGE = "sidewalk_damage"
    TRAFFIC_SIGNAL = "traffic_signal"
    DRAINAGE_ISSUE = "drainage_issue"
    OTHER = "other"


class PriorityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentType(str, enum.Enum):
    INTAKE = "intake"
    VISION = "vision"
    SPEECH = "speech"
    LOCATION = "location"
    RAG = "rag"
    DECISION = "decision"
    VERIFICATION = "verification"
    HUMAN_REVIEW = "human_review"


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[ComplaintStatus] = mapped_column(Enum(ComplaintStatus), default=ComplaintStatus.PENDING, nullable=False)
    category: Mapped[Optional[ComplaintCategory]] = mapped_column(Enum(ComplaintCategory), nullable=True)
    priority: Mapped[Optional[PriorityLevel]] = mapped_column(Enum(PriorityLevel), nullable=True)
    
    text_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    vision_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    speech_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    rag_context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    decision: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    verification: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    work_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    work_order_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    agent_logs: Mapped[List["AgentLog"]] = relationship("AgentLog", back_populates="complaint", cascade="all, delete-orphan")
    human_reviews: Mapped[List["HumanReview"]] = relationship("HumanReview", back_populates="complaint", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_complaints_location", "latitude", "longitude"),
        Index("ix_complaints_status", "status"),
        Index("ix_complaints_created_at", "created_at"),
    )


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trace_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    span_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    complaint: Mapped["Complaint"] = relationship("Complaint", back_populates="agent_logs")
    
    __table_args__ = (
        Index("ix_agent_logs_complaint_id", "complaint_id"),
        Index("ix_agent_logs_agent_type", "agent_type"),
    )


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modified_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    complaint: Mapped["Complaint"] = relationship("Complaint", back_populates="human_reviews")
    
    __table_args__ = (
        Index("ix_human_reviews_complaint_id", "complaint_id"),
    )


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[List[float]] = mapped_column(VectorArray(384), nullable=False)
    doc_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[Optional[ComplaintCategory]] = mapped_column(Enum(ComplaintCategory, name="complaint_category", create_type=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("ix_rag_documents_category", "category"),
        Index("ix_rag_documents_source", "source"),
    )


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    work_order_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ComplaintCategory] = mapped_column(Enum(ComplaintCategory), nullable=False)
    priority: Mapped[PriorityLevel] = mapped_column(Enum(PriorityLevel), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    assigned_department: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_duration_days: Mapped[Optional[int]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_work_orders_complaint_id", "complaint_id"),
        Index("ix_work_orders_status", "status"),
    )