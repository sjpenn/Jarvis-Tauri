"""
JARVIS Transport Agent - Real-time transit and transportation information

Supports multiple transportation types simultaneously:
- Metro/Subway (WMATA, MTA, BART, etc.)
- Bus systems
- Commuter rail (Amtrak, MARC, VRE, etc.)
- Rideshare estimates
- Bike share availability

Location-aware with multi-region support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from jarvis.agents.agent_base import Agent, DraftAction
from jarvis.agents.connectors.connector_base import Connector
from jarvis.agents.connectors.maps_connector import MapsConnector


class TransportMode(Enum):
    """Types of transportation"""
    METRO = "metro"           # Subway/Metro
    BUS = "bus"               # Local bus
    COMMUTER_RAIL = "rail"    # Amtrak, MARC, VRE, etc.
    LIGHT_RAIL = "light_rail" # Streetcar, light rail
    RIDESHARE = "rideshare"   # Uber, Lyft estimates
    BIKESHARE = "bikeshare"   # Capital Bikeshare, etc.
    SCOOTER = "scooter"       # Electric scooters
    FERRY = "ferry"           # Water taxi, ferries
    ANY = "any"               # All modes


@dataclass
class Departure:
    """A transit departure"""
    route: str               # Train line, bus route, etc.
    destination: str         # Final destination
    time: datetime           # Departure time
    mode: TransportMode = TransportMode.ANY
    status: str = "On Time"  # On Time, Delayed, Cancelled
    track: Optional[str] = None
    platform: Optional[str] = None
    minutes_away: Optional[int] = None
    provider: str = ""       # Which transit system (WMATA, Amtrak, etc.)
    headsign: Optional[str] = None  # Display text on vehicle
    alerts: List[str] = field(default_factory=list)


@dataclass
class Station:
    """A transit station/stop"""
    id: str
    name: str
    modes: List[TransportMode] = field(default_factory=list)
    lines: List[str] = field(default_factory=list)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    provider: str = ""


@dataclass 
class TransportLocation:
    """A configured location with transit preferences"""
    name: str                    # "home", "work", "dc"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    preferred_stations: List[str] = field(default_factory=list)
    preferred_modes: List[TransportMode] = field(default_factory=list)


@dataclass
class TransportProvider:
    """Configuration for a transit provider"""
    name: str                    # "wmata", "amtrak", "marc"
    display_name: str            # "WMATA Metro", "Amtrak"
    modes: List[TransportMode] = field(default_factory=list)
    api_key: Optional[str] = None
    enabled: bool = True
    region: Optional[str] = None  # "dc", "nyc", "sf"


class TransportAgent(Agent):
    """
    Multi-modal transportation agent.
    
    Supports multiple providers and transport modes simultaneously.
    Location-aware with configurable regions.
    
    Features:
    - Real-time departure information across all modes
    - Station/stop search
    - Service alerts
    - Multi-provider aggregation
    - Location-based defaults
    
    Example Config (models.yaml):
    ```yaml
    agents:
      transport:
        enabled: true
        location: dc
        locations:
          dc:
            latitude: 38.9072
            longitude: -77.0369
            preferred_stations: ["Metro Center", "Union Station"]
            preferred_modes: [metro, bus, rail]
        providers:
          - name: wmata
            display_name: "WMATA Metro & Bus"
            modes: [metro, bus]
            api_key: ${WMATA_API_KEY}
          - name: amtrak
            display_name: "Amtrak"
            modes: [rail]
          - name: marc
            display_name: "MARC Train"
            modes: [rail]
          - name: vre
            display_name: "VRE"
            modes: [rail]
          - name: capital_bikeshare
            display_name: "Capital Bikeshare"
            modes: [bikeshare]
    ```
    """
    
    def __init__(self):
        super().__init__()
        self._locations: Dict[str, TransportLocation] = {}
        self._providers: Dict[str, TransportProvider] = {}
        self._current_location: Optional[str] = None
        self._home_station: Optional[str] = None
        self._default_modes: Set[TransportMode] = {TransportMode.ANY}
    
    @property
    def name(self) -> str:
        return "transport"
    
    @property
    def description(self) -> str:
        return "Get real-time transit info - Metro, bus, Amtrak, rideshare, bikeshare"
    
    def configure(
        self,
        home_station: Optional[str] = None,
        default_destination: Optional[str] = None,
        current_location: Optional[str] = None,
        locations: Optional[Dict[str, dict]] = None,
        providers: Optional[List[dict]] = None,
    ) -> None:
        """
        Configure transport agent with locations and providers.
        
        Args:
            home_station: Default departure station
            default_destination: Default arrival station
            current_location: Key into locations dict (e.g., "dc")
            locations: Dict of named locations with preferences
            providers: List of transit provider configurations
        """
        self._home_station = home_station
        self._current_location = current_location
        
        # Parse locations
        if locations:
            for name, loc_data in locations.items():
                modes = [
                    TransportMode(m) if isinstance(m, str) else m 
                    for m in loc_data.get("preferred_modes", [])
                ]
                self._locations[name] = TransportLocation(
                    name=name,
                    latitude=loc_data.get("latitude"),
                    longitude=loc_data.get("longitude"),
                    address=loc_data.get("address"),
                    preferred_stations=loc_data.get("preferred_stations", []),
                    preferred_modes=modes,
                )
        
        # Parse providers
        if providers:
            for prov_data in providers:
                modes = [
                    TransportMode(m) if isinstance(m, str) else m 
                    for m in prov_data.get("modes", ["any"])
                ]
                self._providers[prov_data["name"]] = TransportProvider(
                    name=prov_data["name"],
                    display_name=prov_data.get("display_name", prov_data["name"]),
                    modes=modes,
                    api_key=prov_data.get("api_key"),
                    enabled=prov_data.get("enabled", True),
                    region=prov_data.get("region"),
                )
        
        # Set default modes from current location
        if current_location and current_location in self._locations:
            loc = self._locations[current_location]
            if loc.preferred_modes:
                self._default_modes = set(loc.preferred_modes)
    
    def add_location(self, location: TransportLocation) -> None:
        """Add a named location"""
        self._locations[location.name] = location
    
    def add_provider(self, provider: TransportProvider) -> None:
        """Add a transit provider"""
        self._providers[provider.name] = provider
    
    async def understand(self, query: str) -> Dict[str, Any]:
        """Parse transport-related intent"""
        query_lower = query.lower()
        
        # Detect transport mode
        mode = TransportMode.ANY
        if any(w in query_lower for w in ["metro", "subway", "train"]):
            mode = TransportMode.METRO
        elif "bus" in query_lower:
            mode = TransportMode.BUS
        elif any(w in query_lower for w in ["amtrak", "marc", "vre", "commuter"]):
            mode = TransportMode.COMMUTER_RAIL
        elif any(w in query_lower for w in ["uber", "lyft", "rideshare"]):
            mode = TransportMode.RIDESHARE
        elif any(w in query_lower for w in ["bike", "bikeshare", "capital bike"]):
            mode = TransportMode.BIKESHARE
        
        # Detect station mentions
        station = None
        destination = None
        
        if "from" in query_lower:
            parts = query_lower.split("from")
            if len(parts) > 1:
                # Take words until "to" or end
                rest = parts[1].strip()
                if " to " in rest:
                    station = rest.split(" to ")[0].strip()
                else:
                    station = " ".join(rest.split()[:4])
        
        if " to " in query_lower:
            parts = query_lower.split(" to ")
            if len(parts) > 1:
                destination = " ".join(parts[-1].strip().split()[:4])
        
        # Use defaults if not specified
        if not station:
            station = self._get_default_station()
        
        return {
            "action": "departures",
            "station": station or "current_location",
            "destination": destination,
            "mode": mode.value,
            "query": query,
        }
    
    async def search(self, criteria: Dict[str, Any]) -> List[Departure]:
        """
        Get departure information across all configured providers.
        
        Args:
            criteria: {
                "station": "Metro Center" or "current_location",
                "destination": "Union Station" (optional),
                "mode": "metro" | "bus" | "rail" | "any",
                "limit": 10,
                "providers": ["wmata", "amtrak"] (optional, defaults to all)
            }
        """
        station = criteria.get("station", self._home_station)
        destination = criteria.get("destination")
        mode_str = criteria.get("mode", "any")
        mode = TransportMode(mode_str) if isinstance(mode_str, str) else mode_str
        limit = criteria.get("limit", 10)
        provider_filter = criteria.get("providers")
        
        all_departures: List[Departure] = []
        
        # Query each connector
        for connector in self._connectors:
            # Filter by provider if specified
            if provider_filter and connector.config.name not in provider_filter:
                continue
            
            # Get provider config
            provider = self._providers.get(connector.config.name)
            
            # Filter by mode if provider has mode restrictions
            if provider and mode != TransportMode.ANY:
                if mode not in provider.modes:
                    continue
            
            try:
                results = await connector.search({
                    "station": station,
                    "destination": destination,
                    "mode": mode.value,
                    "limit": limit,
                })
                
                for dep_data in results:
                    departure = self._normalize_departure(dep_data, connector.config.name)
                    all_departures.append(departure)
                    
            except Exception as e:
                print(f"Error getting departures from {connector.name}: {e}")
        
        # If no connectors, show helpful info about DC transit
        if not self._connectors:
            return self._get_dc_setup_info(station, mode)
        
        # Sort by departure time
        all_departures.sort(key=lambda d: d.time)
        
        # Filter by mode if needed
        if mode != TransportMode.ANY:
            all_departures = [d for d in all_departures if d.mode == mode]
        
        return all_departures[:limit]
    
    async def propose_action(self, intent: Dict[str, Any]) -> DraftAction:
        """Transport agent is informational only"""
        return DraftAction(
            agent=self.name,
            action_type="info_only",
            description="Transport queries are informational - no action needed.",
            params=intent,
        )
    
    async def execute(self, action: DraftAction) -> str:
        """Transport agent actions are informational"""
        return "Transport information retrieved"
    
    def _normalize_departure(self, data: Dict[str, Any], provider: str) -> Departure:
        """Convert connector data to unified Departure"""
        time = data.get("time")
        if isinstance(time, str):
            try:
                time = datetime.fromisoformat(time)
            except Exception:
                time = datetime.now()
        elif not isinstance(time, datetime):
            time = datetime.now()
        
        minutes_away = None
        if time:
            delta = time - datetime.now()
            minutes_away = max(0, int(delta.total_seconds() / 60))
        
        # Parse mode
        mode_str = data.get("mode", "any")
        try:
            mode = TransportMode(mode_str)
        except ValueError:
            mode = TransportMode.ANY
        
        return Departure(
            route=data.get("route", data.get("line", "")),
            destination=data.get("destination", ""),
            time=time,
            mode=mode,
            status=data.get("status", "On Time"),
            track=data.get("track"),
            platform=data.get("platform"),
            minutes_away=minutes_away,
            provider=provider,
            headsign=data.get("headsign"),
            alerts=data.get("alerts", []),
        )
    
    def _get_default_station(self) -> Optional[str]:
        """Get default station based on current location"""
        if self._home_station:
            return self._home_station
        
        if self._current_location and self._current_location in self._locations:
            loc = self._locations[self._current_location]
            if loc.preferred_stations:
                return loc.preferred_stations[0]
        
        return None
    
    def _get_dc_setup_info(
        self,
        station: Optional[str],
        mode: TransportMode,
    ) -> List[Departure]:
        """Return DC-specific setup information"""
        now = datetime.now()
        
        info_lines = [
            Departure(
                route="🚇 WMATA Metro",
                destination="Get API key at developer.wmata.com",
                time=now,
                mode=TransportMode.METRO,
                status="Not configured",
                provider="wmata",
            ),
            Departure(
                route="🚌 WMATA Bus",
                destination="Same API key as Metro",
                time=now,
                mode=TransportMode.BUS,
                status="Not configured",
                provider="wmata",
            ),
            Departure(
                route="🚆 Amtrak",
                destination="amtrak.com API program",
                time=now,
                mode=TransportMode.COMMUTER_RAIL,
                status="Not configured",
                provider="amtrak",
            ),
            Departure(
                route="🚃 MARC Train",
                destination="mta.maryland.gov",
                time=now,
                mode=TransportMode.COMMUTER_RAIL,
                status="Not configured",
                provider="marc",
            ),
            Departure(
                route="🚃 VRE",
                destination="vre.org",
                time=now,
                mode=TransportMode.COMMUTER_RAIL,
                status="Not configured",
                provider="vre",
            ),
            Departure(
                route="🚲 Capital Bikeshare",
                destination="GBFS feed - no API key needed",
                time=now,
                mode=TransportMode.BIKESHARE,
                status="Available",
                provider="capital_bikeshare",
            ),
        ]
        
        return info_lines
    
    def get_capabilities(self) -> List[str]:
        capabilities = []
        
        # List configured providers
        for provider in self._providers.values():
            if provider.enabled:
                modes = ", ".join(m.value for m in provider.modes)
                capabilities.append(f"{provider.display_name} ({modes})")
        
        if not self._providers:
            capabilities.append("Configure transit providers in models.yaml")
        
        if self._home_station:
            capabilities.append(f"Default station: {self._home_station}")
        
        return capabilities
    
    async def get_next_departure(
        self,
        station: Optional[str] = None,
        destination: Optional[str] = None,
        mode: TransportMode = TransportMode.ANY,
    ) -> Optional[Departure]:
        """Get the very next departure"""
        station = station or self._get_default_station()
        
        departures = await self.search({
            "station": station,
            "destination": destination,
            "mode": mode.value,
            "limit": 1,
        })
        
        return departures[0] if departures else None
    
    async def get_all_modes_from(
        self,
        station: str,
        limit_per_mode: int = 3,
    ) -> Dict[TransportMode, List[Departure]]:
        """Get departures grouped by transport mode"""
        results: Dict[TransportMode, List[Departure]] = {}
        
        for mode in TransportMode:
            if mode == TransportMode.ANY:
                continue
            
            departures = await self.search({
                "station": station,
                "mode": mode.value,
                "limit": limit_per_mode,
            })
            
            if departures:
                results[mode] = departures
        
        return results

    async def get_travel_estimate(self, start: str, end: str, mode: TransportMode = TransportMode.RIDESHARE) -> Dict[str, Any]:
        """
        Get travel time estimate between two points.
        Uses MapsConnector if available, or falls back to basic estimation.
        """
        # Try to find a maps connector
        maps_connector = None
        for conn in self._connectors:
             if isinstance(conn, MapsConnector):
                 maps_connector = conn
                 break
        
        if not maps_connector:
            # Fallback: Just return a link
            return {
                "status": "link_only",
                "maps_url": f"http://maps.apple.com/?saddr={start.replace(' ', '+')}&daddr={end.replace(' ', '+')}"
            }
            
        return await maps_connector.get_travel_time(start, end, "transit" if mode in [TransportMode.METRO, TransportMode.BUS, TransportMode.COMMUTER_RAIL] else "driving")
