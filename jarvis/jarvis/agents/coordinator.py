"""
JARVIS Agent Coordinator - Central routing and orchestration for domain agents

Routes user queries to appropriate agents, aggregates results,
and manages the draft action workflow.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from jarvis.agents.agent_base import Agent, DraftAction, ActionStatus
from jarvis.agents.action_queue import ActionQueue
from jarvis.core.llm_engine import Tool

if TYPE_CHECKING:
    from jarvis.core.memory_store import MemoryStore


class AgentCoordinator:
    """
    Central coordinator for all domain agents.
    
    Responsibilities:
    - Route user queries to appropriate agent(s)
    - Aggregate results from multiple agents
    - Manage draft action queue
    - Handle approve/reject/edit commands
    - Provide tools for the main orchestrator
    """
    
    def __init__(self, memory_store: Optional["MemoryStore"] = None):
        self._agents: Dict[str, Agent] = {}
        self._action_queue = ActionQueue()
        self._memory_store = memory_store
    
    def register_agent(self, agent: Agent) -> None:
        """Register a domain agent"""
        self._agents[agent.name] = agent
    
    def get_agent(self, name: str) -> Optional[Agent]:
        """Get a specific agent by name"""
        return self._agents.get(name)
    
    @property
    def agents(self) -> Dict[str, Agent]:
        """All registered agents"""
        return self._agents
    
    @property
    def action_queue(self) -> ActionQueue:
        """The action queue"""
        return self._action_queue
    
    def get_tools(self) -> List[Tool]:
        """
        Get tools for integration with JARVISOrchestrator.
        
        Provides high-level tools that route to appropriate agents.
        """
        return [
            Tool(
                name="search_emails",
                description="Search emails across all connected email accounts (Gmail, Outlook)",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'from:john meeting notes')",
                    },
                    "accounts": {
                        "type": "string",
                        "description": "Which accounts to search: 'all' or comma-separated list",
                    },
                }
            ),
            Tool(
                name="draft_email",
                description="Create a draft email for user review (not sent until approved)",
                parameters={
                    "to": {
                        "type": "string",
                        "description": "Recipient email address(es)",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line",
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body content",
                    },
                    "account": {
                        "type": "string",
                        "description": "Which account to send from",
                    },
                }
            ),
            Tool(
                name="get_calendar_unified",
                description="Get calendar events from all connected calendars",
                parameters={
                    "hours": {
                        "type": "integer",
                        "description": "Hours to look ahead (default: 24)",
                    },
                }
            ),
            Tool(
                name="get_next_train",
                description="Get next train/transit departure from a station",
                parameters={
                    "station": {
                        "type": "string",
                        "description": "Station name or 'current_location'",
                    },
                    "destination": {
                        "type": "string",
                        "description": "Optional destination station",
                    },
                }
            ),
            Tool(
                name="list_pending_actions",
                description="List all pending draft actions awaiting approval",
                parameters={}
            ),
            Tool(
                name="approve_action",
                description="Approve a pending draft action for execution",
                parameters={
                    "action_id": {
                        "type": "string",
                        "description": "ID of the action to approve",
                    },
                }
            ),
            Tool(
                name="reject_action",
                description="Reject/cancel a pending draft action",
                parameters={
                    "action_id": {
                        "type": "string",
                        "description": "ID of the action to reject",
                    },
                }
            ),
        ]
    
    async def execute_tool(self, tool_name: str, params: dict) -> str:
        """Execute a coordinator tool"""
        
        if tool_name == "search_emails":
            return await self._search_emails(params)
        
        elif tool_name == "draft_email":
            return await self._draft_email(params)
        
        elif tool_name == "get_calendar_unified":
            return await self._get_calendar_unified(params)
        
        elif tool_name == "get_next_train":
            return await self._get_next_train(params)
        
        elif tool_name == "list_pending_actions":
            return self._list_pending_actions()
        
        elif tool_name == "approve_action":
            return await self._approve_action(params.get("action_id", ""))
        
        elif tool_name == "reject_action":
            return self._reject_action(params.get("action_id", ""))
        
        else:
            return f"Unknown coordinator tool: {tool_name}"
    
    async def _search_emails(self, params: dict) -> str:
        """Search emails across all accounts"""
        email_agent = self._agents.get("email")
        if not email_agent:
            return "Email agent not configured. Please set up email accounts in config."
        
        try:
            results = await email_agent.search({
                "query": params.get("query", ""),
                "accounts": params.get("accounts", "all"),
            })
            
            if not results:
                return "No emails found matching your search."
            
            # Format results
            lines = [f"Found {len(results)} emails:\n"]
            for email in results[:10]:  # Limit to 10
                lines.append(f"• {email.get('subject', 'No subject')} - {email.get('from', 'Unknown')}")
            
            if len(results) > 10:
                lines.append(f"\n... and {len(results) - 10} more")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error searching emails: {e}"
    
    async def _draft_email(self, params: dict) -> str:
        """Create a draft email action"""
        email_agent = self._agents.get("email")
        if not email_agent:
            return "Email agent not configured."
        
        # Create draft action
        action = DraftAction(
            agent="email",
            action_type="send_email",
            description=f"Send email to {params.get('to')}\nSubject: {params.get('subject')}\n\n{params.get('body', '')[:200]}...",
            params={
                "to": params.get("to", ""),
                "subject": params.get("subject", ""),
                "body": params.get("body", ""),
                "account": params.get("account", "default"),
            },
        )
        
        # Add to queue
        self._action_queue.add(action)
        
        return f"""📧 Draft email created!

