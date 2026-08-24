from typing import Dict, Any, Optional, List
import uuid
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentResult
from app.db.models import AgentType, ComplaintCategory
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.core.config import settings
import structlog

from app.rag.retrieval import Retriever, RetrievalConfig, RetrievalResult
from app.rag.reranking import Reranker, RerankConfig, combine_and_rerank

logger = structlog.get_logger()


class RagInput(BaseModel):
    category: Optional[ComplaintCategory] = None
    text_description: Optional[str] = None
    vision_analysis: Optional[Dict[str, Any]] = None
    speech_transcript: Optional[str] = None
    location_details: Optional[Dict[str, Any]] = None
    complaint_id: str


class CitedSource(BaseModel):
    id: str
    title: str
    content: str
    source: str
    category: Optional[str]
    similarity_score: float
    citation_id: str


class RagOutput(BaseModel):
    relevant_rules: List[CitedSource]
    relevant_incidents: List[CitedSource]
    synthesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    citations: List[Dict[str, Any]] = Field(default_factory=list)


RAG_PROMPT = ChatPromptTemplate.from_template("""
You are a municipal policy analyst. Synthesize relevant city rules and past incidents for a citizen complaint.

COMPLAINT:
- Category: {category}
- Description: {text_description}
- Vision Analysis: {vision_analysis}
- Speech Transcript: {speech_transcript}
- Location Details: {location_details}

RELEVANT CITY RULES & REGULATIONS:
{rules}

RELEVANT PAST INCIDENTS:
{incidents}

SYNTHESIS REQUIREMENTS:
1. Cite specific code sections or policy documents using [CITATION_ID] format
2. Reference similar past incidents with their outcomes
3. State clear priority recommendation with reasoning
4. Note any jurisdictional considerations
5. Include confidence in your assessment (0-1)

For citations, use the citation_id from the source documents.

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
            max_tokens=2048,
        )
        self.parser = PydanticOutputParser(pydantic_object=RagOutput)
        self.chain = RAG_PROMPT | self.llm | self.parser
        self.retriever = Retriever()
        self.reranker = Reranker()

    def _build_query(self, input_data: RagInput) -> str:
        parts = []
        
        if input_data.text_description:
            parts.append(f"Description: {input_data.text_description}")
        
        if input_data.vision_analysis:
            vision = input_data.vision_analysis
            if isinstance(vision, dict):
                if vision.get("caption"):
                    parts.append(f"Visual: {vision['caption']}")
                if vision.get("damage_assessment"):
                    parts.append(f"Damage: {vision['damage_assessment']}")
                if vision.get("recommended_category"):
                    parts.append(f"Category: {vision['recommended_category']}")
        
        if input_data.speech_transcript:
            parts.append(f"Audio: {input_data.speech_transcript}")
        
        if input_data.location_details:
            loc = input_data.location_details
            if isinstance(loc, dict):
                if loc.get("formatted_address"):
                    parts.append(f"Location: {loc['formatted_address']}")
                if loc.get("nearest_intersection"):
                    parts.append(f"Intersection: {loc['nearest_intersection']}")
        
        if input_data.category:
            parts.append(f"Category: {input_data.category.value}")
        
        return " | ".join(parts)

    def _format_sources_for_llm(
        self, 
        sources: List[RetrievalResult], 
        source_type: str
    ) -> str:
        if not sources:
            return f"No {source_type} found."
        
        lines = []
        for result in sources:
            doc = result.document
            citation_id = f"[{source_type.upper()[:3]}-{result.rank}]"
            
            meta = doc.doc_metadata or {}
            section = meta.get("section", "")
            page = meta.get("page", "")
            
            location_info = ""
            if section:
                location_info += f" Section: {section}"
            if page:
                location_info += f" Page: {page}"
            
            lines.append(
                f"{citation_id} {doc.title} ({doc.source}){location_info}: "
                f"{doc.content[:500]}... [Similarity: {result.similarity_score:.2f}]"
            )
        
        return "\n".join(lines)

    def _create_cited_sources(self, results: List[RetrievalResult], prefix: str) -> List[CitedSource]:
        cited = []
        for result in results:
            doc = result.document
            citation_id = f"[{prefix}-{result.rank}]"
            
            cited.append(CitedSource(
                id=str(doc.id),
                title=doc.title,
                content=doc.content,
                source=doc.source,
                category=doc.category.value if doc.category else None,
                similarity_score=result.similarity_score,
                citation_id=citation_id,
            ))
        return cited

    async def process(
        self,
        input_data: RagInput,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        trace_id: str,
    ) -> AgentResult[RagOutput]:
        try:
            query = self._build_query(input_data)
            logger.info("rag_query_built", complaint_id=str(complaint_id), query=query[:200])
            
            rules_results, incidents_results = await self.retriever.hybrid_retrieve(
                query=query,
                db=db,
                category=input_data.category,
                rules_top_k=10,
                incidents_top_k=10,
            )
            
            rules_results, incidents_results = combine_and_rerank(
                rules_results,
                incidents_results,
                query,
            )
            
            rules_results = rules_results[:5]
            incidents_results = incidents_results[:5]
            
            if not rules_results and not incidents_results:
                return AgentResult(
                    success=True,
                    output=RagOutput(
                        relevant_rules=[],
                        relevant_incidents=[],
                        synthesis="No relevant city rules or past incidents found in database for this complaint.",
                        confidence=0.2,
                        citations=[],
                    )
                )
            
            rules_text = self._format_sources_for_llm(rules_results, "rule")
            incidents_text = self._format_sources_for_llm(incidents_results, "incident")
            
            result = await self.chain.ainvoke({
                "category": input_data.category.value if input_data.category else "unknown",
                "text_description": input_data.text_description or "None",
                "vision_analysis": str(input_data.vision_analysis) if input_data.vision_analysis else "None",
                "speech_transcript": input_data.speech_transcript or "None",
                "location_details": str(input_data.location_details) if input_data.location_details else "None",
                "rules": rules_text,
                "incidents": incidents_text,
                "format_instructions": self.parser.get_format_instructions(),
            })
            
            result.relevant_rules = self._create_cited_sources(rules_results, "RUL")
            result.relevant_incidents = self._create_cited_sources(incidents_results, "INC")
            
            result.citations = [
                {"id": s.citation_id, "title": s.title, "source": s.source, "score": s.similarity_score}
                for s in result.relevant_rules + result.relevant_incidents
            ]
            
            logger.info(
                "rag_completed",
                complaint_id=str(complaint_id),
                rules_count=len(result.relevant_rules),
                incidents_count=len(result.relevant_incidents),
                confidence=result.confidence,
            )
            
            return AgentResult(success=True, output=result)
            
        except Exception as e:
            logger.error("rag_llm_failed", error=str(e), complaint_id=str(complaint_id))
            
            query = self._build_query(input_data)
            rules_results, incidents_results = await self.retriever.hybrid_retrieve(
                query=query,
                db=db,
                category=input_data.category,
            )
            rules_results, incidents_results = combine_and_rerank(rules_results, incidents_results, query)
            
            synthesis = self._fallback_synthesis(rules_results, incidents_results, input_data)
            
            output = RagOutput(
                relevant_rules=self._create_cited_sources(rules_results[:5], "RUL"),
                relevant_incidents=self._create_cited_sources(incidents_results[:5], "INC"),
                synthesis=synthesis,
                confidence=0.5,
                citations=[
                    {"id": s.citation_id, "title": s.title, "source": s.source, "score": s.similarity_score}
                    for s in self._create_cited_sources(rules_results[:5], "RUL") + self._create_cited_sources(incidents_results[:5], "INC")
                ],
            )
            return AgentResult(success=True, output=output, metadata={"fallback": True})

    def _fallback_synthesis(
        self,
        rules: List[RetrievalResult],
        incidents: List[RetrievalResult],
        input_data: RagInput,
    ) -> str:
        parts = []
        
        if rules:
            parts.append("Relevant rules:")
            for r in rules[:3]:
                citation = f"[RUL-{r.rank}]"
                parts.append(f"  {citation} {r.document.title}: {r.document.content[:300]}...")
        
        if incidents:
            parts.append("Past incidents:")
            for i in incidents[:3]:
                citation = f"[INC-{i.rank}]"
                parts.append(f"  {citation} {i.document.title}: {i.document.content[:300]}...")
        
        if not parts:
            parts.append("No relevant documents found in database.")
        
        cat = input_data.category.value if input_data.category else "issue"
        parts.append(f"\nRecommendation: Process as {cat} per standard municipal procedures.")
        
        return "\n".join(parts)