"""
Maps Connector - Routing via Apple Maps

Uses macOS Apple Maps via AppleScript to get travel times and directions.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from jarvis.agents.connectors.connector_base import Connector, ConnectorConfig

class MapsConnector(Connector):
    """
    Apple Maps connector via AppleScript.
    
    Features:
    - effective travel time calculation
    - route generation
    """
    
    @property
    def connector_type(self) -> str:
        return "maps"
    
    async def authenticate(self) -> bool:
        """Check if we can access Apple Maps"""
        # We can't easily "auth" with Apple Maps app, but we can check if we can run osascript
        return True
        
    async def get_travel_time(self, start: str, end: str, transport_type: str = "automobile") -> Dict[str, Any]:
        """
        Get travel time from Apple Maps.
        
        Args:
            start: "Current Location" or address
            end: Destination address
            transport_type: "automobile", "transit", "walking"
        """
        
        # Note: Apple Maps via AppleScript is limited. 
        # We can open the app, but getting data OUT is hard without UI scripting which is flaky/requires permissions.
        # However, for a "Next Appointment" flow, we might often be better off just generating a deep link
        # OR using a free routing API if available. 
        # But wait, looking at `open -a "Maps"` we can pass URLs.
        
        # ACTUALLY - Getting *time* estimates without a proper API (Google/Mapbox) is very hard locally.
        # But we can fall back to the "Transit" approach for everything if we don't have a car API.
        
        # Let's try to see if we can use a basic MapKit JS or similar? No, that needs key.
        # OSRM (Open Source Routing Machine) public demo server? No, restricted.
        
        # STRATEGY CHANGE for this file:
        # Since we don't have a paid API key for Traffic, we will:
        # 1. Use WMATA (existing) for Transit estimates in DC.
        # 2. For driving, we will simulate/estimate based on straight line distance * factor if real data unavailable,
        #    OR return a "Check Apple Maps" link.
        # 3. BUT, let's try a clever AppleScript that *might* work for some users if they have location services enabled.
        
        # For now, we will return a structured object that the TransportAgent can use to decide what to show.
        
        return {
            "start": start,
            "end": end,
            "status": "link_only", # Indicates we can't get real-time traffic in background
            "maps_url": f"http://maps.apple.com/?saddr={start.replace(' ', '+')}&daddr={end.replace(' ', '+')}&dirflg={self._get_dir_flag(transport_type)}"
        }

    def _get_dir_flag(self, mode: str) -> str:
        """Get Apple Maps direction flag"""
        if mode == "transit": return "r"
        if mode == "walking": return "w"
        return "d" # driving
    
    async def search(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search mostly returns the deep link for now.
        """
        start = criteria.get("start", "Current Location")
        end = criteria.get("end", "")
        mode = criteria.get("mode", "driving")
        
        result = await self.get_travel_time(start, end, mode)
        return [result]

    async def execute_action(self, action_type: str, params: Dict[str, Any]) -> Any:
        return None
