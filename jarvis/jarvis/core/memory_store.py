"""
JARVIS Memory Store - Persistent memory for user identity and preferences

Provides SQLite-backed storage for:
- User profile (name, identity, key facts)
- Preferences (likes, dislikes, preferred styles)
- Long-term memories (facts, context)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json


@dataclass
class UserProfile:
    """User identity and profile information"""
    name: Optional[str] = None
    facts: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass  
class Preference:
    """A user preference"""
    category: str  # e.g., "programming", "communication", "scheduling"
    key: str       # e.g., "language", "meeting_time"
    value: str     # e.g., "Python", "morning"
    created_at: Optional[datetime] = None


@dataclass
class Memory:
    """A stored memory/fact"""
    id: Optional[int] = None
    content: str = ""
    category: str = "general"  # fact, preference, context, personal
    importance: int = 5        # 1-10 scale
    created_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None


class MemoryStore:
    """
    SQLite-backed persistent memory store.
    
    Stores user profile, preferences, and memories that persist
    across JARVIS sessions.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path.home() / ".jarvis" / "memory.db")
        
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # User profile table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    facts TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key)
                )
            """)
            
            # Memories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    importance INTEGER DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for faster searches
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_category 
                ON memories(category)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_importance 
                ON memories(importance DESC)
            """)
            
            conn.commit()
    
    # ========== User Profile Methods ==========
    
    def get_user_profile(self) -> UserProfile:
        """Retrieve the user profile"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, facts, created_at, updated_at FROM user_profile LIMIT 1")
            row = cursor.fetchone()
            
            if row:
                facts = json.loads(row[1]) if row[1] else []
                return UserProfile(
                    name=row[0],
                    facts=facts,
                    created_at=datetime.fromisoformat(row[2]) if row[2] else None,
                    updated_at=datetime.fromisoformat(row[3]) if row[3] else None,
                )
            return UserProfile()
    
    def save_user_profile(self, profile: UserProfile) -> None:
        """Save or update the user profile"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            facts_json = json.dumps(profile.facts)
            
            # Check if profile exists
            cursor.execute("SELECT COUNT(*) FROM user_profile")
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                cursor.execute("""
                    UPDATE user_profile 
                    SET name = ?, facts = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (profile.name, facts_json))
            else:
                cursor.execute("""
                    INSERT INTO user_profile (name, facts) VALUES (?, ?)
                """, (profile.name, facts_json))
            
            conn.commit()
    
    def set_user_name(self, name: str) -> None:
        """Set the user's name"""
        profile = self.get_user_profile()
        profile.name = name
        self.save_user_profile(profile)
    
    def add_user_fact(self, fact: str) -> None:
        """Add a fact about the user"""
        profile = self.get_user_profile()
        if fact not in profile.facts:
            profile.facts.append(fact)
            self.save_user_profile(profile)
    
    # ========== Preference Methods ==========
    
    def set_preference(self, category: str, key: str, value: str) -> None:
        """Set or update a preference"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO preferences (category, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(category, key) DO UPDATE SET value = ?
            """, (category, key, value, value))
            conn.commit()
    
    def get_preference(self, category: str, key: str) -> Optional[str]:
        """Get a specific preference"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM preferences WHERE category = ? AND key = ?",
                (category, key)
            )
            row = cursor.fetchone()
            return row[0] if row else None
    
    def get_all_preferences(self) -> List[Preference]:
        """Get all stored preferences"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category, key, value, created_at FROM preferences")
            rows = cursor.fetchall()
            
            return [
                Preference(
                    category=row[0],
                    key=row[1],
                    value=row[2],
                    created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                )
                for row in rows
            ]
    
    # ========== Memory Methods ==========
    
    def add_memory(
        self, 
        content: str, 
        category: str = "general",
        importance: int = 5
    ) -> int:
        """Store a new memory"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memories (content, category, importance)
                VALUES (?, ?, ?)
            """, (content, category, importance))
            conn.commit()
            return cursor.lastrowid
    
    def search_memories(
        self, 
        query: str, 
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Memory]:
        """Search memories by keyword"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if category:
                cursor.execute("""
                    SELECT id, content, category, importance, created_at, last_accessed
                    FROM memories 
                    WHERE content LIKE ? AND category = ?
                    ORDER BY importance DESC, created_at DESC
                    LIMIT ?
                """, (f"%{query}%", category, limit))
            else:
                cursor.execute("""
                    SELECT id, content, category, importance, created_at, last_accessed
                    FROM memories 
                    WHERE content LIKE ?
                    ORDER BY importance DESC, created_at DESC
                    LIMIT ?
                """, (f"%{query}%", limit))
            
            rows = cursor.fetchall()
            
            # Update last_accessed for returned memories
            memory_ids = [row[0] for row in rows]
            if memory_ids:
                placeholders = ",".join("?" * len(memory_ids))
                cursor.execute(f"""
                    UPDATE memories SET last_accessed = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                """, memory_ids)
                conn.commit()
            
            return [
                Memory(
                    id=row[0],
                    content=row[1],
                    category=row[2],
                    importance=row[3],
                    created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    last_accessed=datetime.fromisoformat(row[5]) if row[5] else None,
                )
                for row in rows
            ]
    
    def get_recent_memories(self, limit: int = 20) -> List[Memory]:
        """Get most recent memories"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, content, category, importance, created_at, last_accessed
                FROM memories 
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [
                Memory(
                    id=row[0],
                    content=row[1],
                    category=row[2],
                    importance=row[3],
                    created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    last_accessed=datetime.fromisoformat(row[5]) if row[5] else None,
                )
                for row in cursor.fetchall()
            ]
    
    def get_important_memories(self, min_importance: int = 7, limit: int = 10) -> List[Memory]:
        """Get high-importance memories"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, content, category, importance, created_at, last_accessed
                FROM memories 
                WHERE importance >= ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
            """, (min_importance, limit))
            
            return [
                Memory(
                    id=row[0],
                    content=row[1],
                    category=row[2],
                    importance=row[3],
                    created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    last_accessed=datetime.fromisoformat(row[5]) if row[5] else None,
                )
                for row in cursor.fetchall()
            ]
    
    def delete_memory(self, memory_id: int) -> bool:
        """Delete a specific memory"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # ========== Utility Methods ==========
    
    def clear_all(self) -> None:
        """Clear all stored data (use with caution!)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_profile")
            cursor.execute("DELETE FROM preferences")
            cursor.execute("DELETE FROM memories")
            conn.commit()
    
    def get_context_summary(self) -> str:
        """
        Get a summary of stored context for injection into system prompt.
        
        Returns a formatted string with user profile, preferences, and
        key memories for the LLM to use.
        """
        profile = self.get_user_profile()
        preferences = self.get_all_preferences()
        important_memories = self.get_important_memories(min_importance=7, limit=5)
        
        parts = []
        
        # User identity
        if profile.name:
            parts.append(f"User's name: {profile.name}")
        
        if profile.facts:
            parts.append("Known facts about user:")
            for fact in profile.facts[:5]:  # Limit to 5 facts
                parts.append(f"  - {fact}")
        
        # Preferences
        if preferences:
            parts.append("\nUser preferences:")
            for pref in preferences[:10]:  # Limit to 10 preferences
                parts.append(f"  - {pref.category}/{pref.key}: {pref.value}")
        
        # Important memories
        if important_memories:
            parts.append("\nImportant context:")
            for mem in important_memories:
                parts.append(f"  - {mem.content}")
        
        return "\n".join(parts) if parts else ""
    
    def get_stats(self) -> dict:
        """Get memory statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM memories")
            memory_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM preferences")
            pref_count = cursor.fetchone()[0]
            
            profile = self.get_user_profile()
            
            return {
                "has_profile": profile.name is not None,
                "user_name": profile.name,
                "fact_count": len(profile.facts),
                "preference_count": pref_count,
                "memory_count": memory_count,
                "db_path": str(self.db_path),
            }