To: {params.get('to')}
Subject: {params.get('subject')}
Account: {params.get('account', 'default')}

{params.get('body', '')[:300]}{'...' if len(params.get('body', '')) > 300 else ''}

---
Action ID: {action.id}
Say "approve {action.id}" to send, or "reject {action.id}" to cancel."""
    
    async def _get_calendar_unified(self, params: dict) -> str:
        """Get unified calendar view"""
        calendar_agent = self._agents.get("calendar")
        if not calendar_agent:
            # Fall back to legacy calendar integration
            return "Calendar agent not configured. Using legacy calendar integration."
        
        try:
            hours = params.get("hours", 24)
            results = await calendar_agent.search({"hours": hours})
            
            if not results:
                return f"No events in the next {hours} hours."
            
            lines = [f"📅 Events in the next {hours} hours:\n"]
            for event in results:
                lines.append(f"• {event.get('title', 'Untitled')} - {event.get('start', 'Unknown time')}")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error getting calendar: {e}"
    
    async def _get_next_train(self, params: dict) -> str:
        """Get next train departure"""
        transport_agent = self._agents.get("transport")
        if not transport_agent:
            return "Transport agent not configured. Please set up transit API in config."
        
        try:
            results = await transport_agent.search({
                "station": params.get("station", ""),
                "destination": params.get("destination"),
            })
            
            if not results:
                return "No upcoming departures found."
            
            lines = ["🚆 Upcoming departures:\n"]
            for trip in results[:5]:
                lines.append(f"• {trip.get('route', '')} to {trip.get('destination', '')} at {trip.get('time', '')}")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error getting train info: {e}"
    
    def _list_pending_actions(self) -> str:
        """List all pending actions"""
        pending = self._action_queue.get_pending()
        
        if not pending:
            return "No pending actions."
        
        lines = [f"📋 {len(pending)} pending action(s):\n"]
        for action in pending:
            lines.append(f"[{action.id}] {action.agent}: {action.action_type}")
            lines.append(f"    {action.description[:60]}...")
            lines.append("")
        
        lines.append("Say 'approve <id>' or 'reject <id>' to manage actions.")
        return "\n".join(lines)
    
    async def _approve_action(self, action_id: str) -> str:
        """Approve and execute an action"""
        action = self._action_queue.get(action_id)
        if not action:
            return f"Action {action_id} not found."
        
        if action.status != ActionStatus.PENDING:
            return f"Action {action_id} is not pending (status: {action.status.value})"
        
        # Mark as approved
        self._action_queue.approve(action_id)
        
        # Get the agent and execute
        agent = self._agents.get(action.agent)
        if not agent:
            self._action_queue.fail(action_id, f"Agent '{action.agent}' not available")
            return f"Error: Agent '{action.agent}' not configured."
        
        try:
            result = await agent.execute(action)
            self._action_queue.complete(action_id, result)
            return f"✅ Action {action_id} executed successfully!\n{result}"
        except Exception as e:
            error_msg = str(e)
            self._action_queue.fail(action_id, error_msg)
            return f"❌ Action {action_id} failed: {error_msg}"
    
    def _reject_action(self, action_id: str) -> str:
        """Reject an action"""
        action = self._action_queue.get(action_id)
        if not action:
            return f"Action {action_id} not found."
        
        self._action_queue.reject(action_id)
        return f"🚫 Action {action_id} rejected and removed from queue."
    
    async def setup(self) -> None:
        """Initialize all registered agents"""
        for agent in self._agents.values():
            await agent.setup()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all agents"""
        results = {}
        for name, agent in self._agents.items():
            results[name] = await agent.health_check()
        return results
    
    def handle_action_command(self, text: str) -> Optional[str]:
        """
        Check if text is an action command (approve/reject/edit).
        
        Returns response if it was a command, None otherwise.
        """
        text = text.strip().lower()
        
        # Check for approve command
        match = re.match(r'^approve\s+(\S+)$', text)
        if match:
            # Note: This is sync, caller should use execute_tool for async
            return f"Approving action {match.group(1)}..."
        
        # Check for reject command
        match = re.match(r'^reject\s+(\S+)$', text)
        if match:
            return self._reject_action(match.group(1))
        
        return None
