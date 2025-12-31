
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, "/Users/sjpenn/AgentSites/Jarvis/jarvis")

from jarvis.agents.connectors.weather_connector import WeatherConnector
from jarvis.agents.connectors.flight_connector import FlightConnector
from jarvis.agents.connectors.hotel_connector import HotelConnector
from jarvis.agents.connectors.connector_base import ConnectorConfig
import yaml

async def verify_connectors():
    print("Starting verification...")
    
    # Load config
    config_path = Path("/Users/sjpenn/AgentSites/Jarvis/jarvis/config/models.yaml")
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)
    
    agents_config = config_data.get("agents", {})
    
    # 1. Verify Weather
    print("\n--- Verifying Weather Connector ---")
    weather_conf_data = agents_config.get("weather", {})
    w_config = ConnectorConfig(
        name="weather_test",
        connector_type="weather",
        extra=weather_conf_data
    )
    weather = WeatherConnector(w_config)
    await weather.authenticate()
    print(f"Weather Auth: {weather.is_authenticated}")
    
    results = await weather.search({"location": "Washington, DC", "type": "current"})
    if results and "error" not in results[0]:
        print("✅ Weather data fetched successfully")
        print(f"Data: {results[0].get('data', {}).get('temperature')}F, {results[0].get('data', {}).get('description')}")
    else:
        print(f"❌ Weather fetch failed: {results}")

    # 2. Verify Flight
    print("\n--- Verifying Flight Connector ---")
    flight_conf_data = agents_config.get("flight", {})
    f_config = ConnectorConfig(
        name="flight_test",
        connector_type="flight",
        api_key=flight_conf_data.get("api_key"),
        extra=flight_conf_data
    )
    flight = FlightConnector(f_config)
    await flight.authenticate()
    print(f"Flight Auth: {flight.is_authenticated}")
    
    # We won't search to save API calls, but Auth check is good.
    # Actually, let's try a simple search if auth worked, but handle error if no usage left.
    if flight.is_authenticated:
        print("Flight API Key configured.")
    else:
        print("❌ Flight API Key missing or invalid.")

    # 3. Verify Hotel
    print("\n--- Verifying Hotel Connector ---")
    trip_conf_data = agents_config.get("trip", {})
    h_config = ConnectorConfig(
        name="hotel_test",
        connector_type="hotel",
        api_key=trip_conf_data.get("api_key"), # This is empty placeholder
        extra={"rapidapi_key": trip_conf_data.get("rapidapi_key")}
    )
    hotel = HotelConnector(h_config)
    await hotel.authenticate()
    
    # Should use demo data
    results = await hotel.search({"location": "Miami", "guests": 2})
    if results:
         print(f"✅ Hotel search returned {len(results)} results")
         print(f"First result: {results[0].get('name')}")
         # Check if it was demo data (we didn't set rapidapi key so it should be)
         if results[0].get('id').startswith('miami'):
             print("ℹ️ verified using demo data (fallback working)")
    else:
        print("❌ Hotel search failed")

if __name__ == "__main__":
    asyncio.run(verify_connectors())
