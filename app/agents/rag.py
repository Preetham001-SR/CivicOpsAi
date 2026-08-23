from typing import Dict, Any, Optional, List
import uuid
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentResult
from app.agents.state import ComplaintState
from app.db.models import AgentType, RagDocument, ComplaintCategory
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class RagInput(BaseModel):
    category: Optional[ComplaintCategory] = None
    text_description: Optional[str] = None
    vision_analysis: Optional[Dict[str, Any]] = None
    speech_transcript: Optional[str] = None
    location_details: Optional[Dict[str, Any]] = None
    complaint_id: str


class RagSource(BaseModel):
    id: str
    title: str
    content: str
    source: str
    category: Optional[str]
    relevance_score: float


class RagOutput(BaseModel):
    relevant_rules: List[RagSource]
    relevant_incidents: List[RagSource]
    synthesis: str
    confidence: float = Field(ge=0.0, le=1.0)


RAG_PROMPT = ChatPromptTemplate.from_template("""
You are a municipal policy analyst. Synthesize relevant city rules and past incidents for a citizen complaint.

COMPLAINT:
- Category: {category}
- Description: {text_description}
- Vision: {vision_analysis}
- Speech: {speech_transcript}
- Location: {location_details}

RELEVANT DOCUMENTS:
{rules}
{incidents}

SYNTHESIS REQUIREMENTS:
1. Cite specific code sections or policy documents
2. Reference similar past incidents
3. State clear priority recommendation with reasoning
4. Note any jurisdictional considerations

Respond with JSON:
{format_instructions}
""")


class RagAgent(BaseAgent[RagInput, RagOutput]):
    def __init__(self):
        super().__init__(AgentType.RAG)
        self.llm = ChatNVIDIA(
            model=settings.NVIDIA_MODEL,
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=0.1,
            max_tokens=1536,
        )
        self.parser = PydanticOutputParser(pydantic_object=RagOutput)
        self.chain = RAG_PROMPT | self.llm | self.parser

    async def process(
        self,
        input_data: RagInput,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        trace_id: str,
    ) -> AgentResult[RagOutput]:
        try:
            # Query pgvector for relevant documents
            relevant_rules, relevant_incidents = await self._retrieve_documents(db, input_data)
            
            if not relevant_rules and not relevant_incidents:
                return AgentResult(
                    success=True,
                    output=RagOutput(
                        relevant_rules=[],
                        relevant_incidents=[],
                        synthesis="No relevant city rules or past incidents found in database.",
                        confidence=0.3,
                    )
                )
            
            # Format documents for LLM
            rules_text = "\n".join([
                f"- {r.title} ({r.source}): {r.content[:300]}..." 
                for r in relevant_rules
            ])
            incidents_text = "\n".join([
                f"- {i.title} ({i.source}): {i.content[:300]}..." 
                for i in relevant_incidents
            ])
            
            # Generate synthesis via LLM
            result = await self.chain.ainvoke({
                "category": input_data.category.value if input_data.category else "unknown",
                "text_description": input_data.text_description or "None",
                "vision_analysis": str(input_data.vision_analysis) if input_data.vision_analysis else "None",
                "speech_transcript": input_data.speech_transcript or "None",
                "location_details": str(input_data.location_details) if input_data.location_details else "None",
                "rules": rules_text or "No relevant rules found",
                "incidents": incidents_text or "No relevant incidents found",
                "format_instructions": self.parser.get_format_instructions(),
            })
            
            # Attach sources to result
            result.relevant_rules = relevant_rules
            result.relevant_incidents = relevant_incidents
            
            return AgentResult(success=True, output=result)
            
        except Exception as e:
            logger.error("rag_llm_failed", error=str(e), complaint_id=str(complaint_id))
            relevant_rules, relevant_incidents = await self._retrieve_documents(db, input_data)
            
            # Fallback synthesis
            synthesis = self._fallback_synthesis(relevant_rules, relevant_incidents, input_data)
            
            output = RagOutput(
                relevant_rules=relevant_rules,
                relevant_incidents=relevant_incidents,
                synthesis=synthesis,
                confidence=0.5,
            )
            return AgentResult(success=True, output=output, metadata={"fallback": True})

    async def _retrieve_documents(
        self, 
        db: AsyncSession, 
        input_data: RagInput
    ) -> tuple[List[RagSource], List[RagSource]]:
        # Query pgvector for similar documents
        # For now, query by category since embeddings not yet implemented
        query = select(RagDocument).where(
            RagDocument.category == input_data.category
        ).limit(10) if input_data.category else select(RagDocument).limit(10)
        
        results = await db.execute(query)
        documents = results.scalars().all()
        
        rules = []
        incidents = []
        
        for doc in documents:
            source = RagSource(
                id=str(doc.id),
                title=doc.title,
                content=doc.content,
                source=doc.source,
                category=doc.category.value if doc.category else None,
                relevance_score=0.8,  # TODO: compute from vector similarity
            )
            if doc.source in ["municipal_code", "policy_document", "regulation"]:
                rules.append(source)
            else:
                incidents.append(source)
        
        return rules[:5], incidents[:5]

    def _fallback_synthesis(
        self,
        rules: List[RagSource],
        incidents: List[RagSource],
        input_data: RagInput,
    ) -> str:
        parts = []
        if rules:
            parts.append("Relevant rules:")
            for r in rules[:3]:
                parts.append(f"  - {r.title}: {r.content[:200]}")
        if incidents:
            parts.append("Past incidents:")
            for i in incidents[:3]:
                parts.append(f"  - {i.title}: {i.content[:200]}")
        if not parts:
            parts.append("No relevant documents found in database.")
        
        cat = input_data.category.value if input_data.category else "issue"
        parts.append(f"\nRecommendation: Process as {cat} per standard municipal procedures.")
        
        return "\n".join(parts)