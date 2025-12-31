"""
JARVIS Weather Agent - Weather forecasting and travel preparation

Provides:
- Current weather conditions
- Multi-day forecasts
- Travel weather preparation
- Packing suggestions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from jarvis.agents.agent_base import Agent, DraftAction


@dataclass
class WeatherLocation:
    """A configured location for weather queries"""
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None


class WeatherAgent(Agent):
    """
    Weather information agent.
    
    Provides weather data for trip planning and daily use.
    
    Features:
    - Current conditions for any location
    - Multi-day forecasts
    - Packing suggestions based on weather
    - Travel weather preparation
    """
    
    def __init__(self):
        super().__init__()
        self._default_location: Optional[str] = None
        self._locations: Dict[str, WeatherLocation] = {}
    
    @property
    def name(self) -> str:
        return "weather"
    
    @property
    def description(self) -> str:
        return "Weather forecasts, current conditions, and travel preparation"
    
    def configure(
        self,
        default_location: Optional[str] = None,
        locations: Optional[Dict[str, dict]] = None,
    ) -> None:
        """
        Configure weather agent.
        
        Args:
            default_location: Default location for weather queries
            locations: Named locations with coordinates
        """
        if default_location:
            self._default_location = default_location
        
        if locations:
            for name, loc_data in locations.items():
                self._locations[name] = WeatherLocation(
                    name=name,
                    latitude=loc_data.get("latitude"),
                    longitude=loc_data.get("longitude"),
                    address=loc_data.get("address"),
                )
    
    async def understand(self, query: str) -> Dict[str, Any]:
        """Parse weather-related intent"""
        query_lower = query.lower()
        
        intent = {
            "action": "weather",
            "location": None,
            "type": "both",  # current, forecast, or both
            "days": 3,
            "packing": False,
            "original_query": query,
        }
        
        # Check for forecast vs current
        if any(word in query_lower for word in ["forecast", "week", "tomorrow", "next"]):
            intent["type"] = "forecast"
            if "week" in query_lower:
                intent["days"] = 7
            elif "tomorrow" in query_lower:
                intent["days"] = 2
        elif any(word in query_lower for word in ["current", "now", "right now", "today"]):
            intent["type"] = "current"
        
        # Check for packing query
        if any(word in query_lower for word in ["pack", "bring", "wear", "clothes"]):
            intent["packing"] = True
            intent["type"] = "forecast"
        
        # Extract location - look for patterns like "in [location]", "for [location]"
        location_indicators = ["in ", "for ", "at ", "weather "]
        for indicator in location_indicators:
            if indicator in query_lower:
                idx = query_lower.find(indicator)
                location_part = query[idx + len(indicator):].strip()
                # Remove trailing punctuation and common words
                for end_word in ["?", ".", "!", " tomorrow", " this week", " next week", 
                                " today", " forecast", " weather"]:
                    if location_part.lower().endswith(end_word):
                        location_part = location_part[:-len(end_word)].strip()
                if location_part:
                    intent["location"] = location_part
                    break
        
        # Use default location if none found
        if not intent["location"]:
            intent["location"] = self._default_location or "Washington, DC"
        
        return intent
    
    async def search(self, criteria: Dict[str, Any]) -> List[Any]:
        """
        Get weather data.
        
        Args:
            criteria: {
                "location": "New York",
                "type": "current" | "forecast" | "both",
                "days": 5,
                "packing": True/False,
            }
        """
        location = criteria.get("location", self._default_location or "Washington, DC")
        query_type = criteria.get("type", "both")
        days = criteria.get("days", 3)
        include_packing = criteria.get("packing", False)
        
        results = []
        
        for connector in self._connectors:
            try:
                weather_data = await connector.search({
                    "location": location,
                    "type": query_type,
                    "days": days,
                })
                
                if weather_data:
                    # Add packing suggestions if requested
                    if include_packing:
                        for item in weather_data:
                            if item.get("type") == "forecast":
                                forecast = item.get("data", [])
                                if hasattr(connector, "get_packing_suggestions"):
                                    suggestions = connector.get_packing_suggestions(forecast)
                                    results.append({
                                        "type": "packing_suggestions",
                                        "data": suggestions,
                                    })
                    
                    results.extend(weather_data)
            except Exception as e:
                print(f"Weather search error: {e}")
        
        return results
    
    async def propose_action(self, intent: Dict[str, Any]) -> DraftAction:
        """Weather agent is informational only"""
        return DraftAction(
            agent=self.name,
            action_type="get_weather",
            description=f"Get weather for {intent.get('location', 'default location')}",
            params=intent,
        )
    
    async def execute(self, action: DraftAction) -> str:
        """Weather agent actions are informational"""
        return "Weather information retrieved"
    
    def get_capabilities(self) -> List[str]:
        return [
            "Get current weather conditions",
            "Get multi-day weather forecasts",
            "Provide packing suggestions for trips",
            "Check weather for travel planning",
        ]
    
    async def get_weather_for_location(
        self, 
        location: str,
        include_forecast: bool = True,
        days: int = 3,
    ) -> Dict[str, Any]:
        """
        Convenience method to get weather for a location.
        
        Returns formatted weather data ready for display.
        """
        results = await self.search({
            "location": location,
            "type": "both" if include_forecast else "current",
            "days": days,
        })
        
        response = {
            "location": location,
            "current": None,
            "forecast": [],
        }
        
        for r in results:
            if r.get("type") == "current":
                response["current"] = r.get("data")
            elif r.get("type") == "forecast":
                response["forecast"] = r.get("data", [])
        
        return response
    
    async def get_travel_weather(
        self,
        destination: str,
        start_date: Optional[datetime] = None,
        days: int = 5,
    ) -> Dict[str, Any]:
        """
        Get weather information for travel planning.
        
        Returns weather forecast and packing suggestions.
        """
        results = await self.search({
            "location": destination,
            "type": "forecast",
            "days": days,
            "packing": True,
        })
        
        response = {
            "destination": destination,
            "forecast": [],
            "packing_suggestions": [],
        }
        
        for r in results:
            if r.get("type") == "forecast":
                response["forecast"] = r.get("data", [])
            elif r.get("type") == "packing_suggestions":
                response["packing_suggestions"] = r.get("data", [])
        
        return response
    
    def format_weather_response(self, weather_data: Dict[str, Any]) -> str:
        """Format weather data as natural language response"""
        parts = []
        location = weather_data.get("location", "the location")
        
        current = weather_data.get("current")
        if current:
            parts.append(
                f"Currently in {location}: {current.get('temperature', 'N/A')}°F, "
                f"{current.get('description', 'N/A')}. "
                f"Humidity: {current.get('humidity', 'N/A')}%, "
                f"Wind: {current.get('wind_speed', 'N/A')} mph from {current.get('wind_direction', 'N/A')}."
            )
        
        forecast = weather_data.get("forecast", [])
        if forecast:
            parts.append("\nForecast:")
            for day in forecast[:5]:
                date_str = day.get("date", "")
                parts.append(
                    f"  {date_str}: High {day.get('high', 'N/A'):.0f}°F, "
                    f"Low {day.get('low', 'N/A'):.0f}°F - {day.get('description', 'N/A')} "
                    f"({day.get('precipitation_chance', 0)}% precip)"
                )
        
        packing = weather_data.get("packing_suggestions", [])
        if packing:
            parts.append("\nPacking suggestions:")
            for item in packing:
                parts.append(f"  • {item}")
        
        return "\n".join(parts)
