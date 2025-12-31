"""
iMessage Integration
Reads local macOS Messages database to retrieve recent chats.
Requires Full Disk Access for the terminal/app running this code.
"""

import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class IMessageIntegration:
    def __init__(self, db_path: str = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path(os.path.expanduser("~/Library/Messages/chat.db"))

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
            # Timestamps in iMessage are usually Core Data timestamps (mac absolute time), 
            # starting from Jan 1 2001.
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
                
                # Convert Mac Absolute Time (ns or seconds) to readable
                # Usually in nanoseconds since 2001-01-01
                # If number is huge (>1e10), likely nanoseconds.
                # 2001-01-01 timestamp is 978307200 in Unix epoch
                
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
