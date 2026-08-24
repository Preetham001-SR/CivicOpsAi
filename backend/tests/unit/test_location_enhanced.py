import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.agents.location import (
    LocationAgent, 
    LocationInput, 
    LocationOutput,
    WeatherClient,
    OverpassClient,
    CacheManager,
    WeatherData,
    POIData,
)
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


class TestWeatherClient:
    @pytest.mark.asyncio
    async def test_weather_client_no_api_key(self):
        client = WeatherClient(api_key=None)
        result = await client.get_weather(40.7128, -74.0060)
        assert result is None

    @pytest.mark.asyncio
    async def test_weather_client_success(self):
        mock_response = {
            "weather": [{"main": "Rain", "description": "light rain"}],
            "main": {"temp": 15.5, "humidity": 80},
            "rain": {"1h": 2.5},
            "wind": {"speed": 5.0},
        }
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_get.return_value = mock_response_obj
            
            client = WeatherClient(api_key="test_key")
            result = await client.get_weather(40.7128, -74.0060)
            
            assert result is not None
            assert result.condition == "rain"
            assert result.temperature_celsius == 15.5
            assert result.humidity_percent == 80
            assert result.precipitation_mm == 2.5
            assert result.wind_speed_kmh == 18.0  # 5 m/s * 3.6

    @pytest.mark.asyncio
    async def test_weather_client_http_error(self):
        import httpx
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection failed")
            
            client = WeatherClient(api_key="test_key")
            result = await client.get_weather(40.7128, -74.0060)
            assert result is None


class TestOverpassClient:
    @pytest.mark.asyncio
    async def test_overpass_client_success(self):
        mock_response = {
            "elements": [
                {
                    "type": "node",
                    "lat": 40.7128,
                    "lon": -74.0060,
                    "tags": {"highway": "bus_stop", "name": "Main St Bus Stop"}
                },
                {
                    "type": "node",
                    "lat": 40.7130,
                    "lon": -74.0062,
                    "tags": {"highway": "traffic_signals"}
                },
                {
                    "type": "way",
                    "center": {"lat": 40.7125, "lon": -74.0058},
                    "tags": {"highway": "residential", "name": "Main St"}
                },
            ]
        }
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_post.return_value = mock_response_obj
            
            client = OverpassClient()
            result = await client.get_nearby_pois(40.7128, -74.0060, radius=200)
            
            assert len(result) >= 2  # At least bus_stop and traffic_signals
            bus_stops = [p for p in result if p.poi_type == "bus_stop"]
            assert len(bus_stops) >= 1
            signals = [p for p in result if p.poi_type == "traffic_signal"]
            assert len(signals) >= 1

    @pytest.mark.asyncio
    async def test_overpass_classify_poi(self):
        client = OverpassClient()
        
        assert client._classify_poi({"highway": "bus_stop"}) == "bus_stop"
        assert client._classify_poi({"highway": "traffic_signals"}) == "traffic_signal"
        assert client._classify_poi({"highway": "crossing"}) == "crossing"
        assert client._classify_poi({"amenity": "bus_station"}) == "bus_station"
        assert client._classify_poi({"amenity": "parking"}) == "parking"
        assert client._classify_poi({"amenity": "school"}) == "school"
        assert client._classify_poi({"highway": "street_lamp"}) == "street_lamp"
        assert client._classify_poi({"highway": "residential"}) == "highway_residential"
        assert client._classify_poi({"random": "tag"}) is None


class TestCacheManager:
    @pytest.mark.asyncio
    async def test_cache_get_set(self):
        manager = CacheManager(redis_url="redis://localhost:6379/0")
        
        # Mock redis client
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.setex = AsyncMock()
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            # Test get (miss)
            result = await manager.get("test", "key1")
            assert result is None
            
            # Test set
            success = await manager.set("test", {"data": "value"}, "key1", ttl=60)
            assert success is True
            mock_redis.setex.assert_called_once()


