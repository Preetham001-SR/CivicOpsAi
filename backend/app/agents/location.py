from typing import Dict, Any, Optional, List
import uuid
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentResult
from app.db.models import AgentType
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import httpx
import json
import hashlib
from datetime import datetime, timedelta

logger = structlog.get_logger()


class WeatherData(BaseModel):
    """Current weather conditions"""
    temperature_celsius: float
    humidity_percent: int
    precipitation_mm: float
    wind_speed_kmh: float
    condition: str  # e.g., "rain", "clear", "cloudy", "storm"
    description: str
    timestamp: datetime


class POIData(BaseModel):
    """Point of Interest from OpenStreetMap/Overpass"""
    name: str
    poi_type: str  # e.g., "bus_stop", "amenity", "highway", "crossing"
    distance_meters: float
    tags: Dict[str, Any]


class LocationOutput(BaseModel):
    formatted_address: str = Field(description="Human-readable formatted address")
    neighborhood: Optional[str] = Field(default=None, description="Neighborhood or area name")
    district: Optional[str] = Field(default=None, description="District or borough")
    nearest_intersection: Optional[str] = Field(default=None, description="Nearest cross streets")
    jurisdiction: str = Field(description="Administrative jurisdiction (city/county)")
    department: str = Field(description="Responsible municipal department")
    coordinate_accuracy: str = Field(description="Accuracy level: exact, approximate, geocoded")
    raw_response: Optional[Dict[str, Any]] = Field(default=None, description="Raw geocoding response")
    model_used: str = Field(default="nominatim", description="Geocoding service used")
    
    # Enhanced data
    weather: Optional[WeatherData] = Field(default=None, description="Current weather conditions")
    nearby_pois: List[POIData] = Field(default_factory=list, description="Nearby points of interest")
    road_type: Optional[str] = Field(default=None, description="Type of road (highway, residential, service, etc.)")
    road_surface: Optional[str] = Field(default=None, description="Road surface type")
    speed_limit: Optional[int] = Field(default=None, description="Speed limit in km/h")
    traffic_signals_nearby: bool = Field(default=False, description="Whether traffic signals are nearby")
    bus_stops_nearby: int = Field(default=0, description="Number of bus stops within 200m")
    flood_risk: Optional[str] = Field(default=None, description="Flood risk level if available")


