"""
JARVIS Outlook Connector - Microsoft Graph API client for Outlook mail

Provides:
- OAuth2 authentication via Microsoft identity platform
- Email search via Microsoft Graph API
- Send/reply/forward operations
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jarvis.agents.connectors.connector_base import Connector, ConnectorConfig

# Optional imports - graceful degradation if not installed
try:
    import msal
    import requests
    OUTLOOK_AVAILABLE = True
except ImportError:
    OUTLOOK_AVAILABLE = False


# Microsoft Graph API endpoints
GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
SCOPES = ['Mail.Read', 'Mail.Send', 'User.Read']


class OutlookConnector(Connector):
    """
    Microsoft Graph API connector for Outlook mail.
    
    Features:
    - OAuth2 via MSAL
    - Personal and work/school accounts
    - Email search and send operations
    """
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._access_token: Optional[str] = None
        self._app: Optional[Any] = None
        
        # Token cache path
        cache_dir = Path.home() / ".jarvis" / "tokens"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path = cache_dir / f"outlook_{config.name}.json"
    
    @property
    def connector_type(self) -> str:
        return "outlook"
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Microsoft Graph API.
        
        Uses MSAL for token management with persistent cache.
        """
        if not OUTLOOK_AVAILABLE:
            print("Outlook dependencies not installed. Run: pip install msal requests")
            return False
        
        client_id = self.config.extra.get("client_id")
        if not client_id:
            print("Outlook client_id not configured")
            return False
        
        # Initialize MSAL with token cache
        cache = msal.SerializableTokenCache()
        if self._cache_path.exists():
            cache.deserialize(self._cache_path.read_text())
        
        self._app = msal.PublicClientApplication(
            client_id,
            authority="https://login.microsoftonline.com/consumers",
            token_cache=cache,
        )
        
        # Try to get token silently from cache
        accounts = self._app.get_accounts()
        result = None
        
        if accounts:
            result = self._app.acquire_token_silent(SCOPES, account=accounts[0])
        
        if not result:
            # Need interactive login
            result = self._app.acquire_token_interactive(
                scopes=SCOPES,
                prompt="select_account",
            )
        
        if "access_token" in result:
            self._access_token = result["access_token"]
            self._authenticated = True
            
            # Save cache
            if cache.has_state_changed:
                self._cache_path.write_text(cache.serialize())
            
            return True
        else:
            print(f"Outlook auth error: {result.get('error_description', 'Unknown error')}")
            return False
    
    async def search(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search emails using Microsoft Graph API.
        
        Args:
            criteria: {
                "query": "search terms",
                "limit": 20,
                "folder": "inbox",  # optional
            }
        """
        if not self._access_token:
            return []
        
        query = criteria.get("query", "")
        limit = criteria.get("limit", 20)
        folder = criteria.get("folder", "inbox")
        
        try:
            # Build request
            url = f"{GRAPH_API_ENDPOINT}/me/mailFolders/{folder}/messages"
            params = {
                "$top": limit,
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview,isRead,hasAttachments",
            }
            
            if query:
                params["$search"] = f'"{query}"'
            
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            messages = data.get("value", [])
            
            return [self._parse_message(msg) for msg in messages]
            
        except Exception as e:
            print(f"Outlook search error: {e}")
            return []
    
    async def execute_action(self, action_type: str, params: Dict[str, Any]) -> Any:
        """Execute email action"""
        
        if action_type == "send_email":
            return await self._send_email(params)
        elif action_type == "reply_email":
            return await self._reply_email(params)
        else:
            raise ValueError(f"Unknown action: {action_type}")
    
    async def _send_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a new email"""
        if not self._access_token:
            raise RuntimeError("Not authenticated")
        
        # Build message
        message = {
            "subject": params.get("subject", ""),
            "body": {
                "contentType": "Text",
                "content": params.get("body", ""),
            },
            "toRecipients": [
                {"emailAddress": {"address": addr.strip()}}
                for addr in params.get("to", "").split(",")
            ],
        }
        
        if params.get("cc"):
            message["ccRecipients"] = [
                {"emailAddress": {"address": addr.strip()}}
                for addr in params.get("cc", "").split(",")
            ]
        
        # Send
        url = f"{GRAPH_API_ENDPOINT}/me/sendMail"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        
        response = requests.post(url, headers=headers, json={"message": message})
        response.raise_for_status()
        
        return {"status": "sent"}
    
    async def _reply_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Reply to an email"""
        if not self._access_token:
            raise RuntimeError("Not authenticated")
        
        message_id = params.get("original_id")
        if not message_id:
            raise ValueError("original_id required")
        
        url = f"{GRAPH_API_ENDPOINT}/me/messages/{message_id}/reply"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        
        body = {
            "comment": params.get("body", ""),
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        return {"status": "sent"}
    
    def _parse_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Graph API message into standard format"""
        from_data = msg.get("from", {}).get("emailAddress", {})
        
        # Parse date
        date = None
        date_str = msg.get("receivedDateTime", "")
        if date_str:
            try:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except Exception:
                pass
        
        return {
            "id": msg.get("id"),
            "subject": msg.get("subject", "No subject"),
            "from": from_data.get("address", ""),
            "from_name": from_data.get("name", from_data.get("address", "")),
            "from_email": from_data.get("address", ""),
            "to": [r.get("emailAddress", {}).get("address", "") for r in msg.get("toRecipients", [])],
            "date": date,
            "snippet": msg.get("bodyPreview", ""),
            "is_read": msg.get("isRead", True),
            "has_attachments": msg.get("hasAttachments", False),
        }
    
    async def get_profile(self) -> Dict[str, Any]:
        """Get authenticated user's profile"""
        if not self._access_token:
            return {}
        
        try:
            url = f"{GRAPH_API_ENDPOINT}/me"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return {
                "email": data.get("mail") or data.get("userPrincipalName"),
                "name": data.get("displayName"),
            }
        except Exception as e:
            return {"error": str(e)}
