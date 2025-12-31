"""
JARVIS Memory Integration - LLM-accessible memory tools

Provides tools for the LLM to:
- Remember facts about the user
- Recall user profile and preferences
- Search stored memories
- Update preferences
"""

from __future__ import annotations

from typing import Any, List

from jarvis.core.llm_engine import Tool
from jarvis.core.memory_store import MemoryStore
from jarvis.integrations.base import Integration


class MemoryIntegration(Integration):
    """
    Integration exposing memory capabilities to the LLM.
    
    Allows JARVIS to remember information about the user,
    learn preferences, and maintain context across sessions.
    """
    
    def __init__(self, db_path: str = None):
        self.memory = MemoryStore(db_path)
    
    @property
    def name(self) -> str:
        return "memory"
    
    @property
    def description(self) -> str:
        return "Persistent memory for user information and preferences"
    
    @property
    def tools(self) -> List[Tool]:
        return [
            Tool(
                name="remember_about_user",
                description="Store a fact or piece of information about the user. Use this when the user shares personal information like their name, job, preferences, or important facts about themselves.",
                parameters={
                    "fact": {
                        "type": "string",
                        "description": "The fact to remember about the user"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category: 'personal' (name, job, etc), 'preference' (likes/dislikes), 'context' (current projects, goals)"
                    },
                    "importance": {
                        "type": "integer",
                        "description": "How important is this? 1-10 scale (10 = very important)"
                    }
                }
            ),
            Tool(
                name="set_user_name",
                description="Set or update the user's name. Use when the user tells you their name.",
                parameters={
                    "name": {
                        "type": "string",
                        "description": "The user's name"
                    }
                }
            ),
            Tool(
                name="recall_user_info",
                description="Retrieve stored information about the user including their name, facts, and preferences. Use this at the start of conversations or when you need to personalize a response.",
                parameters={}
            ),
            Tool(
                name="set_preference",
                description="Store or update a user preference. Use when the user expresses a preference like 'I prefer Python' or 'I like morning meetings'.",
                parameters={
                    "category": {
                        "type": "string",
                        "description": "Category of preference (e.g., 'programming', 'scheduling', 'communication', 'work')"
                    },
                    "key": {
                        "type": "string",
                        "description": "What the preference is about (e.g., 'language', 'meeting_time', 'response_style')"
                    },
                    "value": {
                        "type": "string",
                        "description": "The preferred value (e.g., 'Python', 'morning', 'concise')"
                    }
                }
            ),
            Tool(
                name="search_memory",
                description="Search stored memories for specific information. Use when you need to recall something specific the user has told you before.",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Keywords to search for in memories"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional: filter by category (personal, preference, context, general)"
                    }
                }
            ),
        ]
    
    async def execute(self, tool_name: str, params: dict) -> Any:
        """Execute a memory tool"""
        
        if tool_name == "remember_about_user":
            fact = params.get("fact", "")
            category = params.get("category", "general")
            importance = params.get("importance", 5)
            
            # Store as both a memory and potentially as a user fact
            self.memory.add_memory(fact, category=category, importance=importance)
            
            # If high importance, also add to user facts
            if importance >= 7:
                self.memory.add_user_fact(fact)
            
            return f"Remembered: {fact}"
        
        elif tool_name == "set_user_name":
            name = params.get("name", "")
            self.memory.set_user_name(name)
            return f"User name set to: {name}"
        
        elif tool_name == "recall_user_info":
            profile = self.memory.get_user_profile()
            preferences = self.memory.get_all_preferences()
            
            info_parts = []
            
            if profile.name:
                info_parts.append(f"Name: {profile.name}")
            else:
                info_parts.append("Name: Not yet known")
            
            if profile.facts:
                info_parts.append("Known facts:")
                for fact in profile.facts:
                    info_parts.append(f"  - {fact}")
            
            if preferences:
                info_parts.append("Preferences:")
                for pref in preferences:
                    info_parts.append(f"  - {pref.category}/{pref.key}: {pref.value}")
            
            if not profile.name and not profile.facts and not preferences:
                return "No user information stored yet. Ask the user about themselves to learn more!"
            
            return "\n".join(info_parts)
        
        elif tool_name == "set_preference":
            category = params.get("category", "general")
            key = params.get("key", "")
            value = params.get("value", "")
            
            self.memory.set_preference(category, key, value)
            return f"Preference saved: {category}/{key} = {value}"
        
        elif tool_name == "search_memory":
            query = params.get("query", "")
            category = params.get("category")
            
            memories = self.memory.search_memories(query, category=category)
            
            if not memories:
                return f"No memories found matching '{query}'"
            
            results = [f"Found {len(memories)} memories:"]
            for mem in memories:
                results.append(f"  - [{mem.category}] {mem.content}")
            
            return "\n".join(results)
        
        return f"Unknown memory tool: {tool_name}"
    
    async def setup(self) -> None:
        """Initialize memory store"""
        # Database is initialized in MemoryStore constructor
        pass
    
    async def health_check(self) -> bool:
        """Check if memory store is accessible"""
        try:
            self.memory.get_stats()
            return True
        except Exception:
            return False
    
    def get_context_for_prompt(self) -> str:
        """Get memory context to inject into system prompt"""
        return self.memory.get_context_summary()
