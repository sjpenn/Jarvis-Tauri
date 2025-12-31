"""
JARVIS Agent Base - Abstract base class for domain agents

All agents support draft mode: actions are proposed, not executed immediately.
Users must approve, edit, or reject before execution.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.agents.connectors.connector_base import Connector


class ActionStatus(Enum):
    """Status of a draft action"""
    PENDING = "pending"       # Awaiting user decision
    APPROVED = "approved"     # User approved, ready to execute
    REJECTED = "rejected"     # User rejected
    MODIFIED = "modified"     # User modified, awaiting re-approval
    EXECUTING = "executing"   # Currently executing
    COMPLETED = "completed"   # Successfully executed
    FAILED = "failed"         # Execution failed


@dataclass
class DraftAction:
    """
    A proposed action awaiting user approval.
    
    Actions are created by agents but not executed until explicitly approved.
    This ensures JARVIS never takes irreversible actions without consent.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent: str = ""              # Which agent created this (email, calendar, etc.)
    action_type: str = ""        # Specific action (send_email, create_event, etc.)
    description: str = ""        # Human-readable summary for user
    params: Dict[str, Any] = field(default_factory=dict)  # Execution parameters
    status: ActionStatus = ActionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    result: Optional[str] = None  # Execution result or error message
    
    def to_display(self) -> str:
        """Format action for user display"""
        return f"""
📋 Draft Action [{self.id}]
Agent: {self.agent}
Action: {self.action_type}
Status: {self.status.value}

{self.description}

Commands: [approve {self.id}] [edit {self.id}] [reject {self.id}]
"""

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "agent": self.agent,
            "action_type": self.action_type,
            "description": self.description,
            "params": self.params,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "result": self.result,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DraftAction":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            agent=data["agent"],
            action_type=data["action_type"],
            description=data["description"],
            params=data.get("params", {}),
            status=ActionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            modified_at=datetime.fromisoformat(data["modified_at"]) if data.get("modified_at") else None,
            executed_at=datetime.fromisoformat(data["executed_at"]) if data.get("executed_at") else None,
            result=data.get("result"),
        )


class Agent(ABC):
    """
    Abstract base class for all domain agents.
    
    Each agent:
    - Manages one or more connectors (e.g., email agent has Gmail + Outlook connectors)
    - Understands natural language queries for its domain
    - Aggregates data across all its connectors
    - Proposes actions in draft mode for user approval
    - Executes approved actions
    
    Implement this to add new domains like:
    - Email (Gmail, Outlook)
    - Calendar (Google, macOS, Outlook)
    - Transportation (MTA, NJ Transit, etc.)
    - Tasks/Reminders
    - Documents/Files
    """
    
    def __init__(self):
        self._connectors: List[Connector] = []
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent (e.g., 'email', 'calendar')"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of agent capabilities"""
        pass
    
    @property
    def connectors(self) -> List["Connector"]:
        """List of registered connectors"""
        return self._connectors
    
    def register_connector(self, connector: "Connector") -> None:
        """Add a connector to this agent"""
        self._connectors.append(connector)
    
    @abstractmethod
    async def understand(self, query: str) -> Dict[str, Any]:
        """
        Parse user intent from natural language.
        
        Args:
            query: User's natural language request
            
        Returns:
            Structured intent with action type and parameters
            Example: {"action": "search", "query": "emails from John", "date_range": "7d"}
        """
        pass
    
    @abstractmethod
    async def search(self, criteria: Dict[str, Any]) -> List[Any]:
        """
        Aggregate search across all connectors.
        
        Args:
            criteria: Structured search criteria from understand()
            
        Returns:
            Combined results from all connectors, sorted/deduplicated
        """
        pass
    
    @abstractmethod
    async def propose_action(self, intent: Dict[str, Any]) -> DraftAction:
        """
        Create a draft action for user approval.
        
        This is the core of draft mode: agents propose, users approve.
        
        Args:
            intent: Structured intent from understand()
            
        Returns:
            DraftAction ready for user review
        """
        pass
    
    @abstractmethod
    async def execute(self, action: DraftAction) -> str:
        """
        Execute an approved action.
        
        Only called after user explicitly approves the action.
        
        Args:
            action: The approved DraftAction
            
        Returns:
            Human-readable result message
        """
        pass
    
    async def setup(self) -> None:
        """Initialize agent and all connectors"""
        for connector in self._connectors:
            await connector.setup()
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of agent and all connectors"""
        results = {}
        for connector in self._connectors:
            results[connector.name] = await connector.health_check()
        return results
    
    def get_capabilities(self) -> List[str]:
        """List what this agent can do"""
        return []
