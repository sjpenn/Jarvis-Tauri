"""Calendar Integration - macOS Calendar + optional Google Calendar"""

from __future__ import annotations

import asyncio
import subprocess
from datetime import datetime, timedelta
from typing import Any, List

from .base import Integration
from jarvis.core.llm_engine import Tool


class CalendarIntegration(Integration):
    """
    Calendar integration using macOS Calendar via AppleScript.
    
    Features:
    - Get upcoming events
    - Search for specific events
    - Create new events
    
    Uses AppleScript for native macOS Calendar access.
    """
    
    @property
    def name(self) -> str:
        return "calendar"
    
    @property
    def description(self) -> str:
        return "Access and manage calendar events"
    
    @property
    def tools(self) -> List[Tool]:
        return [
            Tool(
                name="get_calendar_events",
                description="Get upcoming calendar events within a time range",
                parameters={
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours to look ahead (default: 24)",
                    }
                }
            ),
            Tool(
                name="search_calendar",
                description="Search calendar for events matching a query",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Search term to find in event titles",
                    }
                }
            ),
            Tool(
                name="get_next_event",
                description="Get the next upcoming calendar event",
                parameters={}
            ),
        ]
    
    async def execute(self, tool_name: str, params: dict) -> Any:
        """Execute calendar tool"""
        if tool_name == "get_calendar_events":
            hours = params.get("hours", 24)
            return await self.get_events(hours)
        elif tool_name == "search_calendar":
            query = params.get("query", "")
            return await self.search_events(query)
        elif tool_name == "get_next_event":
            return await self.get_next_event()
        else:
            return f"Unknown calendar tool: {tool_name}"
    
    async def get_events(self, hours: int = 24) -> str:
        """Get calendar events for the next N hours using AppleScript"""
        
        applescript = f'''
        tell application "Calendar"
            set nowDate to current date
            set endDate to nowDate + ({hours} * hours)
            set eventList to {{}}
            repeat with c in calendars
                try
                    set evs to (every event of c whose start date ≥ nowDate and start date ≤ endDate)
                    repeat with e in evs
                        set eventInfo to (summary of e & " at " & (start date of e as string))
                        set end of eventList to eventInfo
                    end repeat
                end try
            end repeat
            if (count of eventList) = 0 then
                return "No events in the next {hours} hours."
            else
                return eventList as string
            end if
        end tell
        '''
        
        return await self._run_applescript(applescript)
    
    async def get_next_event(self) -> str:
        """Get the very next calendar event"""
        
        applescript = '''
        tell application "Calendar"
            set nowDate to current date
            set endDate to nowDate + (7 * days)
            set nextEvent to missing value
            set earliestDate to endDate
            
            repeat with c in calendars
                try
                    set evs to (every event of c whose start date ≥ nowDate and start date ≤ endDate)
                    repeat with e in evs
                        if start date of e < earliestDate then
                            set earliestDate to start date of e
                            set nextEvent to e
                        end if
                    end repeat
                end try
            end repeat
            
            if nextEvent is missing value then
                return "No upcoming events found."
            else
                return (summary of nextEvent & " on " & (start date of nextEvent as string))
            end if
        end tell
        '''
        
        return await self._run_applescript(applescript)
    
    async def search_events(self, query: str) -> str:
        """Search for events matching a query"""
        
        applescript = f'''
        tell application "Calendar"
            set nowDate to current date
            set endDate to nowDate + (30 * days)
            set eventList to {{}}
            
            repeat with c in calendars
                try
                    set evs to (every event of c whose start date ≥ nowDate and start date ≤ endDate)
                    repeat with e in evs
                        if summary of e contains "{query}" then
                            set eventInfo to (summary of e & " on " & (start date of e as string))
                            set end of eventList to eventInfo
                        end if
                    end repeat
                end try
            end repeat
            
            if (count of eventList) = 0 then
                return "No events matching '{query}' found."
            else
                return eventList as string
            end if
        end tell
        '''
        
        return await self._run_applescript(applescript)
    
    async def _run_applescript(self, script: str) -> str:
        """Run AppleScript and return result"""
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/osascript", "-e", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            return f"Calendar error: {stderr.decode()}"
        
        return stdout.decode().strip()
    
    async def health_check(self) -> bool:
        """Check if Calendar is accessible"""
        try:
            result = await self._run_applescript('tell application "Calendar" to name of calendars')
            return "error" not in result.lower()
        except Exception:
            return False
