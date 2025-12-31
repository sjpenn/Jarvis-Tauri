
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, "/Users/sjpenn/AgentSites/Jarvis/jarvis")

from jarvis.agents.connectors.flight_connector import FlightConnector
from jarvis.agents.connectors.connector_base import ConnectorConfig
import yaml

async def verify_radar():
    print("Starting Radar Verification...")
    
    # Load config
    config_path = Path("/Users/sjpenn/AgentSites/Jarvis/jarvis/config/models.yaml")
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)
    
    agents_config = config_data.get("agents", {})
    flight_conf_data = agents_config.get("flight", {})
    
    # Configure Flight Connector
    f_config = ConnectorConfig(
        name="flight_test",
        connector_type="flight",
        api_key=flight_conf_data.get("api_key"),
        extra=flight_conf_data
    )
    flight = FlightConnector(f_config)
    await flight.authenticate()
    
    print("\n--- Testing OpenSky Network (Traffic Search) ---")
    # Test around Washington DC
    lat, lon = 38.9072, -77.0369
    radius = 300
    
    print(f"Searching traffic around {lat}, {lon} (Radius: {radius} miles)...")
    traffic = await flight.search_traffic(lat, lon, radius)
    
    if traffic:
        print(f"✅ Success! Found {len(traffic)} aircraft.")
        print("First 3 aircraft:")
        for idx, t in enumerate(traffic[:3]):
            print(f"  {idx+1}. Call: {t.get('callsign')}, Alt: {t.get('altitude')}m, Ctry: {t.get('country')}")
    else:
        print("⚠️ No traffic found or API error (check logs). OpenSky might be rate limited or empty sky?")

if __name__ == "__main__":
    asyncio.run(verify_radar())
