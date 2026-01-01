import asyncio
import os
from datetime import datetime, timedelta
from jarvis.agents.calendar_agent import CalendarAgent, CalendarEvent
from jarvis.agents.transport_agent import TransportAgent
from jarvis.agents.connectors.maps_connector import MapsConnector
from jarvis.agents.connectors.connector_base import ConnectorConfig
from jarvis.core.config import load_config

async def verify():
    print("--- Verifying Calendar & Traffic ---")
    
    # 1. Setup Maps Connector
    print("\n1. Testing Maps Connector...")
    maps = MapsConnector(ConnectorConfig(name="apple_maps", connector_type="maps"))
    res = await maps.get_travel_time("White House", "US Capitol", "driving")
    print(f"Maps result: {res}")
    assert res.get("status") == "link_only"
    assert "maps.apple.com" in res.get("maps_url", "")
    print("✅ Maps Connector OK")

    # 2. Setup Transport Agent
    print("\n2. Testing Transport Agent Integration...")
    transport = TransportAgent()
    transport.register_connector(maps)
    
    estimate = await transport.get_travel_estimate("Home", "Work", mode="rideshare")
    print(f"Transport Estimate: {estimate}")
    assert "maps_url" in estimate
    print("✅ Transport Agent OK")
    
    # 3. Setup Calendar Agent (Mocked)
    print("\n3. Testing Calendar Agent...")
    cal = CalendarAgent()
    
    # Mock search to return a fake event
    original_search = cal.search
    async def mock_search(criteria):
        return [
            CalendarEvent(
                id="123",
                title="Meeting with Tony",
                start=datetime.now() + timedelta(hours=2),
                location="Stark Tower, New York",
                account="mock"
            )
        ]
    cal.search = mock_search
    
    next_event = await cal.get_next_event()
    print(f"Next Event: {next_event}")
    assert next_event.title == "Meeting with Tony"
    assert next_event.location == "Stark Tower, New York"
    print("✅ Calendar Agent OK")
    
    print("\n🎉 Verification Complete!")

if __name__ == "__main__":
    asyncio.run(verify())