class LocationInput(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: Optional[str] = None
    complaint_id: str


DEPARTMENT_MAPPING = {
    "streetlight": "Public Works - Street Lighting",
    "pothole": "Public Works - Street Maintenance",
    "road": "Public Works - Street Maintenance",
    "street": "Public Works - Street Maintenance",
    "sidewalk": "Public Works - Sidewalk Maintenance",
    "light": "Public Works - Street Lighting",
    "traffic": "Transportation - Traffic Engineering",
    "signal": "Transportation - Traffic Engineering",
    "sign": "Transportation - Signs & Markings",
    "drain": "Public Works - Stormwater Management",
    "sewer": "Public Works - Wastewater",
    "water": "Public Works - Water Distribution",
    "tree": "Parks & Recreation - Forestry",
    "park": "Parks & Recreation",
    "graffiti": "Public Works - Graffiti Removal",
    "trash": "Sanitation",
    "building": "Building & Safety",
    "default": "Public Works - General",
}


class WeatherClient:
    """OpenWeatherMap API client with caching"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.WEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        
    async def get_weather(self, latitude: float, longitude: float) -> Optional[WeatherData]:
        if not self.api_key:
            logger.warning("weather_api_key_not_configured")
            return None
            
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.api_key,
            "units": "metric",
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                weather = data.get("weather", [{}])[0]
                main = data.get("main", {})
                wind = data.get("wind", {})
                rain = data.get("rain", {})
                
                return WeatherData(
                    temperature_celsius=main.get("temp", 0),
                    humidity_percent=main.get("humidity", 0),
                    precipitation_mm=rain.get("1h", 0) + rain.get("3h", 0),
                    wind_speed_kmh=wind.get("speed", 0) * 3.6,  # m/s to km/h
                    condition=weather.get("main", "").lower(),
                    description=weather.get("description", ""),
                    timestamp=datetime.utcnow(),
                )
        except httpx.HTTPError as e:
            logger.warning("weather_api_request_failed", error=str(e))
            return None
        except Exception as e:
            logger.warning("weather_api_unexpected_error", error=str(e))
            return None


class OverpassClient:
    """OpenStreetMap Overpass API client for POI queries"""
    
    def __init__(self):
        self.base_url = "https://overpass-api.de/api/interpreter"
        self.user_agent = "CivicOps-AI/1.0"
        
    def _build_query(self, latitude: float, longitude: float, radius: int = 200) -> str:
        """Build Overpass QL query for nearby POIs"""
        return f"""
        [out:json][timeout:25];
        (
          node["highway"="bus_stop"](around:{radius},{latitude},{longitude});
          node["highway"="traffic_signals"](around:{radius},{latitude},{longitude});
          node["highway"="crossing"](around:{radius},{latitude},{longitude});
          node["amenity"="bus_station"](around:{radius},{latitude},{longitude});
          node["amenity"="parking"](around:{radius},{latitude},{longitude});
          node["amenity"="school"](around:{radius},{latitude},{longitude});
          node["amenity"="hospital"](around:{radius},{latitude},{longitude});
          node["highway"="street_lamp"](around:{radius},{latitude},{longitude});
          way["highway"](around:{radius},{latitude},{longitude});
        );
        out center tags;
        """
    
    async def get_nearby_pois(self, latitude: float, longitude: float, radius: int = 200) -> List[POIData]:
        query = self._build_query(latitude, longitude, radius)
        headers = {"User-Agent": self.user_agent}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    data={"data": query},
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                pois = []
                for element in data.get("elements", []):
                    tags = element.get("tags", {})
                    if not tags:
                        continue
                        
                    # Calculate distance
                    if element.get("type") == "node":
                        el_lat = element.get("lat", 0)
                        el_lon = element.get("lon", 0)
                    elif element.get("type") == "way":
                        center = element.get("center", {})
                        el_lat = center.get("lat", 0)
                        el_lon = center.get("lon", 0)
                    else:
                        continue
                        
                    # Simple distance calculation (Haversine would be more accurate)
                    lat_diff = abs(el_lat - latitude) * 111000  # approximate meters per degree
                    lon_diff = abs(el_lon - longitude) * 111000
                    distance = (lat_diff**2 + lon_diff**2)**0.5
                    
                    if distance > 200:  # Filter by radius
                        continue
                        
                    poi_type = self._classify_poi(tags)
                    if poi_type:
                        pois.append(POIData(
                            name=tags.get("name", "Unknown"),
                            poi_type=poi_type,
                            distance_meters=round(distance),
                            tags=tags,
                        ))
                        
                return pois
                
        except httpx.HTTPError as e:
            logger.warning("overpass_request_failed", error=str(e))
            return []
        except Exception as e:
            logger.warning("overpass_unexpected_error", error=str(e))
            return []
            
    def _classify_poi(self, tags: Dict[str, Any]) -> Optional[str]:
        """Classify POI based on OSM tags"""
        if tags.get("highway") == "bus_stop":
            return "bus_stop"
        elif tags.get("highway") == "traffic_signals":
            return "traffic_signal"
        elif tags.get("highway") == "crossing":
            return "crossing"
        elif tags.get("amenity") == "bus_station":
            return "bus_station"
        elif tags.get("amenity") == "parking":
            return "parking"
        elif tags.get("amenity") == "school":
            return "school"
        elif tags.get("amenity") == "hospital":
            return "hospital"
        elif tags.get("highway") == "street_lamp":
            return "street_lamp"
        elif tags.get("highway"):
            return f"highway_{tags['highway']}"
        return None


class CacheManager:
    """Redis-based cache for external API responses"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._client = None
        
    async def _get_client(self):
        if self._client is None:
            import redis.asyncio as redis
            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client
        
    def _make_key(self, prefix: str, *args) -> str:
        """Create a deterministic cache key"""
        key_string = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]
        
    async def get(self, prefix: str, *args) -> Optional[Dict]:
        try:
            client = await self._get_client()
            key = self._make_key(prefix, *args)
            data = await client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("cache_get_failed", prefix=prefix, error=str(e))
        return None
        
    async def set(self, prefix: str, value: Dict, *args, ttl: int = 3600) -> bool:
        try:
            client = await self._get_client()
            key = self._make_key(prefix, *args)
            await client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning("cache_set_failed", prefix=prefix, error=str(e))
            return False


