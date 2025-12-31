"""Ollama LLM Provider - Primary local LLM backend"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, List, Optional, Dict
import ollama

from jarvis.core.llm_engine import LLMEngine, LLMResponse, Tool, ToolCall


# Default JARVIS system prompt
DEFAULT_SYSTEM_PROMPT = """You are JARVIS, an advanced AI assistant inspired by Tony Stark's AI.

**Personality:**
- Helpful, witty, and slightly formal
- Proactive in offering relevant information
- Concise but thorough

**Capabilities:**
- Real-time access to calendar, email, documents, and tasks
- Voice interaction through speech recognition and synthesis
- Autonomous execution of approved actions

**Behavior:**
- Anticipate needs before asked
- Provide concise, actionable responses
- Explain reasoning for complex decisions
- Use tools when appropriate to complete tasks

Always respond naturally as if speaking out loud. Keep responses concise for voice output."""


class OllamaProvider(LLMEngine):
    """
    Ollama-based LLM provider for local inference.
    
    Supports models like Qwen2.5, Llama, Phi-4, etc.
    Includes automatic fallback to secondary model on failure.
    """
    
    def __init__(
        self,
        fast_model: str = "qwen2.5:3b",
        primary_model: str = "qwen2.5:14b-instruct-q5_K_M",
        fallback_model: str = "phi4:latest",
        host: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        self.fast_model = fast_model
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.host = host
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = ollama.AsyncClient(host=host)
    
    async def reason(
        self,
        prompt: str,
        tools: Optional[List[Tool]] = None,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[list[dict]] = None,
        use_fast: bool = None,  # Override complexity detection
    ) -> LLMResponse:
        """Generate a response, with automatic fallback on failure"""
        
        # Build messages
        messages = []
        if system_prompt or DEFAULT_SYSTEM_PROMPT:
            messages.append({
                "role": "system",
                "content": system_prompt or DEFAULT_SYSTEM_PROMPT
            })
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": prompt})
        
        # Convert tools to Ollama format
        ollama_tools = None
        if tools:
            ollama_tools = [t.to_ollama_format() for t in tools]
        
        # Determine which model to use
        # Use fast model for simple queries, deep model for complex ones
        if use_fast is None:
            use_fast = self._is_simple_query(prompt, tools)
        
        selected_model = self.fast_model if use_fast else self.primary_model
        
        # Try selected model first
        try:
            response = await self._call_model(
                selected_model, messages, ollama_tools
            )
            return response
        except Exception as e:
            # If fast model failed on simple query, try primary
            if use_fast:
                print(f"Fast model failed, trying primary: {e}")
                try:
                    response = await self._call_model(
                        self.primary_model, messages, ollama_tools
                    )
                    return response
                except Exception as primary_error:
                    pass  # Fall through to fallback
            
            # Fallback to secondary model
            print(f"Selected model failed ({e}), falling back to {self.fallback_model}")
            try:
                response = await self._call_model(
                    self.fallback_model, messages, ollama_tools
                )
                return response
            except Exception as fallback_error:
                return LLMResponse(
                    content=f"I apologize, but I'm having trouble processing that request. Error: {fallback_error}",
                    tool_calls=[]
                )
    
    def _is_simple_query(self, prompt: str, tools: Optional[List[Tool]] = None) -> bool:
        """
        Determine if a query is simple enough for the fast model.
        
        Simple queries:
        - Greetings, small talk
        - Single tool calls (calendar, tasks)
        - Short factual questions
        
        Complex queries:
        - Multi-step reasoning
        - Code generation
        - Long-form writing
        - Deep analysis
        """
        prompt_lower = prompt.lower()
        
        # Greetings and simple conversation
        simple_patterns = [
            "hello", "hi ", "hey", "good morning", "good evening",
            "how are you", "what can you do", "help",
            "what's", "what is", "when is", "where is",
            "time", "date", "weather",
        ]
        
        if any(p in prompt_lower for p in simple_patterns):
            return True
        
        # Single tool call is simple
        if tools and len(tools) <= 2:
            return True
        
        # Short queries (<50 words) with no special complexity markers
        word_count = len(prompt.split())
        complex_markers = ["analyze", "explain", "write", "generate", "create", "design", "plan"]
        
        if word_count < 50 and not any(m in prompt_lower for m in complex_markers):
            return True
        
        # Default to deep thinking for safety
        return False
    
    async def _call_model(
        self,
        model: str,
        messages: list[dict],
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        """Make the actual API call to Ollama"""
        
        kwargs = {
            "model": model,
            "messages": messages,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            }
        }
        
        if tools:
            kwargs["tools"] = tools
        
        response = await self._client.chat(**kwargs)
        
        # Parse tool calls if present
        tool_calls = []
        if hasattr(response, "message") and hasattr(response.message, "tool_calls"):
            if response.message.tool_calls:
                for tc in response.message.tool_calls:
                    tool_calls.append(ToolCall(
                        name=tc.function.name,
                        arguments=tc.function.arguments
                    ))
        
        content = response.message.content if hasattr(response, "message") else str(response)
        
        return LLMResponse(
            content=content or "",
            tool_calls=tool_calls,
            raw_response=response
        )
    
    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[list[dict]] = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens for real-time TTS"""
        
        messages = []
        if system_prompt or DEFAULT_SYSTEM_PROMPT:
            messages.append({
                "role": "system",
                "content": system_prompt or DEFAULT_SYSTEM_PROMPT
            })
        
        # Include conversation history for context
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": prompt})

        
        try:
            stream = await self._client.chat(
                model=self.primary_model,
                messages=messages,
                stream=True,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                }
            )
            
            async for chunk in stream:
                if hasattr(chunk, "message") and chunk.message.content:
                    yield chunk.message.content
                    
        except Exception as e:
            yield f"Error streaming response: {e}"
    
    async def health_check(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            models = await self._client.list()
            available = [m.model for m in models.models]
            
            # Check if primary or fallback is available
            return (
                self.primary_model in available or 
                self.fallback_model in available or
                any(self.primary_model.split(":")[0] in m for m in available)
            )
        except Exception:
            return False
    
    async def ensure_model(self, model: str) -> bool:
        """Pull model if not available"""
        try:
            await self._client.pull(model)
            return True
        except Exception as e:
            print(f"Failed to pull model {model}: {e}")
            return False
