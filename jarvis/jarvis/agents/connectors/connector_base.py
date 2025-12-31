"""
JARVIS Connector Base - Abstract base class for account-specific API clients

Connectors handle authentication and API communication with external services.
Each agent uses one or more connectors to access different accounts/services.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConnectorConfig:
    """Configuration for a connector"""
    name: str                          # Friendly name (e.g., "work", "personal")
    connector_type: str                # Type (e.g., "gmail", "outlook")
    credentials_path: Optional[str] = None
    api_key: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class Connector(ABC):
    """
    Abstract base class for account-specific API connectors.
    
    Each connector represents a single account/service connection:
    - Gmail account
    - Outlook account
    - Google Calendar
    - Transit API
    
    Connectors handle:
    - Authentication (OAuth, API keys, etc.)
    - API requests
    - Rate limiting
    - Token refresh
    """
    
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self._authenticated = False
    
    @property
    def name(self) -> str:
        """Unique name for this connector instance"""
        return f"{self.config.connector_type}:{self.config.name}"
    
    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Type of connector (gmail, outlook, google_calendar, etc.)"""
        pass
    
    @property
    def is_authenticated(self) -> bool:
        """Whether connector is currently authenticated"""
        return self._authenticated
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the service.
        
        Returns:
            True if authentication successful
        """
        pass
    
    @abstractmethod
    async def search(self, criteria: Dict[str, Any]) -> List[Any]:
        """
        Search this connector's data.
        
        Args:
            criteria: Search parameters specific to this connector type
            
        Returns:
            List of matching items
        """
        pass
    
    @abstractmethod
    async def execute_action(self, action_type: str, params: Dict[str, Any]) -> Any:
        """
        Execute an action through this connector.
        
        Args:
            action_type: Type of action (send_email, create_event, etc.)
            params: Action parameters
            
        Returns:
            Action result
        """
        pass
    
    async def setup(self) -> None:
        """Initialize connector (called by agent.setup())"""
        await self.authenticate()
    
    async def health_check(self) -> bool:
        """Check if connector is functional"""
        return self._authenticated
    
    async def refresh_auth(self) -> bool:
        """Refresh authentication if needed"""
        return await self.authenticate()
