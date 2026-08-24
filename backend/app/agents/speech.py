from typing import Dict, Any, Optional, List
import uuid
import io
import tempfile
import os
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentResult
from app.db.models import AgentType
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import httpx
import torch
import torchaudio

try:
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
except ImportError:
    WhisperProcessor = None
    WhisperForConditionalGeneration = None

logger = structlog.get_logger()


class SpeechInput(BaseModel):
    audio_url: Optional[str] = None
    complaint_id: str


class SpeechOutput(BaseModel):
    transcript: str = Field(description="Transcribed text from audio")
    language: str = Field(description="Detected language code")
    duration_seconds: float = Field(ge=0, description="Audio duration in seconds")
    confidence: float = Field(ge=0.0, le=1.0, description="Transcription confidence")
    key_phrases: List[str] = Field(default_factory=list, description="Important phrases extracted")
    model_used: str = Field(description="Name of the model used for inference")


COMPLAINT_KEYWORDS = [
    "pothole", "hole", "crack", "damage", "broken", "street", "road", "avenue", "boulevard",
    "intersection", "corner", "light", "lamp", "sign", "signal", "sidewalk", "pavement",
    "flood", "water", "drain", "sewer", "graffiti", "paint", "vandalism", "tree", "branch",
    "trash", "garbage", "debris", "noise", "construction", "repair", "fix", "maintenance",
    "dangerous", "hazard", "unsafe", "accident", "car", "vehicle", "tire", "wheel",
]


class SpeechAgent(BaseAgent[SpeechInput, SpeechOutput]):
    def __init__(self):
        super().__init__(AgentType.SPEECH)
        self._model = None
        self._processor = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "openai/whisper-base"

    async def _load_model(self):
        if self._model is None:
            try:
                logger.info("loading_speech_model", model=self.model_name, device=self._device)
                self._processor = WhisperProcessor.from_pretrained(self.model_name)
                self._model = WhisperForConditionalGeneration.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self._device == "cuda" else torch.float32,
                ).to(self._device)
                self._model.eval()
            except Exception as e:
                logger.error("speech_model_load_failed", error=str(e))
                raise

    async def _download_audio(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def _extract_key_phrases(self, transcript: str) -> List[str]:
        transcript_lower = transcript.lower()
        found = []
        for keyword in COMPLAINT_KEYWORDS:
            if keyword in transcript_lower:
                found.append(keyword)
        return list(set(found))

    def _estimate_confidence(self, transcript: str, language: str) -> float:
        if not transcript or len(transcript.strip()) < 3:
            return 0.0
        if language != "en":
            return 0.7
        word_count = len(transcript.split())
        if word_count < 5:
            return 0.6
        if word_count < 15:
            return 0.8
        return 0.9

    async def process(
        self,
        input_data: SpeechInput,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        trace_id: str,
    ) -> AgentResult[SpeechOutput]:
        if not input_data.audio_url:
            logger.info("speech_skipped_no_audio", complaint_id=str(complaint_id))
            return AgentResult(
                success=True,
                output=SpeechOutput(
                    transcript="",
                    language="en",
                    duration_seconds=0.0,
                    confidence=0.0,
                    key_phrases=[],
                    model_used=self.model_name,
                ),
                metadata={"skipped": True, "reason": "no_audio"},
            )

        try:
            await self._load_model()
            
            audio_bytes = await self._download_audio(input_data.audio_url)
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            try:
                waveform, sample_rate = torchaudio.load(tmp_path)
                duration = waveform.shape[1] / sample_rate
                
                if sample_rate != 16000:
                    resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                    waveform = resampler(waveform)
                
                if waveform.shape[0] > 1:
                    waveform = waveform.mean(dim=0, keepdim=True)
                
                inputs = self._processor(
                    waveform.squeeze().numpy(),
                    sampling_rate=16000,
                    return_tensors="pt",
                ).to(self._device)
                
                with torch.no_grad():
                    generated_ids = self._model.generate(
                        inputs.input_features,
                        max_length=448,
                        num_beams=5,
                        early_stopping=True,
                        return_dict_in_generate=True,
                        output_scores=True,
                    )
                
                transcript = self._processor.batch_decode(
                    generated_ids.sequences, skip_special_tokens=True
                )[0].strip()
                
                language = "en"
                confidence = self._estimate_confidence(transcript, language)
                key_phrases = self._extract_key_phrases(transcript)
                
                logger.info(
                    "speech_transcribed",
                    complaint_id=str(complaint_id),
                    transcript=transcript[:100],
                    language=language,
                    confidence=confidence,
                )
                
                output = SpeechOutput(
                    transcript=transcript,
                    language=language,
                    duration_seconds=duration,
                    confidence=confidence,
                    key_phrases=key_phrases,
                    model_used=self.model_name,
                )
                
                return AgentResult(success=True, output=output)
                
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except httpx.HTTPError as e:
            logger.error("speech_audio_download_failed", complaint_id=str(complaint_id), error=str(e))
            return AgentResult(
                success=False,
                error=f"Failed to download audio: {str(e)}",
                metadata={"error_type": "download_error"},
            )
        except Exception as e:
            logger.error("speech_inference_failed", complaint_id=str(complaint_id), error=str(e))
            return AgentResult(
                success=False,
                error=f"Speech inference failed: {str(e)}",
                metadata={"error_type": "inference_error"},
            )