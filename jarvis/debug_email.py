
import asyncio
import os
from pathlib import Path
from jarvis.agents.email_agent import EmailAgent
from jarvis.agents.connectors.gmail_connector import GmailConnector
from jarvis.agents.connectors.connector_base import ConnectorConfig

async def test_email():
    print("Testing Email Agent...")
    
    # Path to credentials
    creds_path = Path.home() / ".jarvis" / "gmail_credentials.json"
    print(f"Checking credentials at: {creds_path}")
    
    if not creds_path.exists():
        print("❌ Credentials file not found!")
        return

    try:
        agent = EmailAgent()
        
        config = ConnectorConfig(
            name="personal",
            connector_type="gmail",
            credentials_path=str(creds_path)
        )
        
        print("Initializing Gmail Connector...")
        connector = GmailConnector(config)
        agent.register_connector(connector)
        
        print("Authenticating...")
        await connector.authenticate()
        print("✅ Authentication successful!")
        
        print("Searching for emails...")
        results = await agent.search({"limit": 5, "accounts": "all"})
        
        print(f"Found {len(results)} emails:")
        for email in results:
            print(f"- From: {email.sender} | Subject: {email.subject}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_email())
