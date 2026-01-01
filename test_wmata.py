#!/usr/bin/env python3
"""Test WMATA connector directly"""
import asyncio
from jarvis.agents.connectors.wmata_connector import WMATAConnector
from jarvis.agents.connectors.connector_base import ConnectorConfig

async def test_wmata():
    # Create connector with API key
    config = ConnectorConfig(
        name='wmata',
        connector_type='wmata',
        api_key='afa4f0928b2e4a078c2a5bada6fe2411',  # From models.yaml
    )
    
    connector = WMATAConnector(config)
    
    # Try to authenticate
    print("Testing WMATA authentication...")
    auth_result = await connector.authenticate()
    print(f"Auth result: {auth_result}")
    
    if not auth_result:
        print("Authentication failed!")
        return
    
    # Try to get predictions for Tysons
    print("\nTesting rail predictions for Tysons...")
    results = await connector.search({
        "station": "Tysons",
        "mode": "metro",
        "limit": 5,
    })
    
    print(f"\nFound {len(results)} results:")
    for r in results:
        print(f"  - {r}")

if __name__ == "__main__":
    asyncio.run(test_wmata())
