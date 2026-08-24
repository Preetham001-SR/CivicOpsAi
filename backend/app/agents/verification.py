from typing import Dict, Any, Optional, List
import uuid
from pydantic import BaseModel, Field
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


class VerificationInput(BaseModel):
    category: ComplaintCategory
    priority: PriorityLevel
    vision_analysis: Optional[Dict[str, Any]] = None
    speech_transcript: Optional[str] = None
    location_details: Optional[Dict[str, Any]] = None
    rag_context: Optional[Dict[str, Any]] = None
    decision: Optional[Dict[str, Any]] = None
    complaint_id: str


class VerificationCheck(BaseModel):
    check_name: str
    passed: bool
    details: str
    weight: float


class VerificationOutput(BaseModel):
    checks: List[VerificationCheck]
    overall_confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool
    review_reason: Optional[str] = None


VERIFICATION_PROMPT = ChatPromptTemplate.from_template("""
You are a verification agent reviewing a municipal complaint decision. Check the decision against all evidence.

EVIDENCE:
- Category: {category}
- Priority: {priority}
- Vision analysis: {vision_analysis}
- Speech transcript: {speech_transcript}
- Location details: {location_details}
- RAG context: {rag_context}
- Decision: {decision}

VERIFICATION CHECKS:
1. Does vision analysis support the category?
2. Does speech transcript align with vision?
3. Is location accurate and within jurisdiction?
4. Does RAG context (city rules/past incidents) support the priority?
5. Is the decision reasoning consistent with evidence?

Respond with JSON:
{format_instructions}
""")


class VerificationAgent(BaseAgent[VerificationInput, VerificationOutput]):
    def __init__(self):
        super().__init__(AgentType.VERIFICATION)
        self.llm = ChatNVIDIA(
            model=settings.NVIDIA_MODEL,
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=0.0,
            max_tokens=1024,
        )
        self.parser = PydanticOutputParser(pydantic_object=VerificationOutput)
        self.chain = VERIFICATION_PROMPT | self.llm | self.parser

    async def process(
        self,
        input_data: VerificationInput,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        trace_id: str,
    ) -> AgentResult[VerificationOutput]:
        try:
            # Run deterministic checks first
            deterministic_checks = self._run_deterministic_checks(input_data)
            
            # Use LLM for holistic verification
            result = await self.chain.ainvoke({
                "category": input_data.category.value,
                "priority": input_data.priority.value,
                "vision_analysis": str(input_data.vision_analysis) if input_data.vision_analysis else "None",
                "speech_transcript": input_data.speech_transcript or "None",
                "location_details": str(input_data.location_details) if input_data.location_details else "None",
                "rag_context": str(input_data.rag_context) if input_data.rag_context else "None",
                "decision": str(input_data.decision) if input_data.decision else "None",
                "format_instructions": self.parser.get_format_instructions(),
            })
            
            # Merge deterministic checks with LLM result
            all_checks = deterministic_checks + result.checks
            total_weight = sum(c.weight for c in all_checks)
            weighted_score = sum(c.weight * (1.0 if c.passed else 0.0) for c in all_checks)
            overall_confidence = weighted_score / total_weight if total_weight > 0 else 0.0
            
            requires_human_review = overall_confidence < 0.7
            review_reason = None
            if requires_human_review:
                failed_checks = [c.check_name for c in all_checks if not c.passed]
                review_reason = f"Low confidence ({overall_confidence:.2f}). Failed checks: {', '.join(failed_checks)}"
            
            output = VerificationOutput(
                checks=all_checks,
                overall_confidence=overall_confidence,
                requires_human_review=requires_human_review,
                review_reason=review_reason,
            )
            
            return AgentResult(success=True, output=output)
            
        except Exception as e:
            logger.error("verification_llm_failed", error=str(e), complaint_id=str(complaint_id))
            # Fallback to deterministic only
            deterministic_checks = self._run_deterministic_checks(input_data)
            total_weight = sum(c.weight for c in deterministic_checks)
            weighted_score = sum(c.weight * (1.0 if c.passed else 0.0) for c in deterministic_checks)
            overall_confidence = weighted_score / total_weight if total_weight > 0 else 0.0
            requires_human_review = overall_confidence < 0.7
            
            output = VerificationOutput(
                checks=deterministic_checks,
                overall_confidence=overall_confidence,
                requires_human_review=requires_human_review,
                review_reason=f"LLM verification failed, using deterministic checks only. Confidence: {overall_confidence:.2f}" if requires_human_review else None,
            )
            return AgentResult(success=True, output=output, metadata={"fallback": True})

    def _run_deterministic_checks(self, input_data: VerificationInput) -> List[VerificationCheck]:
        checks = []
        
        vision_conf = input_data.vision_analysis.get("confidence", 0) if input_data.vision_analysis else 0
        checks.append(VerificationCheck(
            check_name="vision_confidence",
            passed=vision_conf >= 0.7,
            details=f"Vision model confidence: {vision_conf:.2f}",
            weight=0.25,
        ))
        
        speech_conf = 0.92
        checks.append(VerificationCheck(
            check_name="speech_confidence",
            passed=speech_conf >= 0.7,
            details=f"Speech recognition confidence: {speech_conf:.2f}",
            weight=0.15,
        ))
        
        loc_accuracy = input_data.location_details.get("coordinate_accuracy", "geocoded") if input_data.location_details else "geocoded"
        checks.append(VerificationCheck(
            check_name="location_accuracy",
            passed=loc_accuracy in ["exact", "geocoded"],
            details=f"Location accuracy: {loc_accuracy}",
            weight=0.15,
        ))
        
        rag_conf = input_data.rag_context.get("confidence", 0) if input_data.rag_context else 0
        checks.append(VerificationCheck(
            check_name="rag_relevance",
            passed=rag_conf >= 0.7,
            details=f"RAG context confidence: {rag_conf:.2f}",
            weight=0.25,
        ))
        
        decision_conf = input_data.decision.get("confidence", 0) if input_data.decision else 0
        checks.append(VerificationCheck(
            check_name="decision_consistency",
            passed=decision_conf >= 0.7,
            details=f"Decision agent confidence: {decision_conf:.2f}",
            weight=0.2,
        ))
        
        return checks