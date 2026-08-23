import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.pipeline import CivicOpsPipeline, ComplaintState
from app.db.models import ComplaintStatus


@pytest.fixture
def pipeline_instance():
    return CivicOpsPipeline()


@pytest.fixture
def initial_state():
    return ComplaintState(
        complaint_id=uuid.uuid4(),
        text_description="Large pothole on Main Street",
        photo_url="https://example.com/photo.jpg",
        audio_url="https://example.com/audio.wav",
        latitude=40.7128,
        longitude=-74.0060,
        address="Main St & Oak Ave, New York, NY",
        vision_analysis=None,
        speech_transcript=None,
        location_details=None,
        rag_context=None,
        rag_sources=[],
        decision=None,
        verification=None,
        confidence_score=None,
        requires_human_review=False,
        human_review_decision=None,
        human_review_notes=None,
        human_review_modified_data=None,
        work_order=None,
        work_order_id=None,
        status="pending",
        errors=[],
        current_agent=None,
        trace_id="test-trace-123",
    )


class TestCivicOpsPipeline:
    @pytest.mark.asyncio
    async def test_intake_node(self, pipeline_instance, initial_state):
        with patch('app.agents.pipeline.AsyncSessionLocal') as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db
            mock_db.commit = AsyncMock()
            mock_db.flush = AsyncMock()
            
            result_state = await pipeline_instance._intake_node(initial_state)
            
            assert result_state["status"] == "processing"
            assert result_state["current_agent"] == "intake"
            assert result_state["photo_url"] is not None
            assert result_state["audio_url"] is not None

    @pytest.mark.asyncio
    async def test_vision_node(self, pipeline_instance, initial_state):
        initial_state["status"] = "processing"
        
        with patch('app.agents.pipeline.AsyncSessionLocal') as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db
            mock_db.commit = AsyncMock()
            mock_db.flush = AsyncMock()
            
            result_state = await pipeline_instance._vision_node(initial_state)
            
            assert result_state["vision_analysis"] is not None
            assert result_state["current_agent"] == "vision"
            assert "categories" in result_state["vision_analysis"]

    @pytest.mark.asyncio
    async def test_speech_node(self, pipeline_instance, initial_state):
        initial_state["status"] = "processing"
        
        with patch('app.agents.pipeline.AsyncSessionLocal') as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db
            mock_db.commit = AsyncMock()
            mock_db.flush = AsyncMock()
            
            result_state = await pipeline_instance._speech_node(initial_state)
            
            assert result_state["speech_transcript"] is not None
            assert result_state["current_agent"] == "speech"
            assert "pothole" in result_state["speech_transcript"].lower()

    @pytest.mark.asyncio
    async def test_location_node(self, pipeline_instance, initial_state):
        initial_state["status"] = "processing"
        
        with patch('app.agents.pipeline.AsyncSessionLocal') as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db
            mock_db.commit = AsyncMock()
            mock_db.flush = AsyncMock()
            
            result_state = await pipeline_instance._location_node(initial_state)
            
            assert result_state["location_details"] is not None
            assert result_state["current_agent"] == "location"
            assert "department" in result_state["location_details"]

    @pytest.mark.asyncio
    async def test_rag_node(self, pipeline_instance, initial_state):
        initial_state["status"] = "processing"
        initial_state["vision_analysis"] = {
            "recommended_category": "pothole",
            "confidence": 0.85,
        }
        
        with patch('app.agents.pipeline.AsyncSessionLocal') as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db
            mock_db.commit = AsyncMock()
            mock_db.flush = AsyncMock()
            
            result_state = await pipeline_instance._rag_node(initial_state)
            
            assert result_state["rag_context"] is not None
            assert result_state["current_agent"] == "rag"
            assert "relevant_rules" in result_state["rag_context"]
            assert "relevant_incidents" in result_state["rag_context"]

    @pytest.mark.asyncio
    async def test_decision_node(self, pipeline_instance, initial_state):
        initial_state["status"] = "processing"
        initial_state["vision_analysis"] = {"recommended_category": "pothole"}
        initial_state["rag_context"] = {
            "synthesis": "Critical priority per municipal code",
            "confidence": 0.91,
        }
        
        with patch('app.agents.pipeline.AsyncSessionLocal') as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db
            mock_db.commit = AsyncMock()
            mock_db.flush = AsyncMock()
            
            result_state = await pipeline_instance._decision_node(initial_state)
            
            assert result_state["decision"] is not None
            assert result_state["current_agent"] == "decision"
            assert result_state["decision"]["category"] == "pothole"
            assert result_state["decision"]["priority"] in ["high", "critical"]

    @pytest.mark.asyncio
    async def test_verification_node_auto_process(self, pipeline_instance, initial_state):
        initial_state["status"] = "processing"
        initial_state["vision_analysis"] = {"confidence": 0.85}
        initial_state["rag_context"] = {"confidence": 0.91}
        initial_state["decision"] = {"confidence": 0.88}
        initial_state["location_details"] = {"coordinate_accuracy": "exact"}
        
        with patch('app.agents.pipeline.AsyncSessionLocal') as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db
            mock_db.commit = AsyncMock()
            mock_db.flush = AsyncMock()
            
            result_state = await pipeline_instance._verification_node(initial_state)
            
            assert result_state["verification"] is not None
            assert result_state["current_agent"] == "verification"
            assert "overall_confidence" in result_state["verification"]
            assert "requires_human_review" in result_state["verification"]

    @pytest.mark.asyncio
    async def test_verification_node_requires_review(self, pipeline_instance, initial_state):
        initial_state["status"] = "processing"
        initial_state["vision_analysis"] = {"confidence": 0.5}  # Low confidence
        initial_state["rag_context"] = {"confidence": 0.5}
        initial_state["decision"] = {"confidence": 0.5}
        initial_state["location_details"] = {"coordinate_accuracy": "approximate"}
        
        with patch('app.agents.pipeline.AsyncSessionLocal') as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db
            mock_db.commit = AsyncMock()
            mock_db.flush = AsyncMock()
            
            result_state = await pipeline_instance._verification_node(initial_state)
            
            assert result_state["requires_human_review"] is True
            assert result_state["confidence_score"] < 0.7

    def test_should_human_review_true(self, pipeline_instance, initial_state):
        initial_state["requires_human_review"] = True
        assert pipeline_instance._should_human_review(initial_state) == "human_review"

    def test_should_human_review_false(self, pipeline_instance, initial_state):
        initial_state["requires_human_review"] = False
        assert pipeline_instance._should_human_review(initial_state) == "work_order"

    @pytest.mark.asyncio
    async def test_work_order_node(self, pipeline_instance, initial_state):
        initial_state["status"] = "processing"
        initial_state["decision"] = {
            "category": "pothole",
            "priority": "high",
            "assigned_department": "Public Works",
            "estimated_cost": 2500.0,
            "estimated_duration_days": 2,
        }
        initial_state["vision_analysis"] = {"damage_assessment": "Test damage"}
        initial_state["location_details"] = {"nearest_intersection": "Main & Oak"}
        
        with patch('app.agents.pipeline.AsyncSessionLocal') as mock_session_factory:
            mock_db = AsyncMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db
            mock_db.commit = AsyncMock()
            mock_db.flush = AsyncMock()
            
            result_state = await pipeline_instance._work_order_node(initial_state)
            
            assert result_state["work_order"] is not None
            assert result_state["work_order_id"] is not None
            assert result_state["status"] == "completed"
            assert result_state["current_agent"] == "work_order"
            assert "WO-" in result_state["work_order"]["work_order_number"]