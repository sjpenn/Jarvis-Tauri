"""
JARVIS Trip Planning Agent - Cost-based trip planning with hotels

Provides:
- Hotel search and comparison
- Trip cost calculation
- Budget-based recommendations
- Amenity filtering
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from jarvis.agents.agent_base import Agent, DraftAction


@dataclass
class TripPlan:
    """A planned trip"""
    destination: str
    check_in: datetime
    check_out: datetime
    hotel: Optional[Dict[str, Any]] = None
    estimated_hotel_cost: float = 0.0
    total_nights: int = 0
    notes: List[str] = field(default_factory=list)


class TripPlanAgent(Agent):
    """
    Trip planning agent with cost optimization.
    
    Helps plan trips based on budget with hotel search and comparison.
    
    Features:
    - Search hotels by location, price, and amenities
    - Compare options by price and rating
    - Calculate total trip costs
    - Filter by star rating and amenities
    """
    
    def __init__(self):
        super().__init__()
        self._saved_trips: List[TripPlan] = []
    
    @property
    def name(self) -> str:
        return "trip"
    
    @property
    def description(self) -> str:
        return "Trip planning with hotel search and cost optimization"
    
    async def understand(self, query: str) -> Dict[str, Any]:
        """Parse trip planning intent"""
        import re
        
        query_lower = query.lower()
        
        intent = {
            "action": "search_hotels",
            "location": None,
            "max_price": None,
            "min_stars": None,
            "amenities": [],
            "sort_by": "price",
            "original_query": query,
        }
        
        # Extract location
        location_patterns = [
            r'(?:hotels?\s+in|stay\s+in|trip\s+to|visit(?:ing)?)\s+([A-Za-z\s,]+?)(?:\s+(?:under|for|with|that|$))',
            r'(?:in|to)\s+([A-Za-z\s]+?)(?:\s+(?:under|for|with|$))',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                # Clean up common trailing words
                for word in ["under", "for", "with", "that", "hotel", "hotels"]:
                    if location.lower().endswith(word):
                        location = location[:-len(word)].strip()
                if location:
                    intent["location"] = location
                    break
        
        # Extract max price
        price_match = re.search(r'(?:under|less\s+than|max(?:imum)?|budget\s+of?)\s*\$?(\d+)', query_lower)
        if price_match:
            intent["max_price"] = int(price_match.group(1))
        
        # Extract star rating
        star_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:star|stars)', query_lower)
        if star_match:
            intent["min_stars"] = float(star_match.group(1))
        
        # Extract amenities
        common_amenities = ["pool", "spa", "gym", "wifi", "parking", "restaurant", 
                           "bar", "beach", "breakfast", "pet friendly", "jacuzzi"]
        for amenity in common_amenities:
            if amenity in query_lower:
                intent["amenities"].append(amenity)
        
        # Determine sort preference
        if "cheap" in query_lower or "budget" in query_lower or "affordable" in query_lower:
            intent["sort_by"] = "price"
        elif "best" in query_lower or "top rated" in query_lower or "highest rated" in query_lower:
            intent["sort_by"] = "rating"
        elif "luxury" in query_lower or "fancy" in query_lower:
            intent["sort_by"] = "stars"
            if not intent["min_stars"]:
                intent["min_stars"] = 4.0
        
        return intent
    
    async def search(self, criteria: Dict[str, Any]) -> List[Any]:
        """
        Search for hotels.
        
        Args:
            criteria: {
                "location": "Miami",
                "max_price": 200,
                "min_stars": 3,
                "amenities": ["pool", "wifi"],
                "sort_by": "price",
            }
        """
        if not criteria.get("location"):
            return [{"error": "Please specify a destination"}]
        
        results = []
        
        for connector in self._connectors:
            try:
                hotels = await connector.search(criteria)
                results.extend(hotels)
            except Exception as e:
                print(f"Hotel search error: {e}")
        
        return results
    
    async def propose_action(self, intent: Dict[str, Any]) -> DraftAction:
        """Trip agent is informational only for searches"""
        return DraftAction(
            agent=self.name,
            action_type="search_hotels",
            description=f"Search hotels in {intent.get('location', 'unknown')}",
            params=intent,
        )
    
    async def execute(self, action: DraftAction) -> str:
        """Execute trip planning action"""
        return "Hotel search completed"
    
    def get_capabilities(self) -> List[str]:
        return [
            "Search hotels by location",
            "Filter by price, star rating, and amenities",
            "Compare hotel options",
            "Calculate total trip costs",
        ]
    
    async def find_hotels(
        self,
        location: str,
        max_price: Optional[float] = None,
        min_stars: Optional[float] = None,
        amenities: Optional[List[str]] = None,
        sort_by: str = "price",
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to search hotels.
        
        Args:
            location: Destination city
            max_price: Maximum price per night
            min_stars: Minimum star rating
            amenities: Required amenities
            sort_by: "price", "rating", or "stars"
            
        Returns:
            List of matching hotels
        """
        return await self.search({
            "location": location,
            "max_price": max_price or 500,
            "min_stars": min_stars or 1,
            "amenities": amenities or [],
            "sort_by": sort_by,
        })
    
    def calculate_trip_cost(
        self,
        hotel: Dict[str, Any],
        nights: int,
        extras: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate total trip cost.
        
        Args:
            hotel: Hotel data
            nights: Number of nights
            extras: Additional costs (flights, activities, etc.)
            
        Returns:
            Cost breakdown
        """
        hotel_cost = hotel.get("price_per_night", 0) * nights
        
        costs = {
            "hotel_per_night": hotel.get("price_per_night", 0),
            "nights": nights,
            "hotel_total": hotel_cost,
            "extras": extras or {},
            "extras_total": sum((extras or {}).values()),
        }
        
        costs["grand_total"] = costs["hotel_total"] + costs["extras_total"]
        
        return costs
    
    def format_hotel_results(self, hotels: List[Dict[str, Any]], limit: int = 5) -> str:
        """Format hotel search results for display"""
        if not hotels:
            return "No hotels found matching your criteria."
        
        if "error" in hotels[0]:
            return hotels[0]["error"]
        
        parts = [f"Found {len(hotels)} hotels:\n"]
        
        for i, hotel in enumerate(hotels[:limit], 1):
            stars = "⭐" * int(hotel.get("star_rating", 0))
            
            parts.append(
                f"**{i}. {hotel['name']}** {stars}\n"
                f"   💰 ${hotel['price_per_night']}/night\n"
                f"   📊 {hotel.get('review_score', 'N/A')}/10 ({hotel.get('review_count', 0)} reviews)\n"
                f"   🏨 {', '.join(hotel.get('amenities', [])[:4])}\n"
            )
        
        if len(hotels) > limit:
            parts.append(f"\n...and {len(hotels) - limit} more options")
        
        return "\n".join(parts)
    
    def format_trip_cost(self, cost_breakdown: Dict[str, Any]) -> str:
        """Format trip cost breakdown for display"""
        parts = [
            "**Trip Cost Breakdown:**",
            f"🏨 Hotel: ${cost_breakdown['hotel_per_night']}/night × {cost_breakdown['nights']} nights = ${cost_breakdown['hotel_total']:.2f}",
        ]
        
        if cost_breakdown.get("extras"):
            parts.append("\n**Additional Costs:**")
            for item, cost in cost_breakdown["extras"].items():
                parts.append(f"  • {item}: ${cost:.2f}")
            parts.append(f"  Subtotal: ${cost_breakdown['extras_total']:.2f}")
        
        parts.append(f"\n**Total: ${cost_breakdown['grand_total']:.2f}**")
        
        return "\n".join(parts)
