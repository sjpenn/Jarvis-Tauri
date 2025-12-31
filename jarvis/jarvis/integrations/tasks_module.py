"""Tasks Integration - Local SQLite task management"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional
import json

from .base import Integration
from jarvis.core.llm_engine import Tool


class TasksIntegration(Integration):
    """
    Local task management using SQLite.
    
    Features:
    - Create, complete, and list tasks
    - Priority levels
    - Due dates
    - Simple and fast
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".jarvis" / "tasks.db"
        self._connection: Optional[sqlite3.Connection] = None
    
    @property
    def name(self) -> str:
        return "tasks"
    
    @property
    def description(self) -> str:
        return "Manage personal tasks and to-do items"
    
    @property
    def tools(self) -> List[Tool]:
        return [
            Tool(
                name="add_task",
                description="Add a new task to the to-do list",
                parameters={
                    "title": {
                        "type": "string",
                        "description": "Task title/description",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority: low, medium, high (default: medium)",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date in YYYY-MM-DD format (optional)",
                    },
                }
            ),
            Tool(
                name="list_tasks",
                description="List all pending tasks",
                parameters={
                    "include_completed": {
                        "type": "boolean",
                        "description": "Include completed tasks (default: false)",
                    }
                }
            ),
            Tool(
                name="complete_task",
                description="Mark a task as completed",
                parameters={
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to complete",
                    }
                }
            ),
            Tool(
                name="delete_task",
                description="Delete a task",
                parameters={
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to delete",
                    }
                }
            ),
        ]
    
    async def setup(self) -> None:
        """Initialize the SQLite database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._connection = sqlite3.connect(str(self.db_path))
        self._connection.row_factory = sqlite3.Row
        
        self._connection.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                due_date TEXT,
                completed BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        ''')
        self._connection.commit()
    
    async def execute(self, tool_name: str, params: dict) -> Any:
        """Execute task tool"""
        if self._connection is None:
            await self.setup()
        
        if tool_name == "add_task":
            return await self.add_task(
                params.get("title", ""),
                params.get("priority", "medium"),
                params.get("due_date"),
            )
        elif tool_name == "list_tasks":
            return await self.list_tasks(params.get("include_completed", False))
        elif tool_name == "complete_task":
            return await self.complete_task(params.get("task_id"))
        elif tool_name == "delete_task":
            return await self.delete_task(params.get("task_id"))
        else:
            return f"Unknown task tool: {tool_name}"
    
    async def add_task(
        self,
        title: str,
        priority: str = "medium",
        due_date: Optional[str] = None,
    ) -> str:
        """Add a new task"""
        if not title:
            return "Error: Task title is required"
        
        cursor = self._connection.execute(
            "INSERT INTO tasks (title, priority, due_date) VALUES (?, ?, ?)",
            (title, priority, due_date)
        )
        self._connection.commit()
        
        return f"Task added with ID {cursor.lastrowid}: {title}"
    
    async def list_tasks(self, include_completed: bool = False) -> str:
        """List tasks"""
        if include_completed:
            rows = self._connection.execute(
                "SELECT * FROM tasks ORDER BY priority DESC, due_date ASC"
            ).fetchall()
        else:
            rows = self._connection.execute(
                "SELECT * FROM tasks WHERE completed = 0 ORDER BY priority DESC, due_date ASC"
            ).fetchall()
        
        if not rows:
            return "No tasks found."
        
        tasks = []
        for row in rows:
            status = "✓" if row["completed"] else "○"
            due = f" (due: {row['due_date']})" if row["due_date"] else ""
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(row["priority"], "")
            tasks.append(f"{status} [{row['id']}] {priority_emoji} {row['title']}{due}")
        
        return "\n".join(tasks)
    
    async def complete_task(self, task_id: int) -> str:
        """Mark a task as completed"""
        if task_id is None:
            return "Error: Task ID is required"
        
        cursor = self._connection.execute(
            "UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?",
            (datetime.now().isoformat(), task_id)
        )
        self._connection.commit()
        
        if cursor.rowcount == 0:
            return f"Task {task_id} not found"
        
        return f"Task {task_id} marked as completed"
    
    async def delete_task(self, task_id: int) -> str:
        """Delete a task"""
        if task_id is None:
            return "Error: Task ID is required"
        
        cursor = self._connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )
        self._connection.commit()
        
        if cursor.rowcount == 0:
            return f"Task {task_id} not found"
        
        return f"Task {task_id} deleted"
    
    async def health_check(self) -> bool:
        """Check if database is accessible"""
        try:
            if self._connection is None:
                await self.setup()
            self._connection.execute("SELECT 1")
            return True
        except Exception:
            return False
