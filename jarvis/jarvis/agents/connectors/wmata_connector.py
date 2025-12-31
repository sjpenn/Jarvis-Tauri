"""
WMATA Connector - Washington Metropolitan Area Transit Authority API

Provides real-time data for:
- Metro rail arrivals
- Bus predictions
- Service alerts
- Station information

API Key: Get free key at https://developer.wmata.com/
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


# WMATA API endpoints
WMATA_BASE_URL = "https://api.wmata.com"
RAIL_PREDICTIONS = f"{WMATA_BASE_URL}/StationPrediction.svc/json/GetPrediction"
BUS_PREDICTIONS = f"{WMATA_BASE_URL}/NextBusService.svc/json/jPredictions"
RAIL_STATIONS = f"{WMATA_BASE_URL}/Rail.svc/json/jStations"
BUS_STOPS = f"{WMATA_BASE_URL}/Bus.svc/json/jStops"
ALERTS = f"{WMATA_BASE_URL}/Incidents.svc/json/Incidents"


# Common DC Metro stations with codes
STATION_CODES = {
    "metro center": "A01",
    "gallery place": "B01",
    "union station": "B03",
    "dupont circle": "A03",
    "foggy bottom": "C04",
    "farragut north": "A02",
    "farragut west": "C03",
    "mcpherson square": "C02",
    "federal triangle": "D01",
    "smithsonian": "D02",
    "l'enfant plaza": "D03",
    "pentagon": "C07",
    "pentagon city": "C08",
    "crystal city": "C09",
    "ronald reagan washington national airport": "C10",
    "national airport": "C10",
    "dca": "C10",
    "rosslyn": "C05",
    "clarendon": "K02",
    "ballston": "K04",
    "bethesda": "A09",
    "silver spring": "B09",
    "columbia heights": "E04",
    "u street": "E03",
    "shaw": "E02",
    "chinatown": "B01",
    "archives": "F02",
    "waterfront": "F04",
    "navy yard": "F05",
    "anacostia": "F06",
    "king street": "C13",
    "braddock road": "C12",
    "eastern market": "D06",
    "capitol south": "D05",
    "federal center sw": "D04",
    "judiciary square": "B02",
    "tenleytown": "A07",
    "friendship heights": "A08",
    "cleveland park": "A05",
    "woodley park": "A04",
    "noma": "B35",
    "noma-gallaudet": "B35",
}


class WMATAConnector(Connector):
    """
    WMATA API connector for DC Metro and Bus.
    
    Provides real-time arrival predictions for:
    - Metrorail (all lines: Red, Orange, Blue, Green, Yellow, Silver)
    - Metrobus (all routes)
    
    Features:
    - Station name to code resolution
    - Real-time predictions
    - Service alerts
    """
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key = config.api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def connector_type(self) -> str:
        return "wmata"
    
    async def authenticate(self) -> bool:
        """Verify API key works"""
        if not HTTPX_AVAILABLE:
            print("WMATA requires httpx. Run: pip install httpx")
            return False
        
        if not self._api_key:
            print("WMATA API key not configured")
            print("Get free key at: https://developer.wmata.com/")
            return False
        
        # Create client
        self._client = httpx.AsyncClient(
            headers={"api_key": self._api_key},
            timeout=10.0,
        )
        
        # Test API key
        try:
            response = await self._client.get(ALERTS)
            if response.status_code == 401:
                print("WMATA API key invalid")
                return False
            self._authenticated = True
            return True
        except Exception as e:
            print(f"WMATA connection error: {e}")
            return False
    
    async def search(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get real-time predictions.
        
        Args:
            criteria: {
                "station": "Metro Center" or station code,
                "mode": "metro" | "bus",
                "limit": 10,
            }
        """
        if not self._client:
            return []
        
        station = criteria.get("station", "")
        mode = criteria.get("mode", "metro")
        limit = criteria.get("limit", 10)
        
        results = []
        
        if mode in ("metro", "any"):
            rail_results = await self._get_rail_predictions(station, limit)
            results.extend(rail_results)
        
        if mode in ("bus", "any"):
            # Get bus predictions if we have a stop ID
            stop_id = criteria.get("stop_id")
            if stop_id:
                bus_results = await self._get_bus_predictions(stop_id, limit)
                results.extend(bus_results)
        
        return results[:limit]
    
    async def _get_rail_predictions(
        self, 
        station: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get Metro rail predictions for a station"""
        # Resolve station name to code
        station_code = self._resolve_station(station)
        
        if not station_code:
            # Try to get predictions for all stations matching partial name
            station_code = "All"
        
        try:
            url = f"{RAIL_PREDICTIONS}/{station_code}"
            response = await self._client.get(url)
            response.raise_for_status()
            
            data = response.json()
            trains = data.get("Trains", [])
            
            results = []
            for train in trains[:limit]:
                # Parse minutes
                min_str = train.get("Min", "")
                if min_str == "ARR":
                    minutes = 0
                elif min_str == "BRD":
                    minutes = 0
                elif min_str == "---":
                    continue
                else:
                    try:
                        minutes = int(min_str)
                    except ValueError:
                        minutes = 0
                
                # Calculate arrival time
                arrival_time = datetime.now()
                if minutes > 0:
                    from datetime import timedelta
                    arrival_time = arrival_time + timedelta(minutes=minutes)
                
                results.append({
                    "route": train.get("Line", ""),
                    "line": self._get_line_name(train.get("Line", "")),
                    "destination": train.get("DestinationName", ""),
                    "time": arrival_time.isoformat(),
                    "minutes_away": minutes,
                    "status": "Arriving" if min_str in ("ARR", "BRD") else "On Time",
                    "mode": "metro",
                    "cars": train.get("Car", ""),
                    "headsign": train.get("Destination", ""),
                })
            
            return results
            
        except Exception as e:
            print(f"WMATA rail prediction error: {e}")
            return []
    
    async def _get_bus_predictions(
        self,
        stop_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get Metrobus predictions for a stop"""
        try:
            url = f"{BUS_PREDICTIONS}?StopID={stop_id}"
            response = await self._client.get(url)
            response.raise_for_status()
            
            data = response.json()
            predictions = data.get("Predictions", [])
            
            results = []
            for pred in predictions[:limit]:
                # Parse minutes
                minutes = pred.get("Minutes", 0)
                
                # Calculate arrival time
                arrival_time = datetime.now()
                if minutes > 0:
                    from datetime import timedelta
                    arrival_time = arrival_time + timedelta(minutes=minutes)
                
                results.append({
                    "route": pred.get("RouteID", ""),
                    "destination": pred.get("DirectionText", ""),
                    "time": arrival_time.isoformat(),
                    "minutes_away": minutes,
                    "status": "On Time",
                    "mode": "bus",
                    "vehicle_id": pred.get("VehicleID", ""),
                    "headsign": pred.get("DirectionText", ""),
                })
            
            return results
            
        except Exception as e:
            print(f"WMATA bus prediction error: {e}")
            return []
    
    async def execute_action(self, action_type: str, params: Dict[str, Any]) -> Any:
        """WMATA is read-only, no actions to execute"""
        return {"status": "info_only"}
    
    def _resolve_station(self, station: str) -> Optional[str]:
        """Convert station name to WMATA station code"""
        if not station:
            return None
        
        # Check if already a code
        if len(station) == 3 and station[0].isalpha() and station[1:].isdigit():
            return station.upper()
        
        # Look up by name
        station_lower = station.lower().strip()
        
        # Exact match
        if station_lower in STATION_CODES:
            return STATION_CODES[station_lower]
        
        # Partial match
        for name, code in STATION_CODES.items():
            if station_lower in name or name in station_lower:
                return code
        
        return None
    
    def _get_line_name(self, line_code: str) -> str:
        """Convert line code to full name"""
        lines = {
            "RD": "Red Line",
            "OR": "Orange Line",
            "BL": "Blue Line",
            "GR": "Green Line",
            "YL": "Yellow Line",
            "SV": "Silver Line",
        }
        return lines.get(line_code, line_code)
    
    async def get_service_alerts(self) -> List[Dict[str, Any]]:
        """Get current service alerts"""
        if not self._client:
            return []
        
        try:
            response = await self._client.get(ALERTS)
            response.raise_for_status()
            
            data = response.json()
            incidents = data.get("Incidents", [])
            
            return [
                {
                    "type": inc.get("IncidentType", ""),
                    "description": inc.get("Description", ""),
                    "lines": inc.get("LinesAffected", "").split(";"),
                    "date": inc.get("DateUpdated", ""),
                }
                for inc in incidents
            ]
            
        except Exception as e:
            print(f"WMATA alerts error: {e}")
            return []
    
    async def get_all_stations(self) -> List[Dict[str, Any]]:
        """Get list of all Metro stations"""
        if not self._client:
            return []
        
        try:
            response = await self._client.get(RAIL_STATIONS)
            response.raise_for_status()
            
            data = response.json()
            stations = data.get("Stations", [])
            
            return [
                {
                    "code": s.get("Code", ""),
                    "name": s.get("Name", ""),
                    "lines": [
                        l for l in [
                            s.get("LineCode1"),
                            s.get("LineCode2"),
                            s.get("LineCode3"),
                            s.get("LineCode4"),
                        ] if l
                    ],
                    "latitude": s.get("Lat"),
                    "longitude": s.get("Lon"),
                }
                for s in stations
            ]
            
        except Exception as e:
            print(f"WMATA stations error: {e}")
            return []
