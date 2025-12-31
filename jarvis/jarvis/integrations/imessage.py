"""
iMessage Integration
Reads local macOS Messages database to retrieve recent chats.
Sends messages using AppleScript.
Requires Full Disk Access for the terminal/app running this code.
"""

import sqlite3
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from jarvis.core.llm_engine import Tool
from jarvis.integrations.base import Integration

class IMessageIntegration(Integration):
    def __init__(self, db_path: str = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(os.path.expanduser("~/Library/Messages/chat.db"))

    @property
    def name(self) -> str:
        return "imessage"

    @property
    def description(self) -> str:
        return "Read and send iMessages"

    @property
    def tools(self) -> List[Tool]:
        return [
            Tool(
                name="get_recent_messages",
                description="Get recent iMessages",
                parameters={
                    "limit": {
                        "type": "integer",
                        "description": "Number of messages to retrieve (default 10)"
                    }
                }
            ),
            Tool(
                name="send_message",
                description="Send an iMessage to a recipient",
                parameters={
                    "recipient": {
                        "type": "string",
                        "description": "Phone number or email address of the recipient"
                    },
                    "message": {
                        "type": "string",
                        "description": "The message content to send"
                    }
                }
            )
        ]

    def check_permissions(self) -> bool:
        """Check if we can read the database"""
        return self.db_path.exists() and os.access(self.db_path, os.R_OK)

    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent messages with sender info"""
        if not self.check_permissions():
            return [{"error": "No permission to access Messages DB or DB not found."}]

        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()

            # Query to get messages joined with handles (senders)
            query = """
                SELECT 
                    message.text,
                    handle.id as sender,
                    message.date,
                    message.is_from_me
                FROM message 
                LEFT JOIN handle ON message.handle_id = handle.ROWID
                WHERE message.text IS NOT NULL
                ORDER BY message.date DESC
                LIMIT ?
            """
            
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                text, sender, date_val, is_from_me = row
                
                try:
                    # Assuming nanoseconds based on recent macOS versions
                    mac_epoch = 978307200
                    seconds_offset = date_val / 1_000_000_000
                    unix_timestamp = mac_epoch + seconds_offset
                    dt = datetime.fromtimestamp(unix_timestamp)
                    time_str = dt.strftime("%I:%M %p")
                except:
                    time_str = "Unknown"

                messages.append({
                    "text": text,
                    "sender": "Me" if is_from_me else (sender or "Unknown"),
                    "time": time_str,
                    "is_from_me": bool(is_from_me)
                })
            
            conn.close()
            return messages

        except sqlite3.Error as e:
            return [{"error": f"Database error: {e}"}]
        except Exception as e:
            return [{"error": f"Error reading messages: {e}"}]

    async def execute(self, tool_name: str, params: dict) -> Any:
        """Execute iMessage tool"""
        if tool_name == "get_recent_messages":
            limit = params.get("limit", 10)
            return self.get_recent_messages(limit)
        elif tool_name == "send_message":
            recipient = params.get("recipient")
            message = params.get("message")
            return await self.send_message(recipient, message)
        return f"Unknown tool: {tool_name}"

    async def send_message(self, recipient: str, message: str) -> str:
        """Send an iMessage using AppleScript"""
        script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{recipient}" of targetService
            send "{message}" to targetBuddy
        end tell
        '''
        
        try:
            result = await self._run_applescript(script)
            return f"Message sent to {recipient}"
        except Exception as e:
            return f"Failed to send message: {e}"

    async def _run_applescript(self, script: str) -> str:
        """Run AppleScript and return result"""
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise Exception(stderr.decode())
        
        return stdout.decode().strip()

    async def health_check(self) -> bool:
        return self.check_permissions()
