"""
JARVIS Email Agent - Unified email management across multiple accounts

Supports Gmail and Outlook accounts with multi-account aggregation.
All send operations are done in draft mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from jarvis.agents.agent_base import Agent, DraftAction
from jarvis.agents.connectors.connector_base import Connector


@dataclass
class Email:
    """Unified email representation"""
    id: str
    subject: str
    sender: str
    sender_email: str
    recipients: List[str]
    body: str
    body_html: Optional[str] = None
    date: Optional[datetime] = None
    is_read: bool = True
    has_attachments: bool = False
    labels: List[str] = field(default_factory=list)
    account: str = ""  # Which account this came from
    thread_id: Optional[str] = None


class EmailAgent(Agent):
    """
    Unified email agent supporting multiple accounts.
    
    Features:
    - Aggregate search across Gmail + Outlook accounts
    - Draft mode for all send operations
    - Reply, forward, compose actions
    - Label/folder management
    """
    
    @property
    def name(self) -> str:
        return "email"
    
    @property
    def description(self) -> str:
        return "Search and manage emails across Gmail and Outlook accounts"
    
    async def understand(self, query: str) -> Dict[str, Any]:
        """
        Parse email-related intent from natural language.
        
        Examples:
        - "emails from John last week" -> search
        - "reply to the meeting invite" -> reply
        - "send email to boss about vacation" -> compose
        """
        query_lower = query.lower()
        
        # Detect action type
        if any(word in query_lower for word in ["reply", "respond"]):
            return {
                "action": "reply",
                "query": query,
            }
        elif any(word in query_lower for word in ["forward", "send to"]):
            return {
                "action": "forward",
                "query": query,
            }
        elif any(word in query_lower for word in ["compose", "write", "send email", "email to"]):
            return {
                "action": "compose",
                "query": query,
            }
        else:
            # Default to search
            return {
                "action": "search",
                "query": query,
            }
    
    async def search(self, criteria: Dict[str, Any]) -> List[Email]:
        """
        Aggregate search across all email connectors.
        
        Args:
            criteria: {
                "query": "search terms",
                "accounts": "all" or ["gmail:work", "outlook:personal"],
                "limit": 20,
            }
        """
        query = criteria.get("query", "")
        accounts_filter = criteria.get("accounts", "all")
        limit = criteria.get("limit", 20)
        
        all_results: List[Email] = []
        
        for connector in self._connectors:
            # Check account filter
            if accounts_filter != "all":
                if isinstance(accounts_filter, list) and connector.name not in accounts_filter:
                    continue
            
            try:
                results = await connector.search({
                    "query": query,
                    "limit": limit,
                })
                
                # Tag results with account source
                for email_data in results:
                    email = self._normalize_email(email_data, connector.name)
                    all_results.append(email)
                    
            except Exception as e:
                # Log but continue with other connectors
                print(f"Error searching {connector.name}: {e}")
        
        # Sort by date, newest first
        all_results.sort(key=lambda e: e.date or datetime.min, reverse=True)
        
        return all_results[:limit]
    
    async def propose_action(self, intent: Dict[str, Any]) -> DraftAction:
        """
        Create a draft email action.
        
        Supports:
        - compose: New email
        - reply: Reply to existing email
        - forward: Forward existing email
        """
        action_type = intent.get("action", "compose")
        
        if action_type == "compose":
            return DraftAction(
                agent=self.name,
                action_type="send_email",
                description=self._format_email_description(intent),
                params={
                    "to": intent.get("to", ""),
                    "cc": intent.get("cc", ""),
                    "subject": intent.get("subject", ""),
                    "body": intent.get("body", ""),
                    "account": intent.get("account", "default"),
                },
            )
        
        elif action_type == "reply":
            return DraftAction(
                agent=self.name,
                action_type="reply_email",
                description=f"Reply to: {intent.get('original_subject', 'email')}\n\n{intent.get('body', '')[:200]}",
                params={
                    "original_id": intent.get("original_id", ""),
                    "body": intent.get("body", ""),
                    "account": intent.get("account", "default"),
                },
            )
        
        elif action_type == "forward":
            return DraftAction(
                agent=self.name,
                action_type="forward_email",
                description=f"Forward to: {intent.get('to', '')}\nOriginal: {intent.get('original_subject', '')}",
                params={
                    "original_id": intent.get("original_id", ""),
                    "to": intent.get("to", ""),
                    "body": intent.get("body", ""),
                    "account": intent.get("account", "default"),
                },
            )
        
        else:
            return DraftAction(
                agent=self.name,
                action_type="unknown",
                description=f"Unknown email action: {action_type}",
                params=intent,
            )
    
    async def execute(self, action: DraftAction) -> str:
        """Execute an approved email action"""
        
        # Find the appropriate connector
        account = action.params.get("account", "default")
        connector = self._get_connector_for_account(account)
        
        if not connector:
            raise ValueError(f"No connector found for account: {account}")
        
        # Execute the action
        result = await connector.execute_action(
            action.action_type,
            action.params
        )
        
        return f"Email sent successfully via {connector.name}"
    
    def _get_connector_for_account(self, account: str) -> Optional[Connector]:
        """Find connector matching account name"""
        if account == "default" and self._connectors:
            return self._connectors[0]
        
        for connector in self._connectors:
            if account in connector.name or connector.config.name == account:
                return connector
        
        return None
    
    def _normalize_email(self, data: Dict[str, Any], account: str) -> Email:
        """Convert connector-specific data to unified Email format"""
        return Email(
            id=data.get("id", ""),
            subject=data.get("subject", "No subject"),
            sender=data.get("from_name", data.get("from", "")),
            sender_email=data.get("from_email", data.get("from", "")),
            recipients=data.get("to", []),
            body=data.get("body", data.get("snippet", "")),
            body_html=data.get("body_html"),
            date=data.get("date"),
            is_read=data.get("is_read", True),
            has_attachments=data.get("has_attachments", False),
            labels=data.get("labels", []),
            account=account,
            thread_id=data.get("thread_id"),
        )
    
    def _format_email_description(self, intent: Dict[str, Any]) -> str:
        """Format email for display"""
        lines = []
        lines.append(f"To: {intent.get('to', 'Not specified')}")
        if intent.get("cc"):
            lines.append(f"CC: {intent.get('cc')}")
        lines.append(f"Subject: {intent.get('subject', 'No subject')}")
        lines.append("")
        lines.append(intent.get("body", "")[:300])
        if len(intent.get("body", "")) > 300:
            lines.append("...")
        return "\n".join(lines)
    
    def get_capabilities(self) -> List[str]:
        return [
            "search emails across multiple accounts",
            "compose new emails (draft mode)",
            "reply to emails (draft mode)",
            "forward emails (draft mode)",
            "read email contents",
        ]
