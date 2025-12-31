"""
Capital Bikeshare Connector - Washington DC Bike Share System

Provides real-time data for:
- Station status (bikes available, docks available)
- Station information (location, capacity)

Uses the General Bikeshare Feed Specification (GBFS) - no API key required!
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from jarvis.agents.connectors.connector_base import Connector, ConnectorConfig

# Optional imports
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# Capital Bikeshare GBFS endpoints
GBFS_BASE_URL = "https://gbfs.capitalbikeshare.com/gbfs/en"
STATION_INFO = f"{GBFS_BASE_URL}/station_information.json"
STATION_STATUS = f"{GBFS_BASE_URL}/station_status.json"
SYSTEM_INFO = f"{GBFS_BASE_URL}/system_information.json"


class CapitalBikeshareConnector(Connector):
    """
    Capital Bikeshare connector for DC bike share.
    
    Uses GBFS (General Bikeshare Feed Specification) which is free and open.
    No API key required!
    
    Features:
    - Real-time bike availability
    - Station locations
    - Dock availability
    """
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._stations: Dict[str, Dict] = {}  # Cache station info
    
    @property
    def connector_type(self) -> str:
        return "capital_bikeshare"
    
    async def authenticate(self) -> bool:
        """GBFS is open - just verify connectivity"""
        if not HTTPX_AVAILABLE:
            print("Capital Bikeshare requires httpx. Run: pip install httpx")
            return False
        
        # Create client
        self._client = httpx.AsyncClient(timeout=10.0)
        
        # Test connectivity
        try:
            response = await self._client.get(SYSTEM_INFO)
            if response.status_code == 200:
                self._authenticated = True
                # Load station info
                await self._load_station_info()
                return True
            return False
        except Exception as e:
            print(f"Capital Bikeshare connection error: {e}")
            return False
    
    async def _load_station_info(self) -> None:
        """Load station information into cache"""
        try:
            response = await self._client.get(STATION_INFO)
            response.raise_for_status()
            
            data = response.json()
            stations = data.get("data", {}).get("stations", [])
            
            for station in stations:
                station_id = station.get("station_id")
                if station_id:
                    self._stations[station_id] = {
                        "id": station_id,
                        "name": station.get("name", ""),
                        "latitude": station.get("lat"),
                        "longitude": station.get("lon"),
                        "capacity": station.get("capacity", 0),
                        "address": station.get("address", ""),
                    }
        except Exception as e:
            print(f"Error loading station info: {e}")
    
    async def search(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get bike availability.
        
        Args:
            criteria: {
                "station": "Station name" (optional),
                "latitude": float (optional),
                "longitude": float (optional),
                "limit": 10,
            }
        """
        if not self._client:
            return []
        
        station_name = criteria.get("station", "").lower()
        lat = criteria.get("latitude")
        lon = criteria.get("longitude")
        limit = criteria.get("limit", 10)
        
        try:
            response = await self._client.get(STATION_STATUS)
            response.raise_for_status()
            
            data = response.json()
            statuses = data.get("data", {}).get("stations", [])
            
            results = []
            for status in statuses:
                station_id = status.get("station_id")
                station_info = self._stations.get(station_id, {})
                
                # Filter by name if provided
                if station_name:
                    info_name = station_info.get("name", "").lower()
                    if station_name not in info_name:
                        continue
                
                bikes_available = status.get("num_bikes_available", 0)
                docks_available = status.get("num_docks_available", 0)
                ebikes_available = status.get("num_ebikes_available", 0)
                
                results.append({
                    "station_id": station_id,
                    "name": station_info.get("name", f"Station {station_id}"),
                    "bikes_available": bikes_available,
                    "ebikes_available": ebikes_available,
                    "docks_available": docks_available,
                    "capacity": station_info.get("capacity", 0),
                    "latitude": station_info.get("latitude"),
                    "longitude": station_info.get("longitude"),
                    "address": station_info.get("address", ""),
                    "is_renting": status.get("is_renting", 0) == 1,
                    "is_returning": status.get("is_returning", 0) == 1,
                    "mode": "bikeshare",
                    "time": datetime.now().isoformat(),
                    "status": "Available" if bikes_available > 0 else "No bikes",
                })
            
            # Sort by bikes available (most first)
            results.sort(key=lambda x: x["bikes_available"], reverse=True)
            
            # If location provided, could sort by distance (future enhancement)
            
            return results[:limit]
            
        except Exception as e:
            print(f"Capital Bikeshare status error: {e}")
            return []
    
    async def execute_action(self, action_type: str, params: Dict[str, Any]) -> Any:
        """Bikeshare is read-only"""
        return {"status": "info_only"}
    
    async def get_nearby_stations(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float = 0.5,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get stations near a location.
        
        Args:
            latitude: User's latitude
            longitude: User's longitude
            radius_miles: Search radius in miles
            limit: Max stations to return
        """
        import math
        
        def haversine_distance(lat1, lon1, lat2, lon2):
            """Calculate distance in miles between two points"""
            R = 3959  # Earth's radius in miles
            
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            return R * c
        
        # Get all station status
        all_stations = await self.search({"limit": 500})
        
        # Calculate distances
        for station in all_stations:
            if station.get("latitude") and station.get("longitude"):
                station["distance_miles"] = haversine_distance(
                    latitude, longitude,
                    station["latitude"], station["longitude"]
                )
            else:
                station["distance_miles"] = float("inf")
        
        # Filter by radius and sort by distance
        nearby = [s for s in all_stations if s["distance_miles"] <= radius_miles]
        nearby.sort(key=lambda x: x["distance_miles"])
        
        return nearby[:limit]
