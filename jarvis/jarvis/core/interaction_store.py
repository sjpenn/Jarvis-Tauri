"""
JARVIS Interaction Store - Persistent logging of all interactions

Provides SQLite-backed storage for:
- Conversations (sessions)
- Messages (user queries and assistant responses)
- Tool calls (what tools were invoked and results)
- Feedback (user ratings and corrections)
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Conversation:
    """A conversation session"""
    id: Optional[int] = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0


@dataclass
class Message:
    """A single message in a conversation"""
    id: Optional[int] = None
    conversation_id: int = 0
    role: str = "user"  # user, assistant, system
    content: str = ""
    tokens: Optional[int] = None
    model: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """Record of a tool invocation"""
    id: Optional[int] = None
    message_id: int = 0
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    success: bool = True
    created_at: Optional[datetime] = None


@dataclass
class Feedback:
    """User feedback on a message"""
    id: Optional[int] = None
    message_id: int = 0
    rating: int = 0  # -1 (thumbs down), 0 (neutral), 1 (thumbs up)
    correction: Optional[str] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


class InteractionStore:
    """
    SQLite-backed persistent interaction store.
    
    Logs all JARVIS interactions for analysis and training.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path.home() / ".jarvis" / "interactions.db")
        
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    metadata TEXT,
                    message_count INTEGER DEFAULT 0
                )
            """)
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tokens INTEGER,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            
            # Tool calls table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    result TEXT,
                    success BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages(id)
                )
            """)
            
            # Feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    correction TEXT,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages(id)
                )
            """)
            
            # Create indexes for faster searches
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                ON messages(conversation_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_created 
                ON messages(created_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tool_calls_message 
                ON tool_calls(message_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_message 
                ON feedback(message_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_rating 
                ON feedback(rating)
            """)
            
            conn.commit()
    
    # ========== Conversation Methods ==========
    
    def start_conversation(
        self, 
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Start a new conversation session"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            metadata_json = json.dumps(metadata or {})
            
            cursor.execute("""
                INSERT INTO conversations (session_id, metadata)
                VALUES (?, ?)
            """, (session_id, metadata_json))
            
            conn.commit()
            return cursor.lastrowid
    
    def end_conversation(self, conversation_id: int) -> None:
        """Mark a conversation as ended"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversations 
                SET ended_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (conversation_id,))
            conn.commit()
    
    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get a conversation by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, session_id, started_at, ended_at, metadata, message_count
                FROM conversations
                WHERE id = ?
            """, (conversation_id,))
            row = cursor.fetchone()
            
            if row:
                return Conversation(
                    id=row[0],
                    session_id=row[1],
                    started_at=datetime.fromisoformat(row[2]) if row[2] else None,
                    ended_at=datetime.fromisoformat(row[3]) if row[3] else None,
                    metadata=json.loads(row[4]) if row[4] else {},
                    message_count=row[5],
                )
            return None
    
    def get_active_conversation(self) -> Optional[Conversation]:
        """Get the most recent active (not ended) conversation"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, session_id, started_at, ended_at, metadata, message_count
                FROM conversations
                WHERE ended_at IS NULL
                ORDER BY started_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            
            if row:
                return Conversation(
                    id=row[0],
                    session_id=row[1],
                    started_at=datetime.fromisoformat(row[2]) if row[2] else None,
                    ended_at=datetime.fromisoformat(row[3]) if row[3] else None,
                    metadata=json.loads(row[4]) if row[4] else {},
                    message_count=row[5],
                )
            return None
    
    # ========== Message Methods ==========
    
    def log_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        tokens: Optional[int] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Log a message in a conversation"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            metadata_json = json.dumps(metadata or {})
            
            cursor.execute("""
                INSERT INTO messages (conversation_id, role, content, tokens, model, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (conversation_id, role, content, tokens, model, metadata_json))
            
            # Update message count
            cursor.execute("""
                UPDATE conversations 
                SET message_count = message_count + 1
                WHERE id = ?
            """, (conversation_id,))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_messages(
        self, 
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get all messages in a conversation"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, conversation_id, role, content, tokens, model, created_at, metadata
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, (conversation_id,))
            
            return [
                Message(
                    id=row[0],
                    conversation_id=row[1],
                    role=row[2],
                    content=row[3],
                    tokens=row[4],
                    model=row[5],
                    created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    metadata=json.loads(row[7]) if row[7] else {},
                )
                for row in cursor.fetchall()
            ]
    
    # ========== Tool Call Methods ==========
    
    def log_tool_call(
        self,
        message_id: int,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Optional[str] = None,
        success: bool = True
    ) -> int:
        """Log a tool call"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            arguments_json = json.dumps(arguments)
            
            cursor.execute("""
                INSERT INTO tool_calls (message_id, tool_name, arguments, result, success)
                VALUES (?, ?, ?, ?, ?)
            """, (message_id, tool_name, arguments_json, result, success))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_tool_calls(self, message_id: int) -> List[ToolCall]:
        """Get all tool calls for a message"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, message_id, tool_name, arguments, result, success, created_at
                FROM tool_calls
                WHERE message_id = ?
                ORDER BY created_at ASC
            """, (message_id,))
            
            return [
                ToolCall(
                    id=row[0],
                    message_id=row[1],
                    tool_name=row[2],
                    arguments=json.loads(row[3]) if row[3] else {},
                    result=row[4],
                    success=bool(row[5]),
                    created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                )
                for row in cursor.fetchall()
            ]
    
    # ========== Feedback Methods ==========
    
    def log_feedback(
        self,
        message_id: int,
        rating: int,
        correction: Optional[str] = None,
        comment: Optional[str] = None
    ) -> int:
        """Log user feedback on a message"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feedback (message_id, rating, correction, comment)
                VALUES (?, ?, ?, ?)
            """, (message_id, rating, correction, comment))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_feedback(self, message_id: int) -> Optional[Feedback]:
        """Get feedback for a message"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, message_id, rating, correction, comment, created_at
                FROM feedback
                WHERE message_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (message_id,))
            row = cursor.fetchone()
            
            if row:
                return Feedback(
                    id=row[0],
                    message_id=row[1],
                    rating=row[2],
                    correction=row[3],
                    comment=row[4],
                    created_at=datetime.fromisoformat(row[5]) if row[5] else None,
                )
            return None
    
    # ========== Export Methods ==========
    
    def export_to_jsonl(
        self,
        output_path: Path,
        min_rating: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_tool_calls: bool = True
    ) -> int:
        """
        Export conversations to JSONL format for training.
        
        Args:
            output_path: Path to write JSONL file
            min_rating: Only include messages with feedback >= this rating
            start_date: Only include messages after this date
            end_date: Only include messages before this date
            include_tool_calls: Whether to include tool call information
            
        Returns:
            Number of conversations exported
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT DISTINCT c.id
                FROM conversations c
                JOIN messages m ON c.id = m.conversation_id
                LEFT JOIN feedback f ON m.id = f.message_id
                WHERE 1=1
            """
            params = []
            
            if min_rating is not None:
                query += " AND (f.rating IS NULL OR f.rating >= ?)"
                params.append(min_rating)
            
            if start_date:
                query += " AND c.started_at >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND c.started_at <= ?"
                params.append(end_date.isoformat())
            
            query += " ORDER BY c.started_at"
            
            cursor.execute(query, params)
            conversation_ids = [row[0] for row in cursor.fetchall()]
        
        # Export each conversation
        count = 0
        with open(output_path, 'w') as f:
            for conv_id in conversation_ids:
                messages = self.get_messages(conv_id)
                
                if not messages:
                    continue
                
                conversation_data = {
                    "conversation_id": conv_id,
                    "messages": []
                }
                
                for msg in messages:
                    msg_data = {
                        "role": msg.role,
                        "content": msg.content,
                    }
                    
                    if include_tool_calls and msg.role == "assistant":
                        tool_calls = self.get_tool_calls(msg.id)
                        if tool_calls:
                            msg_data["tool_calls"] = [
                                {
                                    "name": tc.tool_name,
                                    "arguments": tc.arguments,
                                    "result": tc.result,
                                }
                                for tc in tool_calls
                            ]
                    
                    conversation_data["messages"].append(msg_data)
                
                f.write(json.dumps(conversation_data) + "\n")
                count += 1
        
        return count
    
    # ========== Statistics ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """Get interaction statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM conversations")
            conversation_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tool_calls")
            tool_call_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM feedback")
            feedback_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT AVG(rating) FROM feedback WHERE rating != 0
            """)
            avg_rating = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM conversations WHERE ended_at IS NULL
            """)
            active_conversations = cursor.fetchone()[0]
            
            return {
                "conversation_count": conversation_count,
                "message_count": message_count,
                "tool_call_count": tool_call_count,
                "feedback_count": feedback_count,
                "average_rating": round(avg_rating, 2) if avg_rating else None,
                "active_conversations": active_conversations,
                "db_path": str(self.db_path),
            }
