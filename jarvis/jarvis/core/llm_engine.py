"""Abstract LLM Engine with tool calling support"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from typing import AsyncIterator


@dataclass
class Tool:
    """Definition of a callable tool for the LLM"""
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    
    def to_ollama_format(self) -> dict:
        """Convert to Ollama tool format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": list(self.parameters.keys())
                }
            }
        }


@dataclass
class ToolCall:
    """A tool call made by the LLM"""
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    """Response from an LLM query"""
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw_response: Optional[Any] = None


class LLMEngine(ABC):
    """
    Abstract base class for LLM providers.
    
    Implement this interface to add new LLM backends.
    The engine must support:
    - Basic text generation
    - Tool/function calling
    - Streaming responses
    """
    
    @abstractmethod
    async def reason(
        self,
        prompt: str,
        tools: Optional[list[Tool]] = None,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[list[dict]] = None,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User's message/query
            tools: Available tools the LLM can call
            system_prompt: System instructions for the LLM
            conversation_history: Previous messages for context
            
        Returns:
            LLMResponse with content and any tool calls
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream response tokens for real-time TTS.
        
        Yields individual tokens/chunks as they're generated.
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM backend is available"""
        pass
