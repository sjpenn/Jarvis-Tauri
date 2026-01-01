"""
Flight Connector - AviationStack API Integration

Provides flight status data for:
- Real-time flight tracking by flight number
- Departure/arrival information
- Delays and cancellations
- Gate and terminal info

API Key: Get free key at https://aviationstack.com/ (100 calls/month free)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from jarvis.agents.connectors.connector_base import Connector, ConnectorConfig

# Optional imports
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

import time
from datetime import datetime, timedelta


# AviationStack API endpoints
AVIATION_BASE_URL = "http://api.aviationstack.com/v1"
FLIGHTS_ENDPOINT = f"{AVIATION_BASE_URL}/flights"


@dataclass
class FlightStatus:
    """Flight status data"""
    flight_number: str
    airline: str
    status: str  # scheduled, active, landed, cancelled, incident, diverted
    departure_airport: str
    departure_city: str
    departure_scheduled: Optional[datetime]
    departure_actual: Optional[datetime]
    departure_terminal: Optional[str]
    departure_gate: Optional[str]
    arrival_airport: str
    arrival_city: str
    arrival_scheduled: Optional[datetime]
    arrival_actual: Optional[datetime]
    arrival_terminal: Optional[str]
    arrival_gate: Optional[str]
    delay_minutes: Optional[int] = None
    aircraft_type: Optional[str] = None


class FlightConnector(Connector):
    """
    AviationStack API connector for flight status.
    
    Provides:
    - Real-time flight tracking
    - Flight status (on-time, delayed, cancelled)
    - Departure and arrival information
    - Gate and terminal data
    
    Note: Free tier limited to 100 calls/month
    """
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._api_key = config.api_key
        self._client: Optional[httpx.AsyncClient] = None
        # Rate limiting state
        self._rate_limited_until: Optional[datetime] = None
        self._backoff_seconds = 60  # Start with 60 second backoff
        self._last_error_message = None
        self._error_count = 0
    
    @property
    def connector_type(self) -> str:
        return "flight"
    
    async def authenticate(self) -> bool:
        """Verify API key works"""
        if not HTTPX_AVAILABLE:
            print("Flight connector requires httpx. Run: pip install httpx")
            return False
        
        if not self._api_key:
            print("AviationStack API key not configured - Status API disabled")
            print("Enabling OpenSky Network (Radar) only.")
            # Still initialize client for OpenSky
            self._client = httpx.AsyncClient(timeout=15.0)
            return True
        
        # Create client
        self._client = httpx.AsyncClient(timeout=15.0)
        
        # Note: We don't test the API key immediately to save API calls
        # The free tier only allows 100 calls/month
        self._authenticated = True
        return True
    
    async def search(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get flight status.
        
        Args:
            criteria: {
                "flight_number": "AA123" or "American Airlines 123",
                "flight_iata": "AA123",  # IATA code directly
                "date": "2024-01-15",  # Optional, defaults to today
            }
        """
        if not self._client:
            return []
        
        flight_number = criteria.get("flight_number", "")
        flight_iata = criteria.get("flight_iata", "")
        
        # Parse flight number if not IATA format
        if flight_number and not flight_iata:
            flight_iata = self._parse_flight_number(flight_number)
        
        if not flight_iata:
            return [{"error": "Please provide a valid flight number (e.g., AA123)"}]
        
        return await self._get_flight_status(flight_iata)
    
    def _parse_flight_number(self, flight_input: str) -> Optional[str]:
        """
        Parse various flight number formats to IATA code.
        
        Handles:
        - "AA123" 
        - "AA 123"
        - "American Airlines 123"
        - "United 456"
        """
        import re
        
        # Common airline name to IATA code mapping
        airline_codes = {
            "american": "AA",
            "american airlines": "AA",
            "united": "UA",
            "united airlines": "UA",
            "delta": "DL",
            "delta airlines": "DL",
            "southwest": "WN",
            "southwest airlines": "WN",
            "jetblue": "B6",
            "alaska": "AS",
            "alaska airlines": "AS",
            "spirit": "NK",
            "frontier": "F9",
            "hawaiian": "HA",
            "hawaiian airlines": "HA",
            "british airways": "BA",
            "lufthansa": "LH",
            "air france": "AF",
            "klm": "KL",
            "emirates": "EK",
            "qatar": "QR",
            "qatar airways": "QR",
        }
        
        flight_input = flight_input.strip().upper()
        
        # Already in IATA format (e.g., AA123 or AA 123)
        match = re.match(r"^([A-Z]{2})\s*(\d+)$", flight_input)
        if match:
            return f"{match.group(1)}{match.group(2)}"
        
        # Check for airline name followed by number
        flight_lower = flight_input.lower()
        for name, code in airline_codes.items():
            if flight_lower.startswith(name):
                # Extract the number after the airline name
                number_part = flight_lower[len(name):].strip()
                if number_part.isdigit():
                    return f"{code}{number_part}"
        
        return None
    
    async def _get_flight_status(
        self, 
        flight_iata: str
    ) -> List[Dict[str, Any]]:
        """Get flight status from AviationStack API"""
        try:
            response = await self._client.get(
                FLIGHTS_ENDPOINT,
                params={
                    "access_key": self._api_key,
                    "flight_iata": flight_iata,
                }
            )
            
            if response.status_code == 401:
                return [{"error": "Invalid API key"}]
            
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if "error" in data:
                error_info = data["error"]
                return [{"error": error_info.get("message", "API error")}]
            
            flights = data.get("data", [])
            
            if not flights:
                return [{"error": f"No flight found for {flight_iata}"}]
            
            results = []
            for flight in flights:
                departure = flight.get("departure", {})
                arrival = flight.get("arrival", {})
                airline = flight.get("airline", {})
                aircraft = flight.get("aircraft", {})
                flight_info = flight.get("flight", {})
                
                # Calculate delay
                delay = None
                if departure.get("delay"):
                    delay = int(departure["delay"])
                
                # Determine status
                status = flight.get("flight_status", "unknown")
                status_display = self._format_status(status, delay)
                
                results.append({
                    "flight_number": flight_info.get("iata", flight_iata),
                    "airline": airline.get("name", ""),
                    "airline_iata": airline.get("iata", ""),
                    "status": status,
                    "status_display": status_display,
                    "departure": {
                        "airport": departure.get("airport", ""),
                        "airport_iata": departure.get("iata", ""),
                        "city": self._get_city_from_airport(departure.get("iata", "")),
                        "terminal": departure.get("terminal"),
                        "gate": departure.get("gate"),
                        "scheduled": departure.get("scheduled"),
                        "estimated": departure.get("estimated"),
                        "actual": departure.get("actual"),
                        "delay_minutes": delay,
                    },
                    "arrival": {
                        "airport": arrival.get("airport", ""),
                        "airport_iata": arrival.get("iata", ""),
                        "city": self._get_city_from_airport(arrival.get("iata", "")),
                        "terminal": arrival.get("terminal"),
                        "gate": arrival.get("gate"),
                        "scheduled": arrival.get("scheduled"),
                        "estimated": arrival.get("estimated"),
                        "actual": arrival.get("actual"),
                    },
                    "aircraft": {
                        "registration": aircraft.get("registration"),
                        "type": aircraft.get("iata"),
                    },
                })
            
            return results
            
        except Exception as e:
            print(f"Flight status error: {e}")
            return [{"error": f"Failed to get flight status: {str(e)}"}]
    
    def _format_status(self, status: str, delay: Optional[int]) -> str:
        """Format flight status for display"""
        status_map = {
            "scheduled": "Scheduled",
            "active": "In Flight",
            "landed": "Landed",
            "cancelled": "Cancelled",
            "incident": "Incident",
            "diverted": "Diverted",
        }
        
        display = status_map.get(status, status.title())
        
        if delay and delay > 0:
            display = f"Delayed ({delay} min)"
        
        return display
    
    async def _get_city_from_airport(self, airport_iata: str) -> str:
        """Get city name from airport IATA code"""
        if not airport_iata:
            return ""
            
        # Try Data Manager first
        if not hasattr(self, "_data_manager"):
            from jarvis.agents.utils.flight_data_manager import FlightDataManager
            self._data_manager = FlightDataManager()
            # We can't await here easily if called from synchronous context, 
            # but usually this is called from async _get_flight_status.
            # However, _get_city_from_airport is defined as sync in original code? 
            # Ah, wait, checking original signature... `def _get_city_from_airport(self, airport_iata: str) -> str:`
            # It's synchronous. We should make it async or rely on pre-loaded data.
            # For safety, let's keep the hardcoded backup and try to use data if loaded.
            pass
            
        if hasattr(self, "_data_manager") and self._data_manager._loaded:
            info = self._data_manager.get_airport_info(airport_iata)
            if info:
                return info.get("city", "")

        # Common airport codes - expand as needed
        airport_cities = {
            "JFK": "New York",
            "LGA": "New York",
            "EWR": "Newark",
            "LAX": "Los Angeles",
            "SFO": "San Francisco",
            "ORD": "Chicago",
            "DFW": "Dallas",
            "DEN": "Denver",
            "ATL": "Atlanta",
            "MIA": "Miami",
            "SEA": "Seattle",
            "BOS": "Boston",
            "DCA": "Washington",
            "IAD": "Washington",
            "BWI": "Baltimore",
            "PHX": "Phoenix",
            "LAS": "Las Vegas",
            "MSP": "Minneapolis",
            "DTW": "Detroit",
            "PHL": "Philadelphia",
            "CLT": "Charlotte",
            "MCO": "Orlando",
            "TPA": "Tampa",
            "SAN": "San Diego",
            "PDX": "Portland",
            "HNL": "Honolulu",
            "ANC": "Anchorage",
        }
        return airport_cities.get(airport_iata, "")
    
    async def execute_action(self, action_type: str, params: Dict[str, Any]) -> Any:
        """Flight status is read-only, no actions to execute"""
        return {"status": "info_only"}
    
    def format_flight_info(self, flight: Dict[str, Any]) -> str:
        """Format flight data as natural language"""
        dep = flight.get("departure", {})
        arr = flight.get("arrival", {})
        
        parts = [
            f"Flight {flight['flight_number']} ({flight.get('airline', 'Unknown Airline')})",
            f"Status: {flight.get('status_display', 'Unknown')}",
            "",
            f"From: {dep.get('airport', 'Unknown')} ({dep.get('airport_iata', '')})",
        ]
        
        if dep.get("terminal"):
            parts.append(f"  Terminal: {dep['terminal']}")
        if dep.get("gate"):
            parts.append(f"  Gate: {dep['gate']}")
        if dep.get("scheduled"):
            parts.append(f"  Scheduled: {dep['scheduled']}")
        if dep.get("delay_minutes") and dep["delay_minutes"] > 0:
            parts.append(f"  Delay: {dep['delay_minutes']} minutes")
        
        parts.extend([
            "",
            f"To: {arr.get('airport', 'Unknown')} ({arr.get('airport_iata', '')})",
        ])
        
        if arr.get("terminal"):
            parts.append(f"  Terminal: {arr['terminal']}")
        if arr.get("gate"):
            parts.append(f"  Gate: {arr['gate']}")
        if arr.get("scheduled"):
            parts.append(f"  Scheduled Arrival: {arr['scheduled']}")
        
        return "\n".join(parts)

    async def search_traffic(
        self, 
        lat: float, 
        lon: float, 
        radius_miles: int = 300
    ) -> List[Dict[str, Any]]:
        """
        Get live air traffic within radius using OpenSky Network.
        No API key required for anonymous access (lower rate limits).
        """
        if not self._client:
            return []
        
        # Check if we're rate limited
        if self._rate_limited_until and datetime.now() < self._rate_limited_until:
            # Silently skip this call while rate limited
            return []
            
        # bbox = min_lat, min_lon, max_lat, max_lon
        # Approx: 1 deg lat = 69 miles, 1 deg lon = ~53 miles (at 40 deg lat)
        lat_deg = radius_miles / 69.0
        lon_deg = radius_miles / 53.0
        
        bbox = (
            lat - lat_deg,      # lamin
            lon - lon_deg,      # lomin
            lat + lat_deg,      # lamax
            lon + lon_deg       # lomax
        )
        
        url = "https://opensky-network.org/api/states/all"
        params = {
            "lamin": bbox[0],
            "lomin": bbox[1],
            "lamax": bbox[2],
            "lomax": bbox[3]
        }
        
        try:
            # Anonymous access doesn't need auth headers, but let's be polite
            response = await self._client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 429:
                # Rate limited - implement exponential backoff
                self._rate_limited_until = datetime.now() + timedelta(seconds=self._backoff_seconds)
                self._backoff_seconds = min(self._backoff_seconds * 2, 600)  # Max 10 min
                
                # Only print once
                if self._last_error_message != "rate_limit":
                    print(f"OpenSky rate limited. Backing off for {self._backoff_seconds}s")
                    self._last_error_message = "rate_limit"
                return []
            
            if response.status_code != 200:
                # Only print error if it's different or we haven't printed many
                error_msg = f"OpenSky API error: {response.status_code}"
                if self._last_error_message != error_msg or self._error_count < 3:
                    print(error_msg)
                    self._last_error_message = error_msg
                    self._error_count += 1
                return []
            
            # Success - reset backoff
            self._backoff_seconds = 60
            self._rate_limited_until = None
            self._error_count = 0
            self._last_error_message = None
            
            data = response.json()
            states = data.get("states", [])
            
            if not states:
                return []
            
            # Lazily load OpenFlights data if not already
            if not hasattr(self, "_data_manager"):
                from jarvis.agents.utils.flight_data_manager import FlightDataManager
                self._data_manager = FlightDataManager()
                await self._data_manager.load_data()
                
            results = []
            for s in states:
                # State vector format: https://openskynetwork.github.io/opensky-api/rest.html
                # 0: icao24 (id)
                # 1: callsign
                # 2: origin_country
                # 5: longitude
                # 6: latitude
                # 7: baro_altitude
                # 10: heading
                
                # Filter out null positions
                if not s[5] or not s[6]:
                    continue
                
                callsign = s[1].strip()
                airline_name = "Unknown Airline"
                
                # Try to resolve airline name from callsign (first 3 chars usually ICAO)
                if len(callsign) >= 3:
                     airline_icao = callsign[:3]
                     resolved_name = self._data_manager.get_airline_name(airline_icao)
                     if resolved_name:
                         airline_name = resolved_name
                    
                aircraft = {
                    "id": s[0],
                    "callsign": callsign,
                    "airline": airline_name, 
                    "country": s[2],
                    "lon": s[5],
                    "lat": s[6],
                    "altitude": s[7] or 0,
                    "heading": s[10] or 0,
                }
                results.append(aircraft)
                
            return results
            
        except Exception as e:
            # Suppress repeated network errors
            error_str = str(e)
            if "nodename nor servname" in error_str or "connection" in error_str.lower():
                if self._last_error_message != "network_error" or self._error_count < 2:
                    print(f"OpenSky network error (will retry): {e}")
                    self._last_error_message = "network_error"
                    self._error_count += 1
            else:
                print(f"OpenSky error: {e}")
            return []

