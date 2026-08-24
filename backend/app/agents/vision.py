from typing import Dict, Any, Optional, List
import uuid
import io
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentResult
from app.db.models import AgentType
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import httpx
from PIL import Image
import torch

try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
except ImportError:
    BlipProcessor = None
    BlipForConditionalGeneration = None

logger = structlog.get_logger()


class VisionInput(BaseModel):
    photo_url: Optional[str] = None
    complaint_id: str


class DetectedObject(BaseModel):
    label: str
    confidence: float
    bbox: Optional[List[float]] = None


class VisionOutput(BaseModel):
    caption: str = Field(description="Natural language description of the image")
    categories: Dict[str, float] = Field(description="Category -> confidence mapping")
    detected_objects: List[DetectedObject] = Field(default_factory=list)
    damage_assessment: str = Field(description="Assessment of damage/issue severity")
    recommended_category: str = Field(description="Most likely complaint category")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence in classification")
    model_used: str = Field(description="Name of the model used for inference")


CATEGORY_KEYWORDS = {
    "pothole": ["pothole", "hole in road", "road damage", "asphalt damage", "cracked pavement", "road surface"],
    "broken_sign": ["sign", "traffic sign", "street sign", "stop sign", "signage", "fallen sign"],
    "damaged_property": ["damaged building", "broken fence", "property damage", "broken wall", "damaged property"],
    "graffiti": ["graffiti", "spray paint", "vandalism", "wall art", "tagging"],
    "streetlight_outage": ["streetlight", "street light", "lamp post", "light pole", "broken light", "dark street"],
    "sidewalk_damage": ["sidewalk", "pavement", "cracked sidewalk", "uneven pavement", "trip hazard"],
    "traffic_signal": ["traffic light", "signal light", "traffic signal", "broken traffic light"],
    "drainage_issue": ["drain", "flooding", "water pooling", "blocked drain", "standing water", "sewer"],
    "other": ["other", "unknown", "miscellaneous"],
}


class VisionAgent(BaseAgent[VisionInput, VisionOutput]):
    def __init__(self):
        super().__init__(AgentType.VISION)
        self._model = None
        self._processor = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "Salesforce/blip-image-captioning-base"

    async def _load_model(self):
        if self._model is None:
            try:
                logger.info("loading_vision_model", model=self.model_name, device=self._device)
                self._processor = BlipProcessor.from_pretrained(self.model_name)
                self._model = BlipForConditionalGeneration.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
                ).to(self._device)
                self._model.eval()
            except Exception as e:
                logger.error("vision_model_load_failed", error=str(e))
                raise

    async def _download_image(self, url: str) -> Image.Image:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content)).convert("RGB")

    def _classify_caption(self, caption: str) -> Dict[str, float]:
        caption_lower = caption.lower()
        scores = {}
        
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = 0.0
            for keyword in keywords:
                if keyword in caption_lower:
                    score += 1.0
            scores[category] = min(score / len(keywords), 1.0)
        
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        
        return scores

    def _assess_damage(self, caption: str, categories: Dict[str, float]) -> str:
        top_category = max(categories.items(), key=lambda x: x[1])[0]
        confidence = categories[top_category]
        
        severity_indicators = {
            "high": ["large", "big", "severe", "major", "huge", "extensive", "collapsed", "dangerous"],
            "medium": ["moderate", "medium", "noticeable", "significant", "cracked", "broken"],
            "low": ["small", "minor", "slight", "minimal", "hairline", "faint"],
        }
        
        caption_lower = caption.lower()
        severity = "medium"
        for level, indicators in severity_indicators.items():
            if any(ind in caption_lower for ind in indicators):
                severity = level
                break
        
        return f"{severity.title()} {top_category.replace('_', ' ')} detected: {caption}. Confidence: {confidence:.0%}"

    async def process(
        self,
        input_data: VisionInput,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        trace_id: str,
    ) -> AgentResult[VisionOutput]:
        if not input_data.photo_url:
            logger.info("vision_skipped_no_photo", complaint_id=str(complaint_id))
            return AgentResult(
                success=True,
                output=VisionOutput(
                    caption="No photo provided",
                    categories={},
                    detected_objects=[],
                    damage_assessment="No photo submitted for analysis",
                    recommended_category="other",
                    confidence=0.0,
                    model_used=self.model_name,
                ),
                metadata={"skipped": True, "reason": "no_photo"},
            )

        try:
            await self._load_model()
            
            image = await self._download_image(input_data.photo_url)
            
            inputs = self._processor(image, return_tensors="pt").to(self._device)
            
            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs,
                    max_length=50,
                    num_beams=5,
                    early_stopping=True,
                )
            
            caption = self._processor.decode(generated_ids[0], skip_special_tokens=True)
            logger.info("vision_caption_generated", complaint_id=str(complaint_id), caption=caption)
            
            categories = self._classify_caption(caption)
            recommended_category = max(categories.items(), key=lambda x: x[1])[0] if categories else "other"
            confidence = categories.get(recommended_category, 0.0)
            damage_assessment = self._assess_damage(caption, categories)
            
            detected_objects = [
                DetectedObject(label=cat, confidence=conf, bbox=None)
                for cat, conf in sorted(categories.items(), key=lambda x: x[1], reverse=True)
                if conf > 0.1
            ]
            
            output = VisionOutput(
                caption=caption,
                categories=categories,
                detected_objects=detected_objects,
                damage_assessment=damage_assessment,
                recommended_category=recommended_category,
                confidence=confidence,
                model_used=self.model_name,
            )
            
            return AgentResult(success=True, output=output)
            
        except httpx.HTTPError as e:
            logger.error("vision_image_download_failed", complaint_id=str(complaint_id), error=str(e))
            return AgentResult(
                success=False,
                error=f"Failed to download image: {str(e)}",
                metadata={"error_type": "download_error"},
            )
        except Exception as e:
            logger.error("vision_inference_failed", complaint_id=str(complaint_id), error=str(e))
            return AgentResult(
                success=False,
                error=f"Vision inference failed: {str(e)}",
                metadata={"error_type": "inference_error"},
            )