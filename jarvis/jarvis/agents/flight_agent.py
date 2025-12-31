"""
JARVIS Flight Agent - Airline flight status tracking

Provides:
- Real-time flight status by flight number
- Departure and arrival information
- Delay and cancellation alerts
- Gate and terminal information
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from jarvis.agents.agent_base import Agent, DraftAction


class FlightAgent(Agent):
    """
    Flight status tracking agent.
    
    Query flight status by flight number for real-time updates.
    
    Features:
    - Track any flight by number (e.g., "AA123", "United 456")
    - Get departure and arrival times
    - Check for delays and cancellations
    - Gate and terminal information
    """
    
    def __init__(self):
        super().__init__()
        self._tracked_flights: List[str] = []  # Flights user is tracking
    
    @property
    def name(self) -> str:
        return "flight"
    
    @property
    def description(self) -> str:
        return "Airline flight status tracking and information"
    
    def configure(
        self,
        tracked_flights: Optional[List[str]] = None,
    ) -> None:
        """
        Configure flight agent.
        
        Args:
            tracked_flights: List of flight numbers to track
        """
        if tracked_flights:
            self._tracked_flights = tracked_flights
    
    async def understand(self, query: str) -> Dict[str, Any]:
        """Parse flight-related intent"""
        import re
        
        query_lower = query.lower()
        
        intent = {
            "action": "flight_status",
            "flight_number": None,
            "original_query": query,
        }
        
        # Extract flight number patterns
        # Pattern 1: AA123, UA 456, etc.
        iata_match = re.search(r'\b([A-Z]{2})\s*(\d{1,4})\b', query.upper())
        if iata_match:
            intent["flight_number"] = f"{iata_match.group(1)}{iata_match.group(2)}"
            return intent
        
        # Pattern 2: Airline name + number (e.g., "American 123")
        airline_patterns = [
            (r'american\s*(?:airlines?)?\s*(\d+)', 'AA'),
            (r'united\s*(?:airlines?)?\s*(\d+)', 'UA'),
            (r'delta\s*(?:airlines?)?\s*(\d+)', 'DL'),
            (r'southwest\s*(?:airlines?)?\s*(\d+)', 'WN'),
            (r'jetblue\s*(\d+)', 'B6'),
            (r'alaska\s*(?:airlines?)?\s*(\d+)', 'AS'),
            (r'spirit\s*(\d+)', 'NK'),
            (r'frontier\s*(\d+)', 'F9'),
        ]
        
        for pattern, code in airline_patterns:
            match = re.search(pattern, query_lower)
            if match:
                intent["flight_number"] = f"{code}{match.group(1)}"
                return intent
        
        # Pattern 3: "flight" followed by something that looks like a number
        flight_match = re.search(r'flight\s+([A-Z0-9]+)', query, re.IGNORECASE)
        if flight_match:
            intent["flight_number"] = flight_match.group(1).upper()
        
        # Check if asking about "my flight" and we have tracked flights
        if "my flight" in query_lower and self._tracked_flights:
            intent["flight_number"] = self._tracked_flights[0]
        
        return intent
    
    async def search(self, criteria: Dict[str, Any]) -> List[Any]:
        """
        Get flight status.
        
        Args:
            criteria: {
                "flight_number": "AA123",
            }
        """
        flight_number = criteria.get("flight_number")
        
        if not flight_number:
            return [{"error": "Please specify a flight number (e.g., AA123)"}]
        
        results = []
        
        for connector in self._connectors:
            try:
                flight_data = await connector.search({
                    "flight_number": flight_number,
                })
                results.extend(flight_data)
            except Exception as e:
                print(f"Flight search error: {e}")
        
        return results
    
    async def propose_action(self, intent: Dict[str, Any]) -> DraftAction:
        """Flight agent is informational only"""
        return DraftAction(
            agent=self.name,
            action_type="get_flight_status",
            description=f"Get status for flight {intent.get('flight_number', 'unknown')}",
            params=intent,
        )
    
    async def execute(self, action: DraftAction) -> str:
        """Flight agent actions are informational"""
        return "Flight information retrieved"
    
    def get_capabilities(self) -> List[str]:
        return [
            "Get real-time flight status",
            "Track flights by flight number",
            "Check for delays and cancellations",
            "Get gate and terminal information",
        ]
    
    async def get_flight_status(self, flight_number: str) -> Dict[str, Any]:
        """
        Convenience method to get flight status.
        
        Args:
            flight_number: Flight number (e.g., "AA123")
            
        Returns:
            Flight status information
        """
        results = await self.search({"flight_number": flight_number})
        
        if not results:
            return {"error": f"No information found for flight {flight_number}"}
        
        if "error" in results[0]:
            return results[0]
        
        return results[0]
    
    def track_flight(self, flight_number: str) -> None:
        """Add a flight to tracking list"""
        if flight_number not in self._tracked_flights:
            self._tracked_flights.append(flight_number)
    
    def untrack_flight(self, flight_number: str) -> None:
        """Remove a flight from tracking list"""
        if flight_number in self._tracked_flights:
            self._tracked_flights.remove(flight_number)
    
    def format_flight_response(self, flight_data: Dict[str, Any]) -> str:
        """Format flight data as natural language response"""
        if "error" in flight_data:
            return f"Sorry, {flight_data['error']}"
        
        dep = flight_data.get("departure", {})
        arr = flight_data.get("arrival", {})
        
        response = [
            f"**Flight {flight_data['flight_number']}** - {flight_data.get('airline', 'Unknown Airline')}",
            f"Status: **{flight_data.get('status_display', 'Unknown')}**",
            "",
        ]
        
        # Departure info
        dep_city = dep.get("city") or dep.get("airport", "Unknown")
        response.append(f"**Departing:** {dep_city} ({dep.get('airport_iata', '')})")
        
        if dep.get("scheduled"):
            response.append(f"  Scheduled: {dep['scheduled']}")
        if dep.get("terminal") or dep.get("gate"):
            gate_info = []
            if dep.get("terminal"):
                gate_info.append(f"Terminal {dep['terminal']}")
            if dep.get("gate"):
                gate_info.append(f"Gate {dep['gate']}")
            response.append(f"  {', '.join(gate_info)}")
        if dep.get("delay_minutes") and dep["delay_minutes"] > 0:
            response.append(f"  ⚠️ Delayed by {dep['delay_minutes']} minutes")
        
        response.append("")
        
        # Arrival info
        arr_city = arr.get("city") or arr.get("airport", "Unknown")
        response.append(f"**Arriving:** {arr_city} ({arr.get('airport_iata', '')})")
        
        if arr.get("scheduled"):
            response.append(f"  Scheduled: {arr['scheduled']}")
        if arr.get("terminal") or arr.get("gate"):
            gate_info = []
            if arr.get("terminal"):
                gate_info.append(f"Terminal {arr['terminal']}")
            if arr.get("gate"):
                gate_info.append(f"Gate {arr['gate']}")
            response.append(f"  {', '.join(gate_info)}")
        
        return "\n".join(response)
