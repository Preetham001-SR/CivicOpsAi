import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.location import LocationAgent, LocationInput, LocationOutput
from app.agents.location import CacheManager  # Import CacheManager
from app.db.models import AgentType


@pytest.fixture
def location_agent():
    return LocationAgent()


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def complaint_id():
    return uuid.uuid4()


@pytest.fixture
def trace_id():
    return "test-trace-123"


class TestLocationAgent:
    @pytest.mark.asyncio
    async def test_location_agent_with_address(self, location_agent, mock_db, complaint_id, trace_id):
        input_data = LocationInput(
            latitude=40.7128,
            longitude=-74.0060,
            address="123 Main St, New York, NY",
            complaint_id=str(complaint_id)
        )
        
        # With address provided, we still do reverse geocoding but the formatted_address
        # will come from the geocoding result
        mock_geocode_response = {
            "display_name": "Main St & Oak Ave, New York, NY 10001, USA",
            "address": {
                "road": "Main St",
                "highway": "Oak Ave",
                "neighbourhood": "Downtown",
                "city_district": "Manhattan",
                "city": "New York",
                "county": "New York County",
                "state": "New York",
                "country": "USA",
            },
            "type": "junction",
        }
        
        # Clear cache to avoid interference from other tests
        import app.agents.location as loc_module
        loc_module.cache = CacheManager()  # Create fresh cache instance
        
        with patch.object(location_agent, '_reverse_geocode', new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = mock_geocode_response
            
            result = await location_agent.execute(input_data, mock_db, complaint_id, trace_id)
        
        assert result.success is True
        assert result.output is not None
        # The formatted address comes from reverse geocoding, not the provided address
        assert "Main St" in result.output.formatted_address
        assert result.output.coordinate_accuracy in ["exact", "geocoded"]
        assert result.output.model_used == "nominatim"

    @pytest.mark.asyncio
    async def test_location_agent_geocoding_success(self, location_agent, mock_db, complaint_id, trace_id):
        mock_geocode_response = {
            "display_name": "Main St & Oak Ave, New York, NY 10001, USA",
            "address": {
                "road": "Main St",
                "highway": "Oak Ave",
                "neighbourhood": "Downtown",
                "city_district": "Manhattan",
                "city": "New York",
                "county": "New York County",
                "state": "New York",
                "country": "USA",
            },
            "type": "junction",
        }
        
        with patch.object(location_agent, '_reverse_geocode', new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = mock_geocode_response
            
            input_data = LocationInput(
                latitude=40.7128,
                longitude=-74.0060,
                address=None,
                complaint_id=str(complaint_id)
            )
            
            result = await location_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output is not None
            assert "Main St" in result.output.formatted_address
            assert result.output.neighborhood == "Downtown"
            assert result.output.district == "Manhattan"
            assert result.output.jurisdiction == "New York"
            assert result.output.nearest_intersection == "Main St & Oak Ave"
            assert result.output.coordinate_accuracy in ["exact", "geocoded"]
            assert result.output.model_used == "nominatim"

    @pytest.mark.asyncio
    async def test_location_agent_geocoding_failure(self, location_agent, mock_db, complaint_id, trace_id):
        with patch.object(location_agent, '_reverse_geocode', new_callable=AsyncMock) as mock_geocode:
            mock_geocode.return_value = None
            
            input_data = LocationInput(
                latitude=40.7128,
                longitude=-74.0060,
                address=None,
                complaint_id=str(complaint_id)
            )
            
            result = await location_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output is not None
            assert "Lat:" in result.output.formatted_address
            assert result.output.coordinate_accuracy == "approximate"
            assert result.output.jurisdiction == "Unknown"
            assert result.output.model_used == "nominatim_failed"

    @pytest.mark.asyncio
    async def test_location_agent_http_error(self, location_agent, mock_db, complaint_id, trace_id):
        import httpx
        
        with patch.object(location_agent, '_reverse_geocode', new_callable=AsyncMock) as mock_geocode:
            mock_geocode.side_effect = httpx.HTTPError("Network error")
            
            input_data = LocationInput(
                latitude=40.7128,
                longitude=-74.0060,
                address=None,
                complaint_id=str(complaint_id)
            )
            
            result = await location_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output is not None
            assert result.output.coordinate_accuracy == "approximate"
            assert "nominatim" in result.output.model_used

    def test_determine_department_pothole(self, location_agent):
        address_components = {"road": "Main St", "suburb": "Pothole Area"}
        dept = location_agent._determine_department(address_components)
        assert dept == "Public Works - Street Maintenance"

    def test_determine_department_streetlight(self, location_agent):
        address_components = {"road": "Oak Ave", "neighbourhood": "Streetlight District"}
        dept = location_agent._determine_department(address_components)
        assert dept == "Public Works - Street Lighting"

    def test_determine_department_drain(self, location_agent):
        address_components = {"road": "Elm St", "suburb": "Drainage Area"}
        dept = location_agent._determine_department(address_components)
        assert dept == "Public Works - Stormwater Management"

    def test_determine_department_default(self, location_agent):
        address_components = {"road": "Unknown St"}
        dept = location_agent._determine_department(address_components)
        assert dept == "Public Works - General"

    def test_extract_intersection_with_junction(self, location_agent):
        address_components = {"junction": "Main St & Oak Ave", "road": "Main St"}
        intersection = location_agent._extract_intersection(address_components)
        assert intersection == "Main St & Oak Ave"

    def test_extract_intersection_with_road_highway(self, location_agent):
        address_components = {"road": "Main St", "highway": "Oak Ave"}
        intersection = location_agent._extract_intersection(address_components)
        assert intersection == "Main St & Oak Ave"

    def test_extract_intersection_none(self, location_agent):
        address_components = {"suburb": "Downtown"}
        intersection = location_agent._extract_intersection(address_components)
        assert intersection is None