class LocationAgent(BaseAgent[LocationInput, LocationOutput]):
    def __init__(self):
        super().__init__(AgentType.LOCATION)
        self.nominatim_url = "https://nominatim.openstreetmap.org/reverse"
        self.user_agent = "CivicOps-AI/1.0"
        self.weather_client = WeatherClient()
        self.overpass_client = OverpassClient()
        self.cache = CacheManager()
        
    def _determine_department(self, address_components: Dict[str, Any]) -> str:
        road_type = address_components.get("road", "").lower()
        suburb = address_components.get("suburb", "").lower()
        neighbourhood = address_components.get("neighbourhood", "").lower()
        
        combined = f"{road_type} {suburb} {neighbourhood}".lower()
        
        for keyword, department in DEPARTMENT_MAPPING.items():
            if keyword in combined:
                return department
        
        return DEPARTMENT_MAPPING["default"]

    def _extract_intersection(self, address_components: Dict[str, Any]) -> Optional[str]:
        road = address_components.get("road")
        highway = address_components.get("highway")
        junction = address_components.get("junction")
        
        if junction:
            return junction
        if road and highway:
            return f"{road} & {highway}"
        if road:
            return road
        return None

    def _extract_road_details(self, geocode_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract road details from Nominatim response"""
        address = geocode_result.get("address", {})
        extratags = geocode_result.get("extratags", {})
        
        return {
            "road_type": address.get("road") or address.get("highway") or address.get("street"),
            "road_surface": extratags.get("surface"),
            "speed_limit": self._parse_speed_limit(extratags.get("maxspeed")),
            "traffic_signals": "traffic_signals" in extratags or "traffic_signals" in str(extratags),
        }
        
    def _parse_speed_limit(self, maxspeed: Optional[str]) -> Optional[int]:
        if not maxspeed:
            return None
        try:
            # Handle formats like "50 km/h", "50", "30 mph"
            import re
            match = re.search(r'(\d+)', maxspeed)
            if match:
                return int(match.group(1))
        except Exception:
            pass
        return None
        
    def _assess_flood_risk(self, weather: Optional[WeatherData], address_components: Dict[str, Any]) -> Optional[str]:
        """Simple flood risk assessment based on weather and location"""
        if not weather:
            return None
            
        # Check for water-related features nearby
        water_features = ["river", "stream", "canal", "drain", "basin", "pond", "lake", "reservoir"]
        combined = " ".join(str(v).lower() for v in address_components.values())
        
        near_water = any(feature in combined for feature in water_features)
        
        if weather.precipitation_mm > 50 and near_water:
            return "high"
        elif weather.precipitation_mm > 20 and near_water:
            return "medium"
        elif weather.condition in ["storm", "heavy_rain"] and near_water:
            return "high"
        elif weather.precipitation_mm > 10:
            return "low"
        return None

    async def _reverse_geocode(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        # Check cache first
        cached = await self.cache.get("nominatim", latitude, longitude)
        if cached:
            logger.info("nominatim_cache_hit", latitude=latitude, longitude=longitude)
            return cached
            
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "addressdetails": 1,
            "extratags": 1,
            "namedetails": 1,
        }
        headers = {"User-Agent": self.user_agent}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.nominatim_url, params=params, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                # Cache for 24 hours
                await self.cache.set("nominatim", result, latitude, longitude, ttl=86400)
                
                return result
        except httpx.HTTPError as e:
            logger.warning("nominatim_request_failed", error=str(e))
            return None
        except Exception as e:
            logger.warning("nominatim_unexpected_error", error=str(e))
            return None

    async def process(
        self,
        input_data: LocationInput,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        trace_id: str,
    ) -> AgentResult[LocationOutput]:
        # Always attempt reverse geocoding for enhanced data (weather, POIs, road details)
        # even if address is provided
        logger.info("location_reverse_geocoding", complaint_id=str(complaint_id), lat=input_data.latitude, lng=input_data.longitude)
        
        # Run geocoding, weather, and Overpass queries in parallel
        geocode_task = self._reverse_geocode(input_data.latitude, input_data.longitude)

        logger.info("location_reverse_geocoding", complaint_id=str(complaint_id), lat=input_data.latitude, lng=input_data.longitude)
        
        # Run geocoding, weather, and Overpass queries in parallel
        geocode_task = self._reverse_geocode(input_data.latitude, input_data.longitude)
        
        try:
            geocode_result = await geocode_task
        except Exception as e:
            logger.warning("reverse_geocode_exception", complaint_id=str(complaint_id), error=str(e))
            geocode_result = None
        
        if not geocode_result:
            logger.warning("geocoding_failed_using_fallback", complaint_id=str(complaint_id))
            output = LocationOutput(
                formatted_address=f"Lat: {input_data.latitude:.6f}, Lng: {input_data.longitude:.6f}",
                neighborhood=None,
                district=None,
                nearest_intersection=None,
                jurisdiction="Unknown",
                department=DEPARTMENT_MAPPING["default"],
                coordinate_accuracy="approximate",
                raw_response={"error": "geocoding_failed"},
                model_used="nominatim_failed",
            )
            return AgentResult(success=True, output=output)
        
        address = geocode_result.get("address", {})
        display_name = geocode_result.get("display_name", f"Lat: {input_data.latitude:.6f}, Lng: {input_data.longitude:.6f}")
        
        neighborhood = address.get("neighbourhood") or address.get("suburb") or address.get("quarter")
        district = address.get("city_district") or address.get("district") or address.get("borough")
        city = address.get("city") or address.get("town") or address.get("village") or address.get("county")
        jurisdiction = city or "Unknown"
        
        intersection = self._extract_intersection(address)
        department = self._determine_department(address)
        road_details = self._extract_road_details(geocode_result)
        
        coordinate_accuracy = "geocoded"
        if geocode_result.get("type") in ["house", "building", "poi"]:
            coordinate_accuracy = "exact"
        elif geocode_result.get("type") in ["road", "street"]:
            coordinate_accuracy = "approximate"
        
        # Fetch weather data (with caching)
        weather = await self._get_weather_cached(input_data.latitude, input_data.longitude)
        
        # Fetch nearby POIs from Overpass (with caching)
        nearby_pois = await self._get_pois_cached(input_data.latitude, input_data.longitude)
        
        # Analyze POIs for specific features
        bus_stops_nearby = sum(1 for poi in nearby_pois if poi.poi_type == "bus_stop")
        traffic_signals_nearby = any(poi.poi_type == "traffic_signal" for poi in nearby_pois)
        
        # Assess flood risk
        flood_risk = self._assess_flood_risk(None, address)  # Will use weather if available
        
        output = LocationOutput(
            formatted_address=display_name,
            neighborhood=neighborhood,
            district=district,
            nearest_intersection=intersection,
            jurisdiction=jurisdiction,
            department=department,
            coordinate_accuracy=coordinate_accuracy,
            raw_response=geocode_result,
            model_used="nominatim",
            
            # Enhanced fields
            weather=None,  # Will be populated below
            nearby_pois=[],  # Will be populated below
            road_type=road_details.get("road_type"),
            road_surface=road_details.get("road_surface"),
            speed_limit=road_details.get("speed_limit"),
            traffic_signals_nearby=road_details.get("traffic_signals", False),
            bus_stops_nearby=0,  # Will be updated
            flood_risk=flood_risk,
        )
        
        # Fetch weather and POIs after creating base output (to avoid blocking)
        weather = await self._get_weather_cached(input_data.latitude, input_data.longitude)
        nearby_pois = await self._get_pois_cached(input_data.latitude, input_data.longitude)
        
        # Update output with weather and POIs
        output.weather = weather
        output.nearby_pois = nearby_pois
        output.bus_stops_nearby = sum(1 for poi in nearby_pois if poi.poi_type == "bus_stop")
        output.traffic_signals_nearby = any(poi.poi_type == "traffic_signal" for poi in nearby_pois)
        
        # Re-assess flood risk with actual weather
        if weather:
            output.flood_risk = self._assess_flood_risk(weather, geocode_result.get("address", {}))
        
        logger.info(
            "location_geocoded_enhanced",
            complaint_id=str(complaint_id),
            address=display_name[:100],
            jurisdiction=jurisdiction,
            department=department,
            weather_condition=weather.condition if weather else None,
            pois_count=len(nearby_pois),
            bus_stops=output.bus_stops_nearby,
            flood_risk=output.flood_risk,
        )
        
        return AgentResult(success=True, output=output)
    
    async def _get_weather_cached(self, latitude: float, longitude: float) -> Optional[WeatherData]:
        # Check cache first (cache for 30 minutes)
        cached = await self.cache.get("weather", latitude, longitude)
        if cached:
            return WeatherData(**cached)
            
        weather = await self.weather_client.get_weather(latitude, longitude)
        if weather:
            await self.cache.set("weather", weather.model_dump(), latitude, longitude, ttl=1800)
        return weather
        
    async def _get_pois_cached(self, latitude: float, longitude: float) -> List[POIData]:
        # Check cache first (cache for 1 hour)
        cached = await self.cache.get("overpass", latitude, longitude)
        if cached:
            return [POIData(**poi) for poi in cached]
            
        pois = await self.overpass_client.get_nearby_pois(latitude, longitude)
        if pois:
            await self.cache.set("overpass", [poi.model_dump() for poi in pois], latitude, longitude, ttl=3600)
        return pois