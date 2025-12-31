"""
JARVIS Action Queue - SQLite-backed queue for draft actions

Manages pending actions with full lifecycle:
pending → approved/rejected → executing → completed/failed
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jarvis.agents.agent_base import ActionStatus, DraftAction


class ActionQueue:
    """
    SQLite-backed persistent queue for draft actions.
    
    Features:
    - Persistent storage of pending actions
    - Status tracking through full lifecycle
    - Modification support (edit before approve)
    - Query by status, agent, or age
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path.home() / ".jarvis" / "actions.db")
        
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id TEXT PRIMARY KEY,
                    agent TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    params TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP,
                    executed_at TIMESTAMP,
                    result TEXT
                )
            """)
            
            # Indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_actions_status 
                ON actions(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_actions_agent 
                ON actions(agent)
            """)
            
            conn.commit()
    
    def add(self, action: DraftAction) -> str:
        """
        Add a new draft action to the queue.
        
        Returns:
            The action's ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO actions (id, agent, action_type, description, params, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                action.id,
                action.agent,
                action.action_type,
                action.description,
                json.dumps(action.params),
                action.status.value,
                action.created_at.isoformat(),
            ))
            conn.commit()
        return action.id
    
    def get(self, action_id: str) -> Optional[DraftAction]:
        """Get a specific action by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, agent, action_type, description, params, status,
                       created_at, modified_at, executed_at, result
                FROM actions WHERE id = ?
            """, (action_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_action(row)
            return None
    
    def get_pending(self) -> List[DraftAction]:
        """Get all pending actions"""
        return self.get_by_status(ActionStatus.PENDING)
    
    def get_by_status(self, status: ActionStatus) -> List[DraftAction]:
        """Get actions by status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, agent, action_type, description, params, status,
                       created_at, modified_at, executed_at, result
                FROM actions WHERE status = ?
                ORDER BY created_at DESC
            """, (status.value,))
            
            return [self._row_to_action(row) for row in cursor.fetchall()]
    
    def get_by_agent(self, agent: str) -> List[DraftAction]:
        """Get all actions from a specific agent"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, agent, action_type, description, params, status,
                       created_at, modified_at, executed_at, result
                FROM actions WHERE agent = ?
                ORDER BY created_at DESC
            """, (agent,))
            
            return [self._row_to_action(row) for row in cursor.fetchall()]
    
    def update_status(
        self, 
        action_id: str, 
        status: ActionStatus,
        result: Optional[str] = None
    ) -> bool:
        """
        Update an action's status.
        
        Returns:
            True if action was found and updated
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            executed_at = now if status in (ActionStatus.COMPLETED, ActionStatus.FAILED) else None
            
            cursor.execute("""
                UPDATE actions 
                SET status = ?, modified_at = ?, executed_at = COALESCE(?, executed_at), result = COALESCE(?, result)
                WHERE id = ?
            """, (status.value, now, executed_at, result, action_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def approve(self, action_id: str) -> bool:
        """Mark an action as approved"""
        return self.update_status(action_id, ActionStatus.APPROVED)
    
    def reject(self, action_id: str) -> bool:
        """Mark an action as rejected"""
        return self.update_status(action_id, ActionStatus.REJECTED)
    
    def complete(self, action_id: str, result: str) -> bool:
        """Mark an action as successfully completed"""
        return self.update_status(action_id, ActionStatus.COMPLETED, result)
    
    def fail(self, action_id: str, error: str) -> bool:
        """Mark an action as failed"""
        return self.update_status(action_id, ActionStatus.FAILED, error)
    
    def modify(self, action_id: str, updates: dict) -> bool:
        """
        Modify an action's parameters or description.
        
        Args:
            action_id: ID of action to modify
            updates: Dict with optional 'description' and/or 'params' keys
            
        Returns:
            True if action was found and updated
        """
        action = self.get(action_id)
        if not action:
            return False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            new_description = updates.get("description", action.description)
            new_params = {**action.params, **updates.get("params", {})}
            now = datetime.now().isoformat()
            
            cursor.execute("""
                UPDATE actions 
                SET description = ?, params = ?, status = ?, modified_at = ?
                WHERE id = ?
            """, (
                new_description,
                json.dumps(new_params),
                ActionStatus.MODIFIED.value,
                now,
                action_id,
            ))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def delete(self, action_id: str) -> bool:
        """Delete an action from the queue"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM actions WHERE id = ?", (action_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_completed(self) -> int:
        """Remove all completed/failed/rejected actions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM actions 
                WHERE status IN (?, ?, ?)
            """, (
                ActionStatus.COMPLETED.value,
                ActionStatus.FAILED.value,
                ActionStatus.REJECTED.value,
            ))
            conn.commit()
            return cursor.rowcount
    
    def get_summary(self) -> dict:
        """Get summary statistics of the queue"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM actions
                GROUP BY status
            """)
            
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                "pending": status_counts.get("pending", 0),
                "approved": status_counts.get("approved", 0),
                "rejected": status_counts.get("rejected", 0),
                "completed": status_counts.get("completed", 0),
                "failed": status_counts.get("failed", 0),
                "total": sum(status_counts.values()),
            }
    
    def _row_to_action(self, row: tuple) -> DraftAction:
        """Convert database row to DraftAction"""
        return DraftAction(
            id=row[0],
            agent=row[1],
            action_type=row[2],
            description=row[3],
            params=json.loads(row[4]),
            status=ActionStatus(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            modified_at=datetime.fromisoformat(row[7]) if row[7] else None,
            executed_at=datetime.fromisoformat(row[8]) if row[8] else None,
            result=row[9],
        )
