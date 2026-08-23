from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass, field
import uuid


class ComplaintState(TypedDict):
    # Input
    complaint_id: uuid.UUID
    text_description: Optional[str]
    photo_url: Optional[str]
    audio_url: Optional[str]
    latitude: float
    longitude: float
    address: Optional[str]
    
    # Parallel agent outputs
    vision_analysis: Optional[Dict[str, Any]]
    speech_transcript: Optional[str]
    location_details: Optional[Dict[str, Any]]
    
    # RAG context
    rag_context: Optional[Dict[str, Any]]
    rag_sources: List[Dict[str, Any]]
    
    # Decision
    decision: Optional[Dict[str, Any]]
    
    # Verification
    verification: Optional[Dict[str, Any]]
    confidence_score: Optional[float]
    
    # Human review
    requires_human_review: bool
    human_review_decision: Optional[str]
    human_review_notes: Optional[str]
    human_review_modified_data: Optional[Dict[str, Any]]
    
    # Final work order
    work_order: Optional[Dict[str, Any]]
    work_order_id: Optional[str]
    
    # Status tracking
    status: str
    errors: List[str]
    current_agent: Optional[str]
    
    # Trace
    trace_id: str


@dataclass
class PipelineContext:
    complaint_id: uuid.UUID
    trace_id: str
    db_session: Any = None
    config: Dict[str, Any] = field(default_factory=dict)