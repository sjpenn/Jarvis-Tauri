"""
JARVIS Gmail Connector - OAuth2 Gmail API client with multi-account support

Provides:
- OAuth2 authentication with token persistence
- Email search via Gmail API
- Send/reply/forward operations
- Label management
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

from jarvis.agents.connectors.connector_base import Connector, ConnectorConfig

# Optional imports - graceful degradation if not installed
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False


# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
]


class GmailConnector(Connector):
    """
    Gmail API connector with OAuth2 authentication.
    
    Features:
    - Persistent token storage per account
    - Full Gmail API access
    - Search with Gmail query syntax
    - Send emails (used by draft mode)
    """
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._service = None
        self._credentials: Optional[Credentials] = None
        
        # Token storage path
        token_dir = Path.home() / ".jarvis" / "tokens"
        token_dir.mkdir(parents=True, exist_ok=True)
        self._token_path = token_dir / f"gmail_{config.name}.json"
    
    @property
    def connector_type(self) -> str:
        return "gmail"
    
    async def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth2.
        
        Uses stored credentials if available, otherwise initiates OAuth flow.
        """
        if not GMAIL_AVAILABLE:
            print("Gmail dependencies not installed. Run: pip install google-auth-oauthlib google-api-python-client")
            return False
        
        creds = None
        
        # Try to load existing token
        if self._token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self._token_path), SCOPES)
            except Exception as e:
                print(f"Error loading credentials: {e}")
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                # Need new OAuth flow
                credentials_file = self.config.credentials_path
                if not credentials_file or not Path(credentials_file).exists():
                    print(f"Gmail credentials file not found: {credentials_file}")
                    print("Please download client_secret.json from Google Cloud Console")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"OAuth flow failed: {e}")
                    return False
            
            # Save credentials for next time
            with open(self._token_path, 'w') as token:
                token.write(creds.to_json())
        
        # Build API service
        try:
            self._service = build('gmail', 'v1', credentials=creds)
            self._credentials = creds
            self._authenticated = True
            return True
        except Exception as e:
            print(f"Error building Gmail service: {e}")
            return False
    
    async def search(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search emails using Gmail query syntax.
        
        Args:
            criteria: {
                "query": "from:john subject:meeting",
                "limit": 20,
                "labels": ["INBOX"],  # optional
            }
        """
        if not self._service:
            return []
        
        query = criteria.get("query", "")
        limit = criteria.get("limit", 20)
        labels = criteria.get("labels", ["INBOX"])
        
        try:
            # Search for message IDs
            results = self._service.users().messages().list(
                userId='me',
                q=query,
                labelIds=labels,
                maxResults=limit,
            ).execute()
            
            messages = results.get('messages', [])
            
            # Fetch full message details
            emails = []
            for msg in messages[:limit]:
                try:
                    full_msg = self._service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['From', 'To', 'Subject', 'Date'],
                    ).execute()
                    
                    email_data = self._parse_message(full_msg)
                    emails.append(email_data)
                except Exception as e:
                    print(f"Error fetching message {msg['id']}: {e}")
            
            return emails
            
        except Exception as e:
            print(f"Gmail search error: {e}")
            return []
    
    async def execute_action(self, action_type: str, params: Dict[str, Any]) -> Any:
        """Execute email action"""
        
        if action_type == "send_email":
            return await self._send_email(params)
        elif action_type == "reply_email":
            return await self._reply_email(params)
        elif action_type == "forward_email":
            return await self._forward_email(params)
        else:
            raise ValueError(f"Unknown action: {action_type}")
    
    async def _send_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a new email"""
        if not self._service:
            raise RuntimeError("Not authenticated")
        
        message = MIMEText(params.get("body", ""))
        message['to'] = params.get("to", "")
        message['subject'] = params.get("subject", "")
        
        if params.get("cc"):
            message['cc'] = params.get("cc")
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        result = self._service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return {"message_id": result.get("id"), "status": "sent"}
    
    async def _reply_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Reply to an email"""
        if not self._service:
            raise RuntimeError("Not authenticated")
        
        original_id = params.get("original_id")
        if not original_id:
            raise ValueError("original_id required for reply")
        
        # Get original message for headers
        original = self._service.users().messages().get(
            userId='me',
            id=original_id,
            format='metadata',
            metadataHeaders=['From', 'Subject', 'Message-ID'],
        ).execute()
        
        headers = {h['name']: h['value'] for h in original.get('payload', {}).get('headers', [])}
        
        message = MIMEText(params.get("body", ""))
        message['to'] = headers.get('From', '')
        message['subject'] = f"Re: {headers.get('Subject', '')}"
        message['In-Reply-To'] = headers.get('Message-ID', '')
        message['References'] = headers.get('Message-ID', '')
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        result = self._service.users().messages().send(
            userId='me',
            body={
                'raw': raw,
                'threadId': original.get('threadId'),
            }
        ).execute()
        
        return {"message_id": result.get("id"), "status": "sent"}
    
    async def _forward_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Forward an email"""
        if not self._service:
            raise RuntimeError("Not authenticated")
        
        original_id = params.get("original_id")
        if not original_id:
            raise ValueError("original_id required for forward")
        
        # Get original message
        original = self._service.users().messages().get(
            userId='me',
            id=original_id,
            format='full',
        ).execute()
        
        # Extract original body
        original_body = self._get_body(original.get('payload', {}))
        headers = {h['name']: h['value'] for h in original.get('payload', {}).get('headers', [])}
        
        # Compose forward
        forward_body = f"""{params.get('body', '')}

---------- Forwarded message ---------
From: {headers.get('From', '')}
Date: {headers.get('Date', '')}
Subject: {headers.get('Subject', '')}

{original_body}
"""
        
        message = MIMEText(forward_body)
        message['to'] = params.get("to", "")
        message['subject'] = f"Fwd: {headers.get('Subject', '')}"
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        result = self._service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return {"message_id": result.get("id"), "status": "sent"}
    
    def _parse_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail API message into standard format"""
        headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
        
        # Parse date
        date_str = headers.get('Date', '')
        date = None
        if date_str:
            try:
                # Gmail date format varies, try common formats
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_str)
            except Exception:
                pass
        
        # Parse from
        from_header = headers.get('From', '')
        from_name = from_header
        from_email = from_header
        if '<' in from_header and '>' in from_header:
            from_name = from_header.split('<')[0].strip().strip('"')
            from_email = from_header.split('<')[1].rstrip('>')
        
        return {
            "id": msg.get('id'),
            "thread_id": msg.get('threadId'),
            "subject": headers.get('Subject', 'No subject'),
            "from": from_header,
            "from_name": from_name,
            "from_email": from_email,
            "to": headers.get('To', '').split(','),
            "date": date,
            "snippet": msg.get('snippet', ''),
            "labels": msg.get('labelIds', []),
            "is_read": 'UNREAD' not in msg.get('labelIds', []),
            "has_attachments": any(
                part.get('filename') 
                for part in msg.get('payload', {}).get('parts', [])
            ),
        }
    
    def _get_body(self, payload: Dict[str, Any]) -> str:
        """Extract body text from message payload"""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode()
        
        # Check parts
        for part in payload.get('parts', []):
            if part.get('mimeType') == 'text/plain':
                if part.get('body', {}).get('data'):
                    return base64.urlsafe_b64decode(part['body']['data']).decode()
        
        return ""
    
    async def get_profile(self) -> Dict[str, Any]:
        """Get authenticated user's profile"""
        if not self._service:
            return {}
        
        try:
            profile = self._service.users().getProfile(userId='me').execute()
            return {
                "email": profile.get('emailAddress'),
                "messages_total": profile.get('messagesTotal'),
                "threads_total": profile.get('threadsTotal'),
            }
        except Exception as e:
            return {"error": str(e)}
