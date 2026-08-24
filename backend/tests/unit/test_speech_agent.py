import pytest
import uuid
import io
import torch
import torchaudio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.speech import SpeechAgent, SpeechInput, SpeechOutput
from app.db.models import AgentType


@pytest.fixture
def speech_agent():
    return SpeechAgent()


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def complaint_id():
    return uuid.uuid4()


@pytest.fixture
def trace_id():
    return "test-trace-123"


class TestSpeechAgent:
    @pytest.mark.asyncio
    async def test_speech_agent_no_audio(self, speech_agent, mock_db, complaint_id, trace_id):
        input_data = SpeechInput(audio_url=None, complaint_id=str(complaint_id))
        
        result = await speech_agent.execute(input_data, mock_db, complaint_id, trace_id)
        
        assert result.success is True
        assert result.output is not None
        assert result.output.transcript == ""
        assert result.output.confidence == 0.0
        assert result.output.duration_seconds == 0.0
        assert result.metadata.get("skipped") is True
        assert result.metadata.get("reason") == "no_audio"

    @pytest.mark.asyncio
    async def test_speech_agent_success(self, speech_agent, mock_db, complaint_id, trace_id):
        fake_audio_bytes = b"fake wav content for testing"
        
        with patch.object(speech_agent, '_download_audio', new_callable=AsyncMock) as mock_download, \
             patch('app.agents.speech.WhisperProcessor') as mock_processor_class, \
             patch('app.agents.speech.WhisperForConditionalGeneration') as mock_model_class, \
             patch('torchaudio.load') as mock_torchaudio_load, \
             patch('torchaudio.transforms.Resample') as mock_resample, \
             patch('torch.no_grad'), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:
            
            mock_download.return_value = fake_audio_bytes
            mock_tempfile.return_value.__enter__.return_value.name = "/tmp/test_audio.wav"
            
            waveform = torch.randn(1, 16000 * 5)
            mock_torchaudio_load.return_value = (waveform, 16000)
            mock_resample_instance = MagicMock()
            mock_resample_instance.return_value = waveform
            mock_resample.return_value = mock_resample_instance
            
            mock_processor = MagicMock()
            mock_return = MagicMock()
            mock_return.to = MagicMock(return_value=mock_return)
            mock_processor.return_value = mock_return
            mock_processor.batch_decode.return_value = ["there is a large pothole on main street near oak avenue"]
            mock_processor_class.from_pretrained.return_value = mock_processor
            
            mock_model = MagicMock()
            mock_generate_result = MagicMock()
            mock_generate_result.sequences = torch.tensor([[1, 2, 3, 4, 5]])
            mock_model.generate.return_value = mock_generate_result
            mock_model.eval.return_value = None
            mock_model.to.return_value = mock_model
            mock_model_class.from_pretrained.return_value = mock_model
            
            speech_agent._processor = mock_processor
            speech_agent._model = mock_model
            
            input_data = SpeechInput(
                audio_url="https://example.com/audio.wav",
                complaint_id=str(complaint_id)
            )
            
            result = await speech_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output is not None
            assert "pothole" in result.output.transcript.lower()
            assert result.output.confidence > 0.5
            assert "pothole" in result.output.key_phrases
            assert result.output.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_speech_agent_download_failure(self, speech_agent, mock_db, complaint_id, trace_id):
        import httpx
        
        with patch.object(speech_agent, '_download_audio', new_callable=AsyncMock) as mock_download, \
             patch.object(speech_agent, '_load_model', new_callable=AsyncMock) as mock_load:
            mock_download.side_effect = httpx.HTTPError("Connection failed")
            
            input_data = SpeechInput(
                audio_url="https://example.com/audio.wav",
                complaint_id=str(complaint_id)
            )
            
            result = await speech_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is False
            assert "download" in result.error.lower()
            assert result.metadata.get("error_type") == "download_error"

    @pytest.mark.asyncio
    async def test_speech_agent_inference_failure(self, speech_agent, mock_db, complaint_id, trace_id):
        audio_bytes = b"fake audio data"
        
        with patch.object(speech_agent, '_download_audio', new_callable=AsyncMock) as mock_download, \
             patch.object(speech_agent, '_load_model', new_callable=AsyncMock) as mock_load, \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:
            
            mock_download.return_value = audio_bytes
            mock_tempfile.return_value.__enter__.return_value.name = "/tmp/test_audio.wav"
            mock_load.side_effect = Exception("Model load failed")
            
            input_data = SpeechInput(
                audio_url="https://example.com/audio.wav",
                complaint_id=str(complaint_id)
            )
            
            result = await speech_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is False
            assert "inference" in result.error.lower()
            assert result.metadata.get("error_type") == "inference_error"

    def test_extract_key_phrases(self, speech_agent):
        transcript = "There is a large pothole on Main Street near the intersection with Oak Avenue. It's causing damage to cars."
        phrases = speech_agent._extract_key_phrases(transcript)
        
        assert "pothole" in phrases
        assert "street" in phrases
        assert "avenue" in phrases
        assert "damage" in phrases
        assert "car" in phrases

    def test_estimate_confidence_short_transcript(self, speech_agent):
        confidence = speech_agent._estimate_confidence("hi", "en")
        assert confidence == 0.0

    def test_estimate_confidence_medium_transcript(self, speech_agent):
        confidence = speech_agent._estimate_confidence("there is a pothole", "en")
        assert confidence == 0.6

    def test_estimate_confidence_long_transcript(self, speech_agent):
        confidence = speech_agent._estimate_confidence("there is a large pothole on main street near oak avenue causing damage to cars", "en")
        assert confidence == 0.9

    def test_estimate_confidence_non_english(self, speech_agent):
        confidence = speech_agent._estimate_confidence("hay un bache grande en la calle", "es")
        assert confidence == 0.7