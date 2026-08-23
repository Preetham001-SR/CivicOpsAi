from typing import Dict, Any, Optional, List
import uuid
from pydantic import BaseModel
from app.agents.base import BaseAgent, AgentResult
from app.agents.state import ComplaintState
from app.db.models import AgentType, ComplaintCategory, PriorityLevel
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class DecisionInput(BaseModel):
    category: Optional[ComplaintCategory] = None
    vision_analysis: Optional[Dict[str, Any]] = None
    speech_transcript: Optional[str] = None
    location_details: Optional[Dict[str, Any]] = None
    rag_context: Optional[Dict[str, Any]] = None
    complaint_id: str


class DecisionOutput(BaseModel):
    category: ComplaintCategory
    priority: PriorityLevel
    recommended_action: str
    assigned_department: str
    estimated_cost: Optional[float] = None
    estimated_duration_days: Optional[int] = None
    reasoning: str
    confidence: float


DECISION_PROMPT = ChatPromptTemplate.from_template("""
You are a municipal infrastructure decision agent. Analyze the citizen complaint and make a classification decision.

COMPLAINT DATA:
- Text description: {text_description}
- Vision analysis: {vision_analysis}
- Speech transcript: {speech_transcript}
- Location: {location_details}
- RAG context (city rules & past incidents): {rag_context}

CATEGORIES: pothole, broken_sign, damaged_property, graffiti, streetlight_outage, sidewalk_damage, traffic_signal, drainage_issue, other
PRIORITIES: low, medium, high, critical

DECISION RULES:
- Critical: Immediate safety hazard, major arterial road, near school/hospital, sinkhole risk
- High: Significant damage, high traffic area, recurring issue
- Medium: Standard repair needed, moderate traffic
- Low: Cosmetic, low traffic, non-urgent

Respond with a JSON object matching this schema:
{format_instructions}
""")


class DecisionAgent(BaseAgent[DecisionInput, DecisionOutput]):
    def __init__(self):
        super().__init__(AgentType.DECISION)
        self.llm = ChatNVIDIA(
            model=settings.NVIDIA_MODEL,
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=0.1,
            max_tokens=1024,
        )
        self.parser = PydanticOutputParser(pydantic_object=DecisionOutput)
        self.chain = DECISION_PROMPT | self.llm | self.parser

    async def process(
        self,
        input_data: DecisionInput,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        trace_id: str,
    ) -> AgentResult[DecisionOutput]:
        try:
            rag_synthesis = input_data.rag_context.get("synthesis", "") if input_data.rag_context else ""
            rag_sources = input_data.rag_context.get("relevant_rules", []) if input_data.rag_context else []
            
            result = await self.chain.ainvoke({
                "text_description": input_data.text_description or "No text provided",
                "vision_analysis": str(input_data.vision_analysis) if input_data.vision_analysis else "No image",
                "speech_transcript": input_data.speech_transcript or "No audio",
                "location_details": str(input_data.location_details) if input_data.location_details else "No location details",
                "rag_context": f"Synthesis: {rag_synthesis}\nSources: {rag_sources}",
                "format_instructions": self.parser.get_format_instructions(),
            })
            
            return AgentResult(success=True, output=result)
            
        except Exception as e:
            logger.error("decision_llm_failed", error=str(e), complaint_id=str(complaint_id))
            # Fallback to rule-based decision
            category = input_data.category or ComplaintCategory.POTHOLE
            priority = PriorityLevel.HIGH
            if "critical" in rag_synthesis.lower() or "24-hour" in rag_synthesis.lower():
                priority = PriorityLevel.CRITICAL
            
            output = DecisionOutput(
                category=category,
                priority=priority,
                recommended_action=f"Repair {category.value} per municipal standards. Schedule based on priority.",
                assigned_department="Public Works - Street Maintenance",
                estimated_cost=2500.0,
                estimated_duration_days=2,
                reasoning=f"LLM failed, using fallback. Vision: {category.value}. RAG: {rag_synthesis[:200]}",
                confidence=0.6,
            )
            return AgentResult(success=True, output=output, metadata={"fallback": True})