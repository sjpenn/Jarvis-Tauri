"""
Weather Connector - NOAA National Weather Service API (weather.gov)

FREE government API - No API key required!

Provides weather data for:
- Current conditions (from nearest observation station)
- 7-day forecasts (12-hour and hourly periods)
- Weather alerts
- Packing suggestions

API Documentation: https://www.weather.gov/documentation/services-web-api
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from jarvis.agents.connectors.connector_base import Connector, ConnectorConfig

# Optional imports
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# NOAA Weather.gov API endpoints
NWS_BASE_URL = "https://api.weather.gov"
POINTS_ENDPOINT = f"{NWS_BASE_URL}/points"
ALERTS_ENDPOINT = f"{NWS_BASE_URL}/alerts/active"

# User agent required by weather.gov
USER_AGENT = "JARVIS-Assistant (github.com/jarvis-assistant)"


class WeatherConnector(Connector):
    """
    NOAA National Weather Service API connector.
    
    FREE government weather API - No API key required!
    
    Provides:
    - 7-day forecasts (12-hour periods)
    - Hourly forecasts
    - Current conditions from observation stations
    - Active weather alerts
    
    Rate limits are generous for typical use.
    """
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._default_units = config.extra.get("units", "imperial")
        # Cache grid points to reduce API calls
        self._grid_cache: Dict[str, Dict[str, Any]] = {}
    
    @property
    def connector_type(self) -> str:
        return "weather"
    
    async def authenticate(self) -> bool:
        """Initialize the connector (no auth needed for weather.gov)"""
        if not HTTPX_AVAILABLE:
            print("Weather connector requires httpx. Run: pip install httpx")
            return False
        
        # Create client with required User-Agent header
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/geo+json",
            },
            timeout=15.0,
        )
        
        # Test connection
        try:
            response = await self._client.get(f"{NWS_BASE_URL}")
            if response.status_code == 200:
                self._authenticated = True
                print("✅ Connected to NOAA Weather Service (weather.gov) - No API key needed!")
                return True
            return False
        except Exception as e:
            print(f"Weather API connection error: {e}")
            return False
    
    async def search(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get weather data.
        
        Args:
            criteria: {
                "location": "Washington, DC" or {"lat": 38.9, "lon": -77.0},
                "type": "current" | "forecast" | "alerts" | "both",
                "days": 7,  # Up to 7 days for forecast
            }
        """
        if not self._client:
            return []
        
        location = criteria.get("location", "")
        query_type = criteria.get("type", "both")
        
        results = []
        
        # Get coordinates from location name if needed
        if isinstance(location, str):
            coords = await self._geocode(location)
        else:
            coords = location
        
        if not coords:
            return [{"error": f"Could not find location: {location}"}]
        
        # Get grid point info (required for NWS forecasts)
        grid_info = await self._get_grid_point(coords["lat"], coords["lon"])
        if not grid_info:
            return [{"error": "Location may not be in US coverage area"}]
        
        if query_type in ("current", "both"):
            current = await self._get_current_conditions(grid_info)
            if current:
                results.append({"type": "current", "data": current})
        
        if query_type in ("forecast", "both"):
            forecast = await self._get_forecast(grid_info, criteria.get("days", 7))
            if forecast:
                results.append({"type": "forecast", "data": forecast})
        
        if query_type in ("alerts", "both"):
            alerts = await self._get_alerts(coords)
            if alerts:
                results.append({"type": "alerts", "data": alerts})
        
        return results
    
    async def _geocode(self, location: str) -> Optional[Dict[str, float]]:
        """
        Convert location name to coordinates using a simple geocoding approach.
        
        For production, consider using Census Geocoder or similar.
        This uses some common city coordinates as fallback.
        """
        # Common US cities (expand as needed)
        known_locations = {
            "washington": {"lat": 38.9072, "lon": -77.0369, "name": "Washington, DC"},
            "washington dc": {"lat": 38.9072, "lon": -77.0369, "name": "Washington, DC"},
            "washington, dc": {"lat": 38.9072, "lon": -77.0369, "name": "Washington, DC"},
            "dc": {"lat": 38.9072, "lon": -77.0369, "name": "Washington, DC"},
            "new york": {"lat": 40.7128, "lon": -74.0060, "name": "New York, NY"},
            "nyc": {"lat": 40.7128, "lon": -74.0060, "name": "New York, NY"},
            "new york city": {"lat": 40.7128, "lon": -74.0060, "name": "New York, NY"},
            "los angeles": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
            "la": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
            "chicago": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
            "miami": {"lat": 25.7617, "lon": -80.1918, "name": "Miami, FL"},
            "dallas": {"lat": 32.7767, "lon": -96.7970, "name": "Dallas, TX"},
            "houston": {"lat": 29.7604, "lon": -95.3698, "name": "Houston, TX"},
            "phoenix": {"lat": 33.4484, "lon": -112.0740, "name": "Phoenix, AZ"},
            "philadelphia": {"lat": 39.9526, "lon": -75.1652, "name": "Philadelphia, PA"},
            "san antonio": {"lat": 29.4241, "lon": -98.4936, "name": "San Antonio, TX"},
            "san diego": {"lat": 32.7157, "lon": -117.1611, "name": "San Diego, CA"},
            "san francisco": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
            "seattle": {"lat": 47.6062, "lon": -122.3321, "name": "Seattle, WA"},
            "denver": {"lat": 39.7392, "lon": -104.9903, "name": "Denver, CO"},
            "boston": {"lat": 42.3601, "lon": -71.0589, "name": "Boston, MA"},
            "atlanta": {"lat": 33.7490, "lon": -84.3880, "name": "Atlanta, GA"},
            "las vegas": {"lat": 36.1699, "lon": -115.1398, "name": "Las Vegas, NV"},
            "portland": {"lat": 45.5152, "lon": -122.6784, "name": "Portland, OR"},
            "detroit": {"lat": 42.3314, "lon": -83.0458, "name": "Detroit, MI"},
            "minneapolis": {"lat": 44.9778, "lon": -93.2650, "name": "Minneapolis, MN"},
            "orlando": {"lat": 28.5383, "lon": -81.3792, "name": "Orlando, FL"},
            "tampa": {"lat": 27.9506, "lon": -82.4572, "name": "Tampa, FL"},
            "baltimore": {"lat": 39.2904, "lon": -76.6122, "name": "Baltimore, MD"},
            "charlotte": {"lat": 35.2271, "lon": -80.8431, "name": "Charlotte, NC"},
            "austin": {"lat": 30.2672, "lon": -97.7431, "name": "Austin, TX"},
            "nashville": {"lat": 36.1627, "lon": -86.7816, "name": "Nashville, TN"},
            "pittsburgh": {"lat": 40.4406, "lon": -79.9959, "name": "Pittsburgh, PA"},
            "cleveland": {"lat": 41.4993, "lon": -81.6944, "name": "Cleveland, OH"},
            "raleigh": {"lat": 35.7796, "lon": -78.6382, "name": "Raleigh, NC"},
            "richmond": {"lat": 37.5407, "lon": -77.4360, "name": "Richmond, VA"},
            "honolulu": {"lat": 21.3069, "lon": -157.8583, "name": "Honolulu, HI"},
            "anchorage": {"lat": 61.2181, "lon": -149.9003, "name": "Anchorage, AK"},
        }
        
        location_lower = location.lower().strip()
        
        # Check known locations
        if location_lower in known_locations:
            return known_locations[location_lower]
        
        # Check partial matches
        for key, coords in known_locations.items():
            if key in location_lower or location_lower in key:
                return coords
        
        # If no match found, try to extract coordinates if provided
        # Format: "lat,lon" or similar
        import re
        coord_match = re.match(r'([-\d.]+)[,\s]+([-\d.]+)', location)
        if coord_match:
            try:
                return {
                    "lat": float(coord_match.group(1)),
                    "lon": float(coord_match.group(2)),
                    "name": location,
                }
            except ValueError:
                pass
        
        # Default to DC if nothing matches
        print(f"Location '{location}' not found, defaulting to Washington, DC")
        return known_locations["washington dc"]
    
    async def _get_grid_point(
        self, 
        lat: float, 
        lon: float
    ) -> Optional[Dict[str, Any]]:
        """Get NWS grid point info for coordinates"""
        cache_key = f"{lat:.4f},{lon:.4f}"
        
        if cache_key in self._grid_cache:
            return self._grid_cache[cache_key]
        
        try:
            response = await self._client.get(f"{POINTS_ENDPOINT}/{lat},{lon}")
            
            if response.status_code != 200:
                print(f"Grid point error: {response.status_code}")
                return None
            
            data = response.json()
            properties = data.get("properties", {})
            
            grid_info = {
                "office": properties.get("gridId"),
                "gridX": properties.get("gridX"),
                "gridY": properties.get("gridY"),
                "forecast_url": properties.get("forecast"),
                "forecast_hourly_url": properties.get("forecastHourly"),
                "observation_stations_url": properties.get("observationStations"),
                "city": properties.get("relativeLocation", {}).get("properties", {}).get("city"),
                "state": properties.get("relativeLocation", {}).get("properties", {}).get("state"),
            }
            
            self._grid_cache[cache_key] = grid_info
            return grid_info
            
        except Exception as e:
            print(f"Grid point error: {e}")
            return None
    
    async def _get_current_conditions(
        self, 
        grid_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get current conditions from nearest observation station"""
        try:
            # Get observation stations
            stations_url = grid_info.get("observation_stations_url")
            if not stations_url:
                return None
            
            stations_response = await self._client.get(stations_url)
            if stations_response.status_code != 200:
                return None
            
            stations_data = stations_response.json()
            stations = stations_data.get("features", [])
            
            if not stations:
                return None
            
            # Get latest observation from first (nearest) station
            station_id = stations[0]["properties"]["stationIdentifier"]
            obs_url = f"{NWS_BASE_URL}/stations/{station_id}/observations/latest"
            
            obs_response = await self._client.get(obs_url)
            if obs_response.status_code != 200:
                return None
            
            obs_data = obs_response.json()
            props = obs_data.get("properties", {})
            
            # Convert temperature
            temp_c = props.get("temperature", {}).get("value")
            temp_f = (temp_c * 9/5 + 32) if temp_c is not None else None
            
            # Convert wind speed from m/s to mph
            wind_ms = props.get("windSpeed", {}).get("value")
            wind_mph = (wind_ms * 2.237) if wind_ms is not None else None
            
            # Convert visibility from m to miles
            vis_m = props.get("visibility", {}).get("value")
            vis_miles = (vis_m / 1609.34) if vis_m is not None else None
            
            return {
                "location": f"{grid_info.get('city', '')}, {grid_info.get('state', '')}",
                "station": station_id,
                "temperature": round(temp_f, 1) if temp_f else None,
                "temperature_unit": "F",
                "description": props.get("textDescription", ""),
                "humidity": props.get("relativeHumidity", {}).get("value"),
                "wind_speed": round(wind_mph, 1) if wind_mph else None,
                "wind_direction": self._degrees_to_direction(
                    props.get("windDirection", {}).get("value")
                ),
                "visibility": round(vis_miles, 1) if vis_miles else None,
                "pressure": props.get("barometricPressure", {}).get("value"),
                "timestamp": props.get("timestamp"),
                "icon": props.get("icon"),
            }
            
        except Exception as e:
            print(f"Current conditions error: {e}")
            return None
    
    async def _get_forecast(
        self, 
        grid_info: Dict[str, Any],
        days: int = 7
    ) -> Optional[List[Dict[str, Any]]]:
        """Get 7-day forecast (12-hour periods)"""
        try:
            forecast_url = grid_info.get("forecast_url")
            if not forecast_url:
                return None
            
            response = await self._client.get(forecast_url)
            if response.status_code != 200:
                print(f"Forecast error: {response.status_code}")
                return None
            
            data = response.json()
            periods = data.get("properties", {}).get("periods", [])
            
            results = []
            # Group periods by day (day + night = 1 day)
            day_forecasts = {}
            
            for period in periods:
                date_str = period.get("startTime", "")[:10]
                is_daytime = period.get("isDaytime", True)
                
                if date_str not in day_forecasts:
                    day_forecasts[date_str] = {
                        "date": date_str,
                        "high": None,
                        "low": None,
                        "description": "",
                        "detailed_forecast": "",
                        "icon": "",
                        "precipitation_chance": 0,
                        "wind_speed": "",
                        "wind_direction": "",
                    }
                
                temp = period.get("temperature")
                if is_daytime:
                    day_forecasts[date_str]["high"] = temp
                    day_forecasts[date_str]["description"] = period.get("shortForecast", "")
                    day_forecasts[date_str]["detailed_forecast"] = period.get("detailedForecast", "")
                    day_forecasts[date_str]["icon"] = period.get("icon", "")
                    day_forecasts[date_str]["wind_speed"] = period.get("windSpeed", "")
                    day_forecasts[date_str]["wind_direction"] = period.get("windDirection", "")
                else:
                    day_forecasts[date_str]["low"] = temp
                
                # Extract precipitation probability
                prob = period.get("probabilityOfPrecipitation", {}).get("value")
                if prob and prob > day_forecasts[date_str]["precipitation_chance"]:
                    day_forecasts[date_str]["precipitation_chance"] = prob
            
            # Convert to list
            for date_str in sorted(day_forecasts.keys())[:days]:
                results.append(day_forecasts[date_str])
            
            return results
            
        except Exception as e:
            print(f"Forecast error: {e}")
            return None
    
    async def _get_alerts(
        self, 
        coords: Dict[str, float]
    ) -> Optional[List[Dict[str, Any]]]:
        """Get active weather alerts for location"""
        try:
            response = await self._client.get(
                ALERTS_ENDPOINT,
                params={"point": f"{coords['lat']},{coords['lon']}"}
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            features = data.get("features", [])
            
            alerts = []
            for feature in features:
                props = feature.get("properties", {})
                alerts.append({
                    "event": props.get("event"),
                    "headline": props.get("headline"),
                    "description": props.get("description"),
                    "severity": props.get("severity"),
                    "urgency": props.get("urgency"),
                    "areas": props.get("areaDesc"),
                    "start": props.get("onset"),
                    "end": props.get("ends"),
                })
            
            return alerts
            
        except Exception as e:
            print(f"Alerts error: {e}")
            return None
    
    async def execute_action(self, action_type: str, params: Dict[str, Any]) -> Any:
        """Weather is read-only, no actions to execute"""
        return {"status": "info_only"}
    
    def _degrees_to_direction(self, degrees: Optional[float]) -> str:
        """Convert wind degrees to cardinal direction"""
        if degrees is None:
            return "N/A"
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        idx = round(degrees / 22.5) % 16
        return directions[idx]
    
    def get_packing_suggestions(self, forecast: List[Dict[str, Any]]) -> List[str]:
        """Generate packing suggestions based on forecast"""
        suggestions = set()
        
        for day in forecast:
            temp_high = day.get("high") or 70
            temp_low = day.get("low") or 50
            precip = day.get("precipitation_chance", 0)
            description = (day.get("description", "") + " " + day.get("detailed_forecast", "")).lower()
            
            # Temperature-based suggestions
            if temp_low and temp_low < 32:
                suggestions.add("Heavy winter coat")
                suggestions.add("Gloves and hat")
                suggestions.add("Warm layers")
            elif temp_low and temp_low < 50:
                suggestions.add("Jacket or sweater")
                suggestions.add("Long pants")
            
            if temp_high and temp_high > 85:
                suggestions.add("Light, breathable clothing")
                suggestions.add("Sunscreen")
                suggestions.add("Sunglasses")
                suggestions.add("Hat for sun protection")
            
            # Precipitation-based suggestions
            if precip > 30 or "rain" in description or "shower" in description:
                suggestions.add("Umbrella")
                suggestions.add("Rain jacket or poncho")
            
            if "snow" in description:
                suggestions.add("Waterproof boots")
                suggestions.add("Warm, waterproof jacket")
            
            if "thunderstorm" in description:
                suggestions.add("Umbrella")
                suggestions.add("Plan for indoor activities")
            
            # Wind-based suggestions
            if "wind" in description and ("strong" in description or "gusty" in description):
                suggestions.add("Windbreaker")
        
        return sorted(list(suggestions))
    
    async def get_weather_summary(self, location: str) -> str:
        """Get a natural language weather summary"""
        results = await self.search({
            "location": location,
            "type": "both",
            "days": 3,
        })
        
        if not results:
            return f"Unable to get weather for {location}"
        
        if "error" in results[0]:
            return results[0]["error"]
        
        current = None
        forecast = None
        
        for r in results:
            if r["type"] == "current":
                current = r["data"]
            elif r["type"] == "forecast":
                forecast = r["data"]
        
        parts = []
        
        if current:
            temp = current.get('temperature', 'N/A')
            parts.append(
                f"Currently in {current.get('location', location)}: {temp}°F, "
                f"{current.get('description', 'N/A')}. "
            )
            if current.get("humidity"):
                parts.append(f"Humidity: {current['humidity']:.0f}%. ")
            if current.get("wind_speed"):
                parts.append(
                    f"Wind: {current['wind_speed']} mph from the {current.get('wind_direction', 'N/A')}."
                )
        
        if forecast and len(forecast) > 0:
            today = forecast[0]
            parts.append(
                f"\nToday: High of {today.get('high', 'N/A')}°F. {today.get('description', '')}. "
                f"{today.get('precipitation_chance', 0)}% chance of precipitation."
            )
            
            if len(forecast) > 1:
                tomorrow = forecast[1]
                parts.append(
                    f"\nTomorrow: High {tomorrow.get('high', 'N/A')}°F, Low {tomorrow.get('low', 'N/A')}°F. "
                    f"{tomorrow.get('description', '')}."
                )
        
        return " ".join(parts)