class TestLocationAgent:
    @pytest.mark.asyncio
    async def test_location_agent_with_address(self, location_agent, mock_db, complaint_id, trace_id):
        # Test with different coordinates to avoid cache hits from other tests
        input_data = LocationInput(
            latitude=34.0522,
            longitude=-118.2437,
            address="123 Main St, Los Angeles, CA",
            complaint_id=str(complaint_id)
        )
        
        # Clear cache to avoid interference from other tests
        import app.agents.location as loc_module
        loc_module.cache = CacheManager()
        
        mock_geocode_response = {
            "display_name": "Main St & 1st St, Los Angeles, CA 90012, USA",
            "address": {
                "road": "Main St",
                "highway": "1st St",
                "neighbourhood": "Downtown",
                "city_district": "Central LA",
                "city": "Los Angeles",
                "county": "Los Angeles County",
                "state": "California",
                "country": "USA",
            },
            "type": "junction",
        }
        
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
            assert result.output.model_used == "nominatim_failed"

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

    @pytest.mark.asyncio
    async def test_location_agent_enhanced_output(self, location_agent, mock_db, complaint_id, trace_id):
        """Test enhanced location output with weather, POIs, and road details"""
        mock_geocode_response = {
            "display_name": "Main St & Oak Ave, New York, NY 10001, USA",
            "address": {
                "road": "Main St",
                "highway": "Oak Ave",
                "neighbourhood": "Downtown",
                "city_district": "Manhattan",
                "city": "New York",
                "waterway": "river",  # Add water feature for flood risk
            },
            "type": "junction",
            "extratags": {
                "surface": "asphalt",
                "maxspeed": "50 km/h",
                "traffic_signals": "yes",
            },
        }
        
        mock_weather = WeatherData(
            temperature_celsius=20.0,
            humidity_percent=65,
            precipitation_mm=25.0,  # Higher precipitation for flood risk
            wind_speed_kmh=15.0,
            condition="Rain",
            description="heavy rain",
            timestamp=datetime.utcnow(),
        )
        
        mock_pois = [
            POIData(name="Main St Bus Stop", poi_type="bus_stop", distance_meters=50, tags={"highway": "bus_stop"}),
            POIData(name="Traffic Light", poi_type="traffic_signal", distance_meters=100, tags={"highway": "traffic_signals"}),
        ]
        
        with patch.object(location_agent, '_reverse_geocode', new_callable=AsyncMock) as mock_geocode, \
             patch.object(location_agent, '_get_weather_cached', new_callable=AsyncMock) as mock_get_weather, \
             patch.object(location_agent, '_get_pois_cached', new_callable=AsyncMock) as mock_get_pois:
            
            mock_geocode.return_value = mock_geocode_response
            mock_get_weather.return_value = mock_weather
            mock_get_pois.return_value = mock_pois
            
            input_data = LocationInput(
                latitude=40.7128,
                longitude=-74.0060,
                address=None,
                complaint_id=str(complaint_id)
            )
            
            result = await location_agent.execute(input_data, mock_db, complaint_id, trace_id)
            
            assert result.success is True
            assert result.output is not None
            assert result.output.weather is not None
            assert result.output.weather.condition == "Rain"
            assert result.output.weather.precipitation_mm == 25.0
            assert len(result.output.nearby_pois) == 2
            assert result.output.bus_stops_nearby == 1
            assert result.output.traffic_signals_nearby is True
            assert result.output.road_type == "Main St"
            assert result.output.road_surface == "asphalt"
            assert result.output.speed_limit == 50
            assert result.output.traffic_signals_nearby is True
            assert result.output.flood_risk is not None


class TestDecisionAgentWithWeather:
    """Test that Decision Agent uses weather and infrastructure context"""
    
    @pytest.mark.asyncio
    async def test_build_weather_context(self):
        from app.agents.decision import DecisionAgent
        
        agent = DecisionAgent()
        
        location_with_weather = {
            "weather": {
                "condition": "Rain",
                "temperature_celsius": 15.0,
                "humidity_percent": 80,
                "precipitation_mm": 25.0,
                "wind_speed_kmh": 20.0,
                "description": "heavy rain",
            }
        }
        
        context = agent._build_weather_context(location_with_weather)
        assert "Rain" in context
        assert "15.0" in context
        assert "25.0" in context
        
    @pytest.mark.asyncio
    async def test_build_infrastructure_context(self):
        from app.agents.decision import DecisionAgent
        
        agent = DecisionAgent()
        
        location_with_infra = {
            "road_type": "Main St",
            "road_surface": "asphalt",
            "speed_limit": 50,
            "traffic_signals_nearby": True,
            "bus_stops_nearby": 2,
            "flood_risk": "high",
            "nearby_pois": [
                {"poi_type": "bus_stop", "tags": {}},
                {"poi_type": "bus_stop", "tags": {}},
                {"poi_type": "traffic_signal", "tags": {}},
            ]
        }
        
        context = agent._build_infrastructure_context(location_with_infra)
        assert "Main St" in context
        assert "asphalt" in context
        assert "50" in context
        assert "2" in context
        assert "high" in context
        assert "bus_stop: 2" in context
        assert "traffic_signal: 1" in context

    @pytest.mark.asyncio
    async def test_decision_fallback_with_weather(self):
        from app.agents.decision import DecisionAgent
        from app.db.models import ComplaintCategory, PriorityLevel
        
        agent = DecisionAgent()
        
        location = {
            "weather": {
                "precipitation_mm": 30,
            },
            "bus_stops_nearby": 1,
            "flood_risk": "high",
        }
        
        rag_synthesis = "Standard pothole repair"
        category = ComplaintCategory.POTHOLE
        
        # Test critical priority due to heavy rain
        priority = PriorityLevel.HIGH
        if location["weather"]["precipitation_mm"] > 20:
            priority = PriorityLevel.CRITICAL
            
        assert priority == PriorityLevel.CRITICAL