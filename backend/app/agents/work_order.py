from typing import Dict, Any, Optional
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.agents.base import BaseAgent, AgentResult
from app.agents.state import ComplaintState
from app.db.models import AgentType, ComplaintCategory, PriorityLevel, WorkOrder
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()


class WorkOrderInput(BaseModel):
    complaint_id: str
    category: ComplaintCategory
    priority: PriorityLevel
    latitude: float
    longitude: float
    address: Optional[str] = None
    vision_analysis: Optional[Dict[str, Any]] = None
    speech_transcript: Optional[str] = None
    location_details: Optional[Dict[str, Any]] = None
    decision: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    human_review_modified_data: Optional[Dict[str, Any]] = None


class WorkOrderOutput(BaseModel):
    work_order_id: str
    work_order_number: str
    title: str
    description: str
    assigned_department: str
    estimated_cost: Optional[float] = None
    estimated_duration_days: Optional[int] = None


class WorkOrderAgent(BaseAgent[WorkOrderInput, WorkOrderOutput]):
    def __init__(self):
        super().__init__(AgentType.DECISION)  # Reuse decision type for logging

    async def process(
        self,
        input_data: WorkOrderInput,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        trace_id: str,
    ) -> AgentResult[WorkOrderOutput]:
        # Apply human review modifications if present
        decision = input_data.decision or {}
        if input_data.human_review_modified_data:
            decision.update(input_data.human_review_modified_data)
        
        # Generate work order number
        work_order_number = f"WO-{complaint_id.hex[:8].upper()}-{datetime.utcnow().strftime('%Y%m%d')}"
        
        # Build title and description
        category_label = input_data.category.value.replace("_", " ").title()
        title = f"{category_label} Repair - {input_data.location_details.get('nearest_intersection', 'Unknown Location') if input_data.location_details else 'Unknown Location'}"
        
        description_parts = [
            f"Category: {category_label}",
            f"Priority: {input_data.priority.value.title()}",
            f"Location: {input_data.address or f'Lat: {input_data.latitude}, Lng: {input_data.longitude}'}",
        ]
        
        if input_data.vision_analysis:
            description_parts.append(f"Vision Assessment: {input_data.vision_analysis.get('damage_assessment', 'N/A')}")
        
        if input_data.speech_transcript:
            description_parts.append(f"Citizen Report: {input_data.speech_transcript[:200]}...")
        
        if decision.get("reasoning"):
            description_parts.append(f"Decision Rationale: {decision['reasoning']}")
        
        description = "\n\n".join(description_parts)
        
        # Create work order record
        work_order = WorkOrder(
            complaint_id=complaint_id,
            work_order_number=work_order_number,
            title=title,
            description=description,
            category=input_data.category,
            priority=input_data.priority,
            latitude=input_data.latitude,
            longitude=input_data.longitude,
            address=input_data.address,
            assigned_department=decision.get("assigned_department", "Public Works"),
            estimated_cost=decision.get("estimated_cost"),
            estimated_duration_days=decision.get("estimated_duration_days"),
            status="open",
        )
        
        db.add(work_order)
        await db.flush()
        
        output = WorkOrderOutput(
            work_order_id=str(work_order.id),
            work_order_number=work_order_number,
            title=title,
            description=description,
            assigned_department=work_order.assigned_department,
            estimated_cost=work_order.estimated_cost,
            estimated_duration_days=work_order.estimated_duration_days,
        )
        
        return AgentResult(success=True, output=output)