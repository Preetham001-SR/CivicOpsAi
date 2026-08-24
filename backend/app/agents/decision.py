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
    text_description: Optional[str] = None


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
- Location details: {location_details}
- Weather conditions: {weather_context}
- Nearby infrastructure: {infrastructure_context}
- RAG context (city rules & past incidents): {rag_context}

CATEGORIES: pothole, broken_sign, damaged_property, graffiti, streetlight_outage, sidewalk_damage, traffic_signal, drainage_issue, other
PRIORITIES: low, medium, high, critical

DECISION RULES:
- Critical: Immediate safety hazard, major arterial road, near school/hospital, sinkhole risk, active flooding, severe weather damage
- High: Significant damage, high traffic area, recurring issue, near school/hospital/bus stop, active precipitation with drainage issues
- Medium: Standard repair needed, moderate traffic, minor damage
- Low: Cosmetic, low traffic, non-urgent, no safety implication

WEATHER & INFRASTRUCTURE FACTORS:
- Heavy rain/storm + drainage issue = increase priority
- Active precipitation + pothole = increase priority (water infiltration worsens damage)
- Near bus stop/school/hospital = increase priority
- Near traffic signals/crossings = increase priority for traffic-related issues
- Flood risk (high/medium) = increase priority for drainage/flooding complaints
- Road type (arterial/highway) = increase priority
- Speed limit > 50 km/h = increase priority for safety issues

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

    def _build_weather_context(self, location_details: Optional[Dict[str, Any]]) -> str:
        """Build weather context string from location details"""
        if not location_details or not location_details.get("weather"):
            return "No weather data available"
            
        weather = location_details["weather"]
        parts = [
            f"Condition: {weather.get('condition', 'unknown')}",
            f"Temperature: {weather.get('temperature_celsius', 0):.1f}°C",
            f"Humidity: {weather.get('humidity_percent', 0)}%",
            f"Precipitation: {weather.get('precipitation_mm', 0)}mm",
            f"Wind: {weather.get('wind_speed_kmh', 0):.1f} km/h",
            f"Description: {weather.get('description', 'N/A')}",
        ]
        return "; ".join(parts)

    def _build_infrastructure_context(self, location_details: Optional[Dict[str, Any]]) -> str:
        """Build infrastructure context string from location details"""
        if not location_details:
            return "No infrastructure data available"
            
        parts = []
        
        # Road details
        if location_details.get("road_type"):
            parts.append(f"Road type: {location_details['road_type']}")
        if location_details.get("road_surface"):
            parts.append(f"Surface: {location_details['road_surface']}")
        if location_details.get("speed_limit"):
            parts.append(f"Speed limit: {location_details['speed_limit']} km/h")
        if location_details.get("traffic_signals_nearby"):
            parts.append("Traffic signals nearby: Yes")
        if location_details.get("bus_stops_nearby", 0) > 0:
            parts.append(f"Bus stops nearby: {location_details['bus_stops_nearby']}")
        if location_details.get("traffic_signals_nearby"):
            parts.append("Traffic signals nearby: Yes")
        if location_details.get("flood_risk"):
            parts.append(f"Flood risk: {location_details['flood_risk']}")
            
        # Nearby POIs
        nearby_pois = location_details.get("nearby_pois", [])
        if nearby_pois:
            poi_types = {}
            for poi in nearby_pois:
                poi_type = poi.get("poi_type", "unknown")
                poi_types[poi_type] = poi_types.get(poi_type, 0) + 1
            for poi_type, count in poi_types.items():
                parts.append(f"{poi_type}: {count} nearby")
                
        return "; ".join(parts) if parts else "No significant infrastructure nearby"

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
            
            weather_context = self._build_weather_context(input_data.location_details)
            infrastructure_context = self._build_infrastructure_context(input_data.location_details)
            
            result = await self.chain.ainvoke({
                "text_description": input_data.text_description or "No text provided",
                "vision_analysis": str(input_data.vision_analysis) if input_data.vision_analysis else "No image",
                "speech_transcript": input_data.speech_transcript or "No audio",
                "location_details": str(input_data.location_details) if input_data.location_details else "No location details",
                "weather_context": weather_context,
                "infrastructure_context": infrastructure_context,
                "rag_context": f"Synthesis: {rag_synthesis}\nSources: {rag_sources}",
                "format_instructions": self.parser.get_format_instructions(),
            })
            
            return AgentResult(success=True, output=result)
            
        except Exception as e:
            logger.error("decision_llm_failed", error=str(e), complaint_id=str(complaint_id))
            # Fallback to rule-based decision
            category = input_data.category or ComplaintCategory.POTHOLE
            priority = PriorityLevel.HIGH
            
            # Enhanced fallback with weather/infrastructure awareness
            location = input_data.location_details or {}
            weather = location.get("weather", {}) if location else {}
            infra = location.get("infrastructure_context", {}) if location else {}
            
            # Elevate priority based on weather
            if weather.get("precipitation_mm", 0) > 20:
                priority = PriorityLevel.CRITICAL
            elif weather.get("precipitation_mm", 0) > 10:
                priority = PriorityLevel.HIGH
            elif location.get("bus_stops_nearby", 0) > 0 or location.get("traffic_signals_nearby"):
                priority = PriorityLevel.HIGH
            elif location.get("flood_risk") in ["high", "medium"]:
                priority = PriorityLevel.CRITICAL
            elif "critical" in rag_synthesis.lower() or "24-hour" in rag_synthesis.lower():
                priority = PriorityLevel.CRITICAL
            
            output = DecisionOutput(
                category=category,
                priority=priority,
                recommended_action=f"Repair {category.value} per municipal standards. Schedule based on priority.",
                assigned_department="Public Works - Street Maintenance",
                estimated_cost=2500.0,
                estimated_duration_days=2,
                reasoning=f"LLM failed, using enhanced fallback. Category: {category.value}. Weather: {weather.get('condition', 'N/A') if isinstance(weather, dict) else 'N/A'}. Infra: {infra}. RAG: {rag_synthesis[:200]}",
                confidence=0.6,
            )
            return AgentResult(success=True, output=output, metadata={"fallback": True})