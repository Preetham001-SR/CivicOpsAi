import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intake import IntakeAgent, IntakeInput, IntakeOutput
from app.db.models import AgentType


@pytest.fixture
def intake_agent():
    return IntakeAgent()


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def complaint_id():
    return uuid.uuid4()


@pytest.fixture
def trace_id():
    return "test-trace-123"


class TestIntakeAgent:
    @pytest.mark.asyncio
    async def test_intake_agent_no_files(self, intake_agent, mock_db, complaint_id, trace_id):
        input_data = IntakeInput(
            text_description="Test complaint",
            photo_url=None,
            audio_url=None,
            latitude=40.7128,
            longitude=-74.0060,
            address="Test address",
        )
        
        result = await intake_agent.execute(input_data, mock_db, complaint_id, trace_id)
        
        assert result.success is True
        assert result.output is not None
        assert result.output.photo_stored is False
        assert result.output.audio_stored is False
        assert result.output.photo_object_name is None
        assert result.output.audio_object_name is None
        assert len(result.output.validation_errors) == 0

    @pytest.mark.asyncio
    async def test_intake_agent_photo_success(self, intake_agent, mock_db, complaint_id, trace_id):
        fake_image = b"fake jpeg content"
        
        with patch.object(intake_agent, '_validate_and_download', new_callable=AsyncMock) as mock_download, \
             patch.object(intake_agent, '_upload_to_minio', new_callable=AsyncMock) as mock_upload:
            
            mock_download.return_value = (fake_image, "image/jpeg")
            mock_upload.return_value = "http://minio:9000/civicops/complaints/test/photo.jpg"
            
            input_data = IntakeInput(
                text_description="Test complaint",
                photo_url="https://example.com/photo.jpg",
                audio_url=None,
                latitude=40.7128,
                longitude=-74.0060,
                address="Test address",
            )
            
            result = await intake_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output.photo_stored is True
            assert result.output.photo_object_name is not None
            assert result.output.photo_object_name.endswith(".jpg")
            assert result.output.photo_url == "http://minio:9000/civicops/complaints/test/photo.jpg"
            assert len(result.output.validation_errors) == 0

    @pytest.mark.asyncio
    async def test_intake_agent_audio_success(self, intake_agent, mock_db, complaint_id, trace_id):
        fake_audio = b"fake wav content"
        
        with patch.object(intake_agent, '_validate_and_download', new_callable=AsyncMock) as mock_download, \
             patch.object(intake_agent, '_upload_to_minio', new_callable=AsyncMock) as mock_upload:
            
            mock_download.return_value = (fake_audio, "audio/wav")
            mock_upload.return_value = "http://minio:9000/civicops/complaints/test/audio.wav"
            
            input_data = IntakeInput(
                text_description="Test complaint",
                photo_url=None,
                audio_url="https://example.com/audio.wav",
                latitude=40.7128,
                longitude=-74.0060,
                address="Test address",
            )
            
            result = await intake_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output.audio_stored is True
            assert result.output.audio_object_name is not None
            assert result.output.audio_object_name.endswith(".wav")
            assert result.output.audio_url == "http://minio:9000/civicops/complaints/test/audio.wav"
            assert len(result.output.validation_errors) == 0

    @pytest.mark.asyncio
    async def test_intake_agent_photo_validation_error(self, intake_agent, mock_db, complaint_id, trace_id):
        with patch.object(intake_agent, '_validate_and_download', new_callable=AsyncMock) as mock_download:
            mock_download.side_effect = ValueError("Unsupported file type: image/tiff")
            
            input_data = IntakeInput(
                text_description="Test complaint",
                photo_url="https://example.com/photo.tiff",
                audio_url=None,
                latitude=40.7128,
                longitude=-74.0060,
                address="Test address",
            )
            
            result = await intake_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output.photo_stored is False
            assert len(result.output.validation_errors) == 1
            assert "Unsupported file type" in result.output.validation_errors[0]

    @pytest.mark.asyncio
    async def test_intake_agent_audio_validation_error(self, intake_agent, mock_db, complaint_id, trace_id):
        with patch.object(intake_agent, '_validate_and_download', new_callable=AsyncMock) as mock_download:
            mock_download.side_effect = ValueError("File size 60000000 exceeds maximum 52428800")
            
            input_data = IntakeInput(
                text_description="Test complaint",
                photo_url=None,
                audio_url="https://example.com/large_audio.wav",
                latitude=40.7128,
                longitude=-74.0060,
                address="Test address",
            )
            
            result = await intake_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output.audio_stored is False
            assert len(result.output.validation_errors) == 1
            assert "exceeds maximum" in result.output.validation_errors[0]

    @pytest.mark.asyncio
    async def test_intake_agent_minio_upload_failure(self, intake_agent, mock_db, complaint_id, trace_id):
        fake_image = b"fake jpeg content"
        
        with patch.object(intake_agent, '_validate_and_download', new_callable=AsyncMock) as mock_download, \
             patch.object(intake_agent, '_upload_to_minio', new_callable=AsyncMock) as mock_upload:
            
            mock_download.return_value = (fake_image, "image/jpeg")
            mock_upload.side_effect = Exception("MinIO connection failed")
            
            input_data = IntakeInput(
                text_description="Test complaint",
                photo_url="https://example.com/photo.jpg",
                audio_url=None,
                latitude=40.7128,
                longitude=-74.0060,
                address="Test address",
            )
            
            result = await intake_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output.photo_stored is False
            assert len(result.output.validation_errors) == 1
            assert "Photo processing failed" in result.output.validation_errors[0]

    @pytest.mark.asyncio
    async def test_intake_agent_both_files(self, intake_agent, mock_db, complaint_id, trace_id):
        fake_image = b"fake jpeg content"
        fake_audio = b"fake wav content"
        
        with patch.object(intake_agent, '_validate_and_download', new_callable=AsyncMock) as mock_download, \
             patch.object(intake_agent, '_upload_to_minio', new_callable=AsyncMock) as mock_upload:
            
            mock_download.side_effect = [
                (fake_image, "image/jpeg"),
                (fake_audio, "audio/wav"),
            ]
            mock_upload.side_effect = [
                "http://minio:9000/civicops/complaints/test/photo.jpg",
                "http://minio:9000/civicops/complaints/test/audio.wav",
            ]
            
            input_data = IntakeInput(
                text_description="Test complaint",
                photo_url="https://example.com/photo.jpg",
                audio_url="https://example.com/audio.wav",
                latitude=40.7128,
                longitude=-74.0060,
                address="Test address",
            )
            
            result = await intake_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output.photo_stored is True
            assert result.output.audio_stored is True
            assert result.output.photo_url is not None
            assert result.output.audio_url is not None
            assert len(result.output.validation_errors) == 0

    def test_intake_input_validation_valid(self):
        input_data = IntakeInput(
            text_description="Valid description",
            photo_url="https://example.com/photo.jpg",
            audio_url="https://example.com/audio.wav",
            latitude=40.7128,
            longitude=-74.0060,
            address="Valid address",
        )
        assert input_data.latitude == 40.7128

    def test_intake_input_validation_invalid_latitude(self):
        with pytest.raises(ValueError):
            IntakeInput(
                text_description="Test",
                latitude=95.0,
                longitude=-74.0060,
            )

    def test_intake_input_validation_invalid_longitude(self):
        with pytest.raises(ValueError):
            IntakeInput(
                text_description="Test",
                latitude=40.7128,
                longitude=-200.0,
            )

    def test_intake_input_empty_url_becomes_none(self):
        input_data = IntakeInput(
            text_description="Test",
            photo_url="",
            audio_url="",
            latitude=40.7128,
            longitude=-74.0060,
        )
        assert input_data.photo_url is None
        assert input_data.audio_url is None