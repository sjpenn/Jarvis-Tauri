"""
Amtrak Connector - Live Train Status via Amtraker API

Provides real-time data for:
- Train arrivals/departures at stations
- Live train tracking (position, delays, status)
- Station information

No API key required! Uses the free Amtraker API (api-v3.amtraker.com)
which proxies Amtrak's public data.

Endpoints (v3):
- /v3/trains/{train_number} - Specific train details
- /v3/stations/{station_code} - Station info and train list
- /v3/trains - All active trains
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import aiohttp

from .connector_base import Connector, ConnectorConfig


logger = logging.getLogger(__name__)

# Amtraker API v3 - free, no auth required
AMTRAKER_BASE_URL = "https://api-v3.amtraker.com"

# Common Amtrak station codes for DC area and Northeast Corridor
STATION_CODES = {
    # DC Area
    "washington union station": "WAS",
    "union station": "WAS",
    "washington dc": "WAS",
    "alexandria": "ALX",
    "new carrollton": "NCR",
    
    # Northeast Corridor
    "new york penn": "NYP",
    "new york": "NYP",
    "penn station": "NYP",
    "philadelphia": "PHL",
    "30th street": "PHL",
    "baltimore penn": "BAL",
    "baltimore": "BAL",
    "wilmington": "WIL",
    "trenton": "TRE",
    "newark": "NWK",
    "boston south": "BOS",
    "boston": "BOS",
    "providence": "PVD",
    "new haven": "NHV",
    "stamford": "STM",
    
    # Virginia
    "fredericksburg": "FBG",
    "quantico": "QAN",
    "woodbridge": "WDB",
    "manassas": "MSS",
    "culpeper": "CLP",
    "charlottesville": "CVS",
    "lynchburg": "LYH",
    "roanoke": "RNK",
    "richmond staples mill": "RVR",
    "richmond main street": "RVM",
    "richmond": "RVR",
    "newport news": "NPN",
    "williamsburg": "WBG",
    
    # Other major stations
    "chicago union": "CHI",
    "chicago": "CHI",
    "los angeles union": "LAX",
    "los angeles": "LAX",
    "seattle": "SEA",
    "portland": "PDX",
}

# Common train names
TRAIN_NAMES = {
    # Northeast Regional
    "northeast regional": "Northeast Regional",
    "regional": "Northeast Regional",
    
    # Acela
    "acela": "Acela Express",
    "acela express": "Acela Express",
    
    # Long distance
    "cardinal": "Cardinal",
    "capitol limited": "Capitol Limited",
    "crescent": "Crescent",
    "palmetto": "Palmetto",
    "silver star": "Silver Star",
    "silver meteor": "Silver Meteor",
    "carolinian": "Carolinian",
    "vermonter": "Vermonter",
    "auto train": "Auto Train",
}


class AmtrakConnector(Connector):
    """
    Amtraker API connector for live Amtrak train data.
    
    Uses the free Amtraker API which requires no authentication.
    Provides real-time train tracking, arrivals, and departures.
    
    Features:
    - Station arrivals/departures
    - Live train tracking
    - Delay information
    - No API key needed!
    """
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def connector_type(self) -> str:
        return "amtrak"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def authenticate(self) -> bool:
        """
        Verify API is accessible.
        No authentication needed for Amtraker API!
        """
        try:
            session = await self._get_session()
            
            # Test API with a simple request
            url = f"{AMTRAKER_BASE_URL}/v3/stations/WAS"
            async with session.get(url) as response:
                if response.status == 200:
                    self._authenticated = True
                    logger.info("✓ Amtraker API accessible (no auth required)")
                    return True
                else:
                    logger.warning(f"Amtraker API returned status {response.status}")
                    self._authenticated = False
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to connect to Amtraker API: {e}")
            self._authenticated = False
            return False
    
    async def search(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get train information.
        
        Args:
            criteria: {
                "station": "Washington Union Station" or station code,
                "train_number": "42" - specific train number,
                "limit": 10,
            }
        """
        train_number = criteria.get("train_number")
        station = criteria.get("station")
        limit = criteria.get("limit", 10)
        
        if train_number:
            return await self._get_train_status(train_number)
        elif station:
            return await self._get_station_arrivals(station, limit)
        else:
            # Get all active trains (filtered)
            return await self._get_active_trains(limit)
    
    async def _get_train_status(self, train_number: str) -> List[Dict[str, Any]]:
        """Get status for a specific train number"""
        try:
            session = await self._get_session()
            url = f"{AMTRAKER_BASE_URL}/v3/trains/{train_number}"
            
            async with session.get(url) as response:
                if response.status != 200:
                    return [{
                        "error": f"Train {train_number} not found or not currently running",
                        "train_number": train_number
                    }]
                
                data = await response.json()
                
                if not data or train_number not in data:
                    return [{
                        "error": f"No data for train {train_number}",
                        "train_number": train_number
                    }]
                
                trains = data[train_number]
                results = []
                
                for train in trains if isinstance(trains, list) else [trains]:
                    results.append(self._format_train(train))
                
                return results
                
        except Exception as e:
            logger.error(f"Error fetching train {train_number}: {e}")
            return [{"error": str(e), "train_number": train_number}]
    
    async def _get_station_arrivals(
        self, 
        station: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get arrivals/departures at a station"""
        try:
            station_code = self._resolve_station(station)
            session = await self._get_session()
            url = f"{AMTRAKER_BASE_URL}/v3/stations/{station_code}"
            
            async with session.get(url) as response:
                if response.status != 200:
                    return [{
                        "error": f"Station {station} ({station_code}) not found",
                        "station": station
                    }]
                
                data = await response.json()
                
                if not data or station_code not in data:
                    return [{
                        "info": f"No station data for {station}",
                        "station": station,
                        "station_code": station_code
                    }]
                
                station_data = data[station_code]
                
                # v3 API returns station info with 'trains' as list of train IDs
                # Format: "80-31" where 80 is train number, 31 is day
                train_ids = station_data.get("trains", [])
                
                if not train_ids:
                    return [{
                        "info": f"No trains currently scheduled for {station}",
                        "station": station,
                        "station_code": station_code,
                        "station_name": station_data.get("name", station),
                        "address": f"{station_data.get('address1', '')} {station_data.get('city', '')}, {station_data.get('state', '')} {station_data.get('zip', '')}".strip()
                    }]
                
                results = []
                
                # Fetch details for each train (extract train number from ID)
                seen_trains = set()
                for train_id in train_ids[:limit * 2]:  # Fetch more to account for duplicates
                    # Extract train number (before the dash)
                    train_num = train_id.split("-")[0] if "-" in train_id else train_id
                    
                    if train_num in seen_trains:
                        continue
                    seen_trains.add(train_num)
                    
                    # Fetch train details
                    train_url = f"{AMTRAKER_BASE_URL}/v3/trains/{train_num}"
                    async with session.get(train_url) as train_response:
                        if train_response.status != 200:
                            continue
                        
                        train_data = await train_response.json()
                        
                        if train_num in train_data:
                            trains = train_data[train_num]
                            for train in trains if isinstance(trains, list) else [trains]:
                                # Find the station in this train's stops
                                formatted = self._format_train_for_station(train, station_code)
                                if formatted:
                                    results.append(formatted)
                    
                    if len(results) >= limit:
                        break
                
                # Sort by scheduled arrival time
                results.sort(key=lambda x: x.get("scheduled_arrival", "") or x.get("scheduled_departure", ""))
                return results[:limit] if results else [{
                    "info": f"No active trains found for {station}",
                    "station": station,
                    "station_code": station_code
                }]
                
        except Exception as e:
            logger.error(f"Error fetching station {station}: {e}")
            return [{"error": str(e), "station": station}]
    
    async def _get_active_trains(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all currently active trains"""
        try:
            session = await self._get_session()
            url = f"{AMTRAKER_BASE_URL}/v3/trains"
            
            async with session.get(url) as response:
                if response.status != 200:
                    return [{"error": "Could not fetch active trains"}]
                
                data = await response.json()
                results = []
                
                for train_num, trains in data.items():
                    for train in trains if isinstance(trains, list) else [trains]:
                        results.append(self._format_train(train))
                        if len(results) >= limit:
                            break
                    if len(results) >= limit:
                        break
                
                return results
                
        except Exception as e:
            logger.error(f"Error fetching active trains: {e}")
            return [{"error": str(e)}]
    
    def _format_train(self, train: Dict[str, Any]) -> Dict[str, Any]:
        """Format train data for display"""
        # Extract delay info
        delay_mins = 0
        if "timely" in train:
            delay_mins = train.get("timely", 0)
        
        # Determine status
        status = "On Time"
        if delay_mins > 0:
            status = f"{delay_mins} min late"
        elif delay_mins < 0:
            status = f"{abs(delay_mins)} min early"
            
        return {
            "train_number": train.get("trainNum", train.get("routeName", "Unknown")),
            "train_name": train.get("routeName", ""),
            "origin": train.get("origName", train.get("orig", "")),
            "destination": train.get("destName", train.get("dest", "")),
            "current_station": train.get("eventName", train.get("stationName", "")),
            "status": status,
            "delay_minutes": delay_mins,
            "scheduled_arrival": train.get("schArr", train.get("scharr", "")),
            "scheduled_departure": train.get("schDep", train.get("schdep", "")),
            "actual_arrival": train.get("arr", ""),
            "actual_departure": train.get("dep", ""),
            "latitude": train.get("lat"),
            "longitude": train.get("lon"),
            "heading": train.get("heading"),
            "velocity": train.get("velocity"),
            "last_update": train.get("lastValTS", train.get("updated", "")),
        }
    
    def _format_train_for_station(
        self, 
        train: Dict[str, Any], 
        station_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Format train data for a specific station.
        
        Finds the station in the train's stops list and extracts
        arrival/departure times specific to that station.
        """
        # Find the station in this train's stops
        stops = train.get("stations", [])
        station_stop = None
        
        for stop in stops:
            if stop.get("code", "").upper() == station_code.upper():
                station_stop = stop
                break
        
        if not station_stop:
            # Station not found in this train's route
            return None
        
        # Get train-level info
        train_num = train.get("trainNum", "")
        route_name = train.get("routeName", "")
        
        # Determine status for this stop
        stop_status = station_stop.get("status", "Scheduled")
        
        return {
            "train_number": train_num,
            "train_name": route_name,
            "origin": train.get("origName", ""),
            "destination": train.get("destName", ""),
            "station_code": station_code,
            "station_name": station_stop.get("name", ""),
            "scheduled_arrival": station_stop.get("schArr", ""),
            "scheduled_departure": station_stop.get("schDep", ""),
            "actual_arrival": station_stop.get("arr", ""),
            "actual_departure": station_stop.get("dep", ""),
            "status": stop_status,
            "train_state": train.get("trainState", ""),
            "current_location": train.get("eventName", ""),
            "provider": train.get("provider", "Amtrak"),
        }
    
    def _format_station_train(
        self, 
        train: Dict[str, Any], 
        station_code: str
    ) -> Dict[str, Any]:
        """Format train data for station view"""
        formatted = self._format_train(train)
        formatted["station_code"] = station_code
        return formatted
    
    def _resolve_station(self, station: str) -> str:
        """Convert station name to Amtrak station code"""
        station_lower = station.lower().strip()
        
        # Check if it's already a code (3 letters)
        if len(station) == 3 and station.isupper():
            return station
        
        # Look up in our mapping
        if station_lower in STATION_CODES:
            return STATION_CODES[station_lower]
        
        # Fuzzy match - check if station name is contained
        for name, code in STATION_CODES.items():
            if station_lower in name or name in station_lower:
                return code
        
        # Return as-is (might be a code)
        return station.upper()[:3]
    
    async def execute_action(self, action_type: str, params: Dict[str, Any]) -> Any:
        """Amtrak connector is read-only, no actions to execute"""
        return {"error": "Amtrak connector is read-only"}
    
    async def get_train_by_name(self, train_name: str) -> List[Dict[str, Any]]:
        """
        Find trains by name/service type.
        
        Examples: "Acela", "Northeast Regional", "Capitol Limited"
        """
        name_lower = train_name.lower()
        
        # Get all active trains
        all_trains = await self._get_active_trains(limit=100)
        
        # Filter by name
        matching = []
        for train in all_trains:
            if "error" in train:
                continue
            train_route = train.get("train_name", "").lower()
            if name_lower in train_route or train_route in name_lower:
                matching.append(train)
        
        return matching if matching else [{
            "info": f"No active trains matching '{train_name}' found"
        }]
    
    async def close(self) -> None:
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
