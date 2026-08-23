import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intake import IntakeAgent, IntakeInput, IntakeOutput
from app.agents.base import AgentResult
from app.db.models import AgentType


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def intake_agent():
    return IntakeAgent()


@pytest.fixture
def sample_input():
    return IntakeInput(
        text_description="Test pothole on Main St",
        photo_url="https://example.com/photo.jpg",
        audio_url="https://example.com/audio.wav",
        latitude=40.7128,
        longitude=-74.0060,
        address="Main St, New York, NY",
    )


@pytest.fixture
def complaint_id():
    return uuid.uuid4()


@pytest.fixture
def trace_id():
    return "test-trace-123"


class TestIntakeAgent:
    @pytest.mark.asyncio
    async def test_happy_path(self, intake_agent, mock_db, sample_input, complaint_id, trace_id):
        result = await intake_agent.execute(sample_input, mock_db, complaint_id, trace_id)
        
        assert result.success is True
        assert result.output is not None
        assert isinstance(result.output, IntakeOutput)
        assert result.output.complaint_id == complaint_id
        assert result.output.photo_stored is True
        assert result.output.audio_stored is True
        assert result.execution_time_ms > 0
        
        # Verify DB log was called
        mock_db.add.assert_called()
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_no_photo_no_audio(self, intake_agent, mock_db, complaint_id, trace_id):
        input_data = IntakeInput(
            text_description="Test complaint",
            latitude=40.7128,
            longitude=-74.0060,
        )
        
        result = await intake_agent.execute(input_data, mock_db, complaint_id, trace_id)
        
        assert result.success is True
        assert result.output.photo_stored is False
        assert result.output.audio_stored is False

    @pytest.mark.asyncio
    async def test_empty_photo_url(self, intake_agent, mock_db, complaint_id, trace_id):
        input_data = IntakeInput(
            text_description="Test complaint",
            photo_url="",
            latitude=40.7128,
            longitude=-74.0060,
        )
        
        result = await intake_agent.execute(input_data, mock_db, complaint_id, trace_id)
        
        assert result.success is True
        assert result.output.photo_stored is False

    @pytest.mark.asyncio
    async def test_database_error_handling(self, intake_agent, mock_db, sample_input, complaint_id, trace_id):
        mock_db.flush.side_effect = Exception("DB connection failed")
        
        result = await intake_agent.execute(sample_input, mock_db, complaint_id, trace_id)
        
        assert result.success is False
        assert "DB connection failed" in result.error
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_agent_type(self, intake_agent):
        assert intake_agent.agent_type == AgentType.INTAKE

    def test_input_validation_valid(self):
        input_data = IntakeInput(
            text_description="Valid description",
            latitude=40.7128,
            longitude=-74.0060,
        )
        assert input_data.latitude == 40.7128
        assert input_data.longitude == -74.0060

    def test_input_validation_invalid_latitude(self):
        with pytest.raises(ValueError):
            IntakeInput(
                text_description="Test",
                latitude=100,  # Invalid
                longitude=-74.0060,
            )

    def test_input_validation_invalid_longitude(self):
        with pytest.raises(ValueError):
            IntakeInput(
                text_description="Test",
                latitude=40.7128,
                longitude=-200,  # Invalid
            )