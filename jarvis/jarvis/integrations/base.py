"""Base integration class with tool registration"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List

from jarvis.core.llm_engine import Tool


class Integration(ABC):
    """
    Abstract base class for JARVIS integrations.
    
    Each integration provides:
    - A set of tools the LLM can call
    - Implementation of those tools
    - Health checking
    
    Implement this to add new capabilities like:
    - Calendar access
    - Email management
    - Document search
    - Task tracking
    - Web search
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this integration"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description"""
        pass
    
    @property
    @abstractmethod
    def tools(self) -> List[Tool]:
        """
        Return list of tools this integration provides.
        
        These will be passed to the LLM for function calling.
        """
        pass
    
    @abstractmethod
    async def execute(self, tool_name: str, params: dict) -> Any:
        """
        Execute a tool call.
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool
            
        Returns:
            Result of the tool execution (will be stringified for LLM)
        """
        pass
    
    async def setup(self) -> None:
        """
        Optional setup/initialization.
        Called when integration is loaded.
        """
        pass
    
    async def health_check(self) -> bool:
        """Check if integration is functional"""
        return True
