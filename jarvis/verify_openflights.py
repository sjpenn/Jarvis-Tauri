
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, "/Users/sjpenn/AgentSites/Jarvis/jarvis")

from jarvis.agents.utils.flight_data_manager import FlightDataManager
from jarvis.agents.connectors.flight_connector import FlightConnector
from jarvis.agents.connectors.connector_base import ConnectorConfig
import yaml

async def verify_openflights():
    print("Starting OpenFlights Verification...")
    
    # 1. Test Data Manager
    manager = FlightDataManager()
    print("Downloading/Loading OpenFlights data...")
    await manager.load_data()
    
    airline = manager.get_airline_name("UAL")
    print(f"Lookup UAL: {airline}")
    if airline == "United Airlines":
        print("✅ Airline lookup working properly")
    else:
        print(f"❌ Airline lookup failed: {airline}")
        
    airport = manager.get_airport_info("DCA")
    print(f"Lookup DCA: {airport}")
    if airport and airport.get("city") == "Washington":
        print("✅ Airport lookup working properly")
    else:
        print(f"❌ Airport lookup failed: {airport}")

    # 2. Test Connector Integration
    print("\n--- Testing Connector Traffic Search Enrichment ---")
    config_path = Path("/Users/sjpenn/AgentSites/Jarvis/jarvis/config/models.yaml")
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)
    
    agents_config = config_data.get("agents", {})
    flight_conf_data = agents_config.get("flight", {})
    
    f_config = ConnectorConfig(
        name="flight_test",
        connector_type="flight",
        api_key=flight_conf_data.get("api_key"),
        extra=flight_conf_data
    )
    flight = FlightConnector(f_config)
    await flight.authenticate()
    
    lat, lon = 38.9072, -77.0369
    print("Searching traffic around DC...")
    results = await flight.search_traffic(lat, lon, 300)
    
    if results:
        print(f"Found {len(results)} aircraft.")
        # Check first 5 for full airline names
        count = 0
        for r in results[:10]:
            name = r.get("airline", "Unknown")
            callsign = r.get("callsign", "")
            if name and name != "Unknown Airline":
                print(f"✅ Enriched: {callsign} -> {name}")
                count += 1
            else:
                 print(f"⚠️ Not enriched: {callsign}")
        
        if count > 0:
            print(f"Successfully enriched {count} flights with airline names!")
    else:
        print("No traffic found.")

if __name__ == "__main__":
    asyncio.run(verify_openflights())
