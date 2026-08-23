from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import uuid
import structlog

from app.agents.state import ComplaintState, PipelineContext
from app.agents.intake import IntakeAgent, IntakeInput
from app.agents.vision import VisionAgent, VisionInput
from app.agents.speech import SpeechAgent, SpeechInput
from app.agents.location import LocationAgent, LocationInput
from app.agents.rag import RagAgent, RagInput
from app.agents.decision import DecisionAgent, DecisionInput
from app.agents.verification import VerificationAgent, VerificationInput
from app.agents.work_order import WorkOrderAgent, WorkOrderInput
from app.db.session import AsyncSessionLocal
from app.core.observability import get_tracer

logger = structlog.get_logger()
tracer = get_tracer(__name__)


class CivicOpsPipeline:
    def __init__(self):
        self.intake_agent = IntakeAgent()
        self.vision_agent = VisionAgent()
        self.speech_agent = SpeechAgent()
        self.location_agent = LocationAgent()
        self.rag_agent = RagAgent()
        self.decision_agent = DecisionAgent()
        self.verification_agent = VerificationAgent()
        self.work_order_agent = WorkOrderAgent()
        
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ComplaintState)
        
        # Add nodes
        workflow.add_node("intake_agent", self._intake_node)
        workflow.add_node("vision_agent", self._vision_node)
        workflow.add_node("speech_agent", self._speech_node)
        workflow.add_node("location_agent", self._location_node)
        workflow.add_node("rag_agent", self._rag_node)
        workflow.add_node("decision_agent", self._decision_node)
        workflow.add_node("verification_agent", self._verification_node)
        workflow.add_node("human_review_agent", self._human_review_node)
        workflow.add_node("work_order_agent", self._work_order_node)
        
        # Define edges - parallel execution for vision, speech, location
        workflow.set_entry_point("intake_agent")
        
        # Pipeline execution: intake -> vision -> speech -> location -> rag -> decision -> verification
        workflow.add_edge("intake_agent", "vision_agent")
        workflow.add_edge("vision_agent", "speech_agent")
        workflow.add_edge("speech_agent", "location_agent")
        workflow.add_edge("location_agent", "rag_agent")
        workflow.add_edge("rag_agent", "decision_agent")
        workflow.add_edge("decision_agent", "verification_agent")
        
        # Conditional: human review or work order
        workflow.add_conditional_edges(
            "verification_agent",
            self._should_human_review,
            {
                "human_review": "human_review_agent",
                "work_order": "work_order_agent",
            }
        )
        
        workflow.add_edge("human_review_agent", "work_order_agent")
        workflow.add_edge("work_order_agent", END)
        
        return workflow.compile(checkpointer=MemorySaver())
    
    async def _get_db_session(self):
        async with AsyncSessionLocal() as session:
            return session
    
    async def _intake_node(self, state: ComplaintState) -> ComplaintState:
        with tracer.start_as_current_span("pipeline.intake") as span:
            span.set_attribute("complaint_id", str(state["complaint_id"]))
            
            async with AsyncSessionLocal() as db:
                input_data = IntakeInput(
                    text_description=state.get("text_description"),
                    photo_url=state.get("photo_url"),
                    audio_url=state.get("audio_url"),
                    latitude=state["latitude"],
                    longitude=state["longitude"],
                    address=state.get("address"),
                )
                
                result = await self.intake_agent.execute(
                    input_data, db, state["complaint_id"], state["trace_id"]
                )
                
                if not result.success:
                    state["errors"].append(f"Intake: {result.error}")
                    state["status"] = "failed"
                    return state
                
                # Update state with stored file info
                if result.output:
                    state["photo_url"] = result.output.photo_object_name or state.get("photo_url")
                    state["audio_url"] = result.output.audio_object_name or state.get("audio_url")
                
                state["status"] = "processing"
                state["current_agent"] = "intake"
                await db.commit()
                
                return state
    
    async def _vision_node(self, state: ComplaintState) -> ComplaintState:
        with tracer.start_as_current_span("pipeline.vision") as span:
            span.set_attribute("complaint_id", str(state["complaint_id"]))
            
            async with AsyncSessionLocal() as db:
                input_data = VisionInput(
                    photo_url=state.get("photo_url"),
                    complaint_id=str(state["complaint_id"]),
                )
                
                result = await self.vision_agent.execute(
                    input_data, db, state["complaint_id"], state["trace_id"]
                )
                
                if result.success and result.output:
                    state["vision_analysis"] = result.output.model_dump()
                else:
                    state["errors"].append(f"Vision: {result.error}")
                
                state["current_agent"] = "vision"
                await db.commit()
                
                return state
    
    async def _speech_node(self, state: ComplaintState) -> ComplaintState:
        with tracer.start_as_current_span("pipeline.speech") as span:
            span.set_attribute("complaint_id", str(state["complaint_id"]))
            
            async with AsyncSessionLocal() as db:
                input_data = SpeechInput(
                    audio_url=state.get("audio_url"),
                    complaint_id=str(state["complaint_id"]),
                )
                
                result = await self.speech_agent.execute(
                    input_data, db, state["complaint_id"], state["trace_id"]
                )
                
                if result.success and result.output:
                    state["speech_transcript"] = result.output.transcript
                else:
                    state["errors"].append(f"Speech: {result.error}")
                
                state["current_agent"] = "speech"
                await db.commit()
                
                return state
    
    async def _location_node(self, state: ComplaintState) -> ComplaintState:
        with tracer.start_as_current_span("pipeline.location") as span:
            span.set_attribute("complaint_id", str(state["complaint_id"]))
            
            async with AsyncSessionLocal() as db:
                input_data = LocationInput(
                    latitude=state["latitude"],
                    longitude=state["longitude"],
                    address=state.get("address"),
                    complaint_id=str(state["complaint_id"]),
                )
                
                result = await self.location_agent.execute(
                    input_data, db, state["complaint_id"], state["trace_id"]
                )
                
                if result.success and result.output:
                    state["location_details"] = result.output.model_dump()
                else:
                    state["errors"].append(f"Location: {result.error}")
                
                state["current_agent"] = "location"
                await db.commit()
                
                return state
    
    async def _rag_node(self, state: ComplaintState) -> ComplaintState:
        with tracer.start_as_current_span("pipeline.rag") as span:
            span.set_attribute("complaint_id", str(state["complaint_id"]))
            
            # Determine category from vision
            category = None
            if state.get("vision_analysis"):
                cat_str = state["vision_analysis"].get("recommended_category")
                if cat_str:
                    from app.db.models import ComplaintCategory
                    try:
                        category = ComplaintCategory(cat_str)
                    except ValueError:
                        pass
            
            async with AsyncSessionLocal() as db:
                input_data = RagInput(
                    category=category,
                    text_description=state.get("text_description"),
                    vision_analysis=state.get("vision_analysis"),
                    speech_transcript=state.get("speech_transcript"),
                    location_details=state.get("location_details"),
                    complaint_id=str(state["complaint_id"]),
                )
                
                result = await self.rag_agent.execute(
                    input_data, db, state["complaint_id"], state["trace_id"]
                )
                
                if result.success and result.output:
                    state["rag_context"] = result.output.model_dump()
                    state["rag_sources"] = [
                        {"type": "rule", **s.model_dump()} for s in result.output.relevant_rules
                    ] + [
                        {"type": "incident", **s.model_dump()} for s in result.output.relevant_incidents
                    ]
                else:
                    state["errors"].append(f"RAG: {result.error}")
                
                state["current_agent"] = "rag"
                await db.commit()
                
                return state
    
    async def _decision_node(self, state: ComplaintState) -> ComplaintState:
        with tracer.start_as_current_span("pipeline.decision") as span:
            span.set_attribute("complaint_id", str(state["complaint_id"]))
            
            # Determine category from vision
            category = None
            if state.get("vision_analysis"):
                cat_str = state["vision_analysis"].get("recommended_category")
                if cat_str:
                    from app.db.models import ComplaintCategory
                    try:
                        category = ComplaintCategory(cat_str)
                    except ValueError:
                        pass
            
            async with AsyncSessionLocal() as db:
                input_data = DecisionInput(
                    category=category,
                    vision_analysis=state.get("vision_analysis"),
                    speech_transcript=state.get("speech_transcript"),
                    location_details=state.get("location_details"),
                    rag_context=state.get("rag_context"),
                    complaint_id=str(state["complaint_id"]),
                )
                
                result = await self.decision_agent.execute(
                    input_data, db, state["complaint_id"], state["trace_id"]
                )
                
                if result.success and result.output:
                    state["decision"] = result.output.model_dump()
                else:
                    state["errors"].append(f"Decision: {result.error}")
                
                state["current_agent"] = "decision"
                await db.commit()
                
                return state
    
    async def _verification_node(self, state: ComplaintState) -> ComplaintState:
        with tracer.start_as_current_span("pipeline.verification") as span:
            span.set_attribute("complaint_id", str(state["complaint_id"]))
            
            # Determine category and priority from decision
            category = None
            priority = None
            if state.get("decision"):
                from app.db.models import ComplaintCategory, PriorityLevel
                try:
                    category = ComplaintCategory(state["decision"].get("category"))
                    priority = PriorityLevel(state["decision"].get("priority"))
                except ValueError:
                    pass
            
            async with AsyncSessionLocal() as db:
                input_data = VerificationInput(
                    category=category,
                    priority=priority,
                    vision_analysis=state.get("vision_analysis"),
                    speech_transcript=state.get("speech_transcript"),
                    location_details=state.get("location_details"),
                    rag_context=state.get("rag_context"),
                    decision=state.get("decision"),
                    complaint_id=str(state["complaint_id"]),
                )
                
                result = await self.verification_agent.execute(
                    input_data, db, state["complaint_id"], state["trace_id"]
                )
                
                if result.success and result.output:
                    state["verification"] = result.output.model_dump()
                    state["confidence_score"] = result.output.overall_confidence
                    state["requires_human_review"] = result.output.requires_human_review
                else:
                    state["errors"].append(f"Verification: {result.error}")
                    state["requires_human_review"] = True
                
                state["current_agent"] = "verification"
                await db.commit()
                
                return state
    
    def _should_human_review(self, state: ComplaintState) -> str:
        if state.get("requires_human_review", False):
            return "human_review"
        return "work_order"
    
    async def _human_review_node(self, state: ComplaintState) -> ComplaintState:
        with tracer.start_as_current_span("pipeline.human_review") as span:
            span.set_attribute("complaint_id", str(state["complaint_id"]))
            
            # In production, this would wait for human input via API
            # For now, auto-approve with logging
            logger.warning(
                "human_review_required_auto_approve",
                complaint_id=str(state["complaint_id"]),
                confidence=state.get("confidence_score"),
                reason=state.get("verification", {}).get("review_reason"),
            )
            
            state["human_review_decision"] = "approve"
            state["human_review_notes"] = "Auto-approved for development"
            state["status"] = "awaiting_review"
            
            return state
    
    async def _work_order_node(self, state: ComplaintState) -> ComplaintState:
        with tracer.start_as_current_span("pipeline.work_order") as span:
            span.set_attribute("complaint_id", str(state["complaint_id"]))
            
            # Determine category and priority
            category = None
            priority = None
            if state.get("decision"):
                from app.db.models import ComplaintCategory, PriorityLevel
                try:
                    category = ComplaintCategory(state["decision"].get("category"))
                    priority = PriorityLevel(state["decision"].get("priority"))
                except ValueError:
                    pass
            
            if not category or not priority:
                state["errors"].append("WorkOrder: Missing category or priority")
                state["status"] = "failed"
                return state
            
            async with AsyncSessionLocal() as db:
                input_data = WorkOrderInput(
                    complaint_id=str(state["complaint_id"]),
                    category=category,
                    priority=priority,
                    latitude=state["latitude"],
                    longitude=state["longitude"],
                    address=state.get("address"),
                    vision_analysis=state.get("vision_analysis"),
                    speech_transcript=state.get("speech_transcript"),
                    location_details=state.get("location_details"),
                    decision=state.get("decision"),
                    verification=state.get("verification"),
                    human_review_modified_data=state.get("human_review_modified_data"),
                )
                
                result = await self.work_order_agent.execute(
                    input_data, db, state["complaint_id"], state["trace_id"]
                )
                
                if result.success and result.output:
                    state["work_order"] = result.output.model_dump()
                    state["work_order_id"] = result.output.work_order_id
                    state["status"] = "completed"
                else:
                    state["errors"].append(f"WorkOrder: {result.error}")
                    state["status"] = "failed"
                
                state["current_agent"] = "work_order"
                await db.commit()
                
                return state
    
    async def run(self, initial_state: ComplaintState) -> ComplaintState:
        config = {"configurable": {"thread_id": str(initial_state["complaint_id"])}}
        
        final_state = await self.graph.ainvoke(initial_state, config=config)
        
        # Update complaint record with final state
        async with AsyncSessionLocal() as db:
            from app.db.models import Complaint, ComplaintStatus
            from sqlalchemy import select
            
            result = await db.execute(
                select(Complaint).where(Complaint.id == initial_state["complaint_id"])
            )
            complaint = result.scalar_one_or_none()
            
            if complaint:
                complaint.status = ComplaintStatus(final_state.get("status", "failed"))
                complaint.vision_analysis = final_state.get("vision_analysis")
                complaint.speech_transcript = final_state.get("speech_transcript")
                complaint.location_details = final_state.get("location_details")
                complaint.rag_context = final_state.get("rag_context")
                complaint.decision = final_state.get("decision")
                complaint.verification = final_state.get("verification")
                complaint.confidence_score = final_state.get("confidence_score")
                complaint.work_order_id = final_state.get("work_order_id")
                complaint.work_order_data = final_state.get("work_order")
                
                if final_state.get("status") == "completed":
                    from datetime import datetime
                    complaint.completed_at = datetime.utcnow()
                
                await db.commit()
        
        return final_state


pipeline = CivicOpsPipeline()