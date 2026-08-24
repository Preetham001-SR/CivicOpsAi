import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image
import io
import torch

from app.agents.vision import VisionAgent, VisionInput, VisionOutput
from app.db.models import AgentType


@pytest.fixture
def vision_agent():
    return VisionAgent()


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def complaint_id():
    return uuid.uuid4()


@pytest.fixture
def trace_id():
    return "test-trace-123"


class TestVisionAgent:
    @pytest.mark.asyncio
    async def test_vision_agent_no_photo(self, vision_agent, mock_db, complaint_id, trace_id):
        input_data = VisionInput(photo_url=None, complaint_id=str(complaint_id))
        
        result = await vision_agent.execute(input_data, mock_db, complaint_id, trace_id)
        
        assert result.success is True
        assert result.output is not None
        assert result.output.caption == "No photo provided"
        assert result.output.confidence == 0.0
        assert result.output.recommended_category == "other"
        assert result.metadata.get("skipped") is True
        assert result.metadata.get("reason") == "no_photo"

    @pytest.mark.asyncio
    async def test_vision_agent_success(self, vision_agent, mock_db, complaint_id, trace_id):
        mock_image = Image.new("RGB", (224, 224), color="red")
        
        with patch.object(vision_agent, '_download_image', new_callable=AsyncMock) as mock_download, \
             patch('app.agents.vision.BlipProcessor') as mock_processor_class, \
             patch('app.agents.vision.BlipForConditionalGeneration') as mock_model_class, \
             patch('torch.no_grad'):
            
            mock_download.return_value = mock_image
            
            mock_processor = MagicMock()
            mock_return = MagicMock()
            mock_return.to = MagicMock(return_value=mock_return)
            mock_return.__getitem__ = MagicMock(return_value=mock_return)
            mock_processor.return_value = mock_return
            mock_processor.decode.return_value = "a large pothole in the road with cracked asphalt"
            mock_processor_class.from_pretrained.return_value = mock_processor
            
            mock_model = MagicMock()
            mock_model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
            mock_model.eval.return_value = None
            mock_model.to.return_value = mock_model
            mock_model_class.from_pretrained.return_value = mock_model
            
            vision_agent._processor = mock_processor
            vision_agent._model = mock_model
            
            input_data = VisionInput(
                photo_url="https://example.com/photo.jpg",
                complaint_id=str(complaint_id)
            )
            
            result = await vision_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output is not None
            assert "pothole" in result.output.caption.lower()
            assert result.output.confidence > 0
            assert result.output.recommended_category == "pothole"
            assert len(result.output.detected_objects) > 0

    @pytest.mark.asyncio
    async def test_vision_agent_download_failure(self, vision_agent, mock_db, complaint_id, trace_id):
        import httpx
        
        with patch.object(vision_agent, '_download_image', new_callable=AsyncMock) as mock_download, \
             patch.object(vision_agent, '_load_model', new_callable=AsyncMock) as mock_load:
            mock_download.side_effect = httpx.HTTPError("Connection failed")
            
            input_data = VisionInput(
                photo_url="https://example.com/photo.jpg",
                complaint_id=str(complaint_id)
            )
            
            result = await vision_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is False
            assert "download" in result.error.lower()
            assert result.metadata.get("error_type") == "download_error"

    @pytest.mark.asyncio
    async def test_vision_agent_inference_failure(self, vision_agent, mock_db, complaint_id, trace_id):
        mock_image = Image.new("RGB", (224, 224), color="red")
        
        with patch.object(vision_agent, '_download_image', new_callable=AsyncMock) as mock_download, \
             patch.object(vision_agent, '_load_model', new_callable=AsyncMock) as mock_load:
            
            mock_download.return_value = mock_image
            mock_load.side_effect = Exception("Model load failed")
            
            input_data = VisionInput(
                photo_url="https://example.com/photo.jpg",
                complaint_id=str(complaint_id)
            )
            
            result = await vision_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is False
            assert "inference" in result.error.lower()
            assert result.metadata.get("error_type") == "inference_error"

    def test_classify_caption_pothole(self, vision_agent):
        caption = "a large pothole in the road with cracked asphalt pavement"
        categories = vision_agent._classify_caption(caption)
        
        assert "pothole" in categories
        assert categories["pothole"] > 0.3

    def test_classify_caption_streetlight(self, vision_agent):
        caption = "a broken streetlight on a dark street at night"
        categories = vision_agent._classify_caption(caption)
        
        assert "streetlight_outage" in categories
        assert categories["streetlight_outage"] > 0.5

    def test_assess_damage_severity(self, vision_agent):
        caption = "a large severe pothole causing dangerous conditions"
        categories = {"pothole": 0.9, "other": 0.1}
        assessment = vision_agent._assess_damage(caption, categories)
        
        assert "high" in assessment.lower() or "severe" in assessment.lower()
        assert "pothole" in assessment.lower()