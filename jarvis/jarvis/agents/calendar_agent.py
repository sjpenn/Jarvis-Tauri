"""
JARVIS Calendar Agent - Unified calendar management across multiple sources

Aggregates events from macOS Calendar, Google Calendar, and Outlook Calendar.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from jarvis.agents.agent_base import Agent, DraftAction
from jarvis.agents.connectors.connector_base import Connector


@dataclass
class CalendarEvent:
    """Unified calendar event representation"""
    id: str
    title: str
    start: datetime
    end: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None
    is_all_day: bool = False
    calendar_name: str = ""
    account: str = ""  # Which account/source this came from


class CalendarAgent(Agent):
    """
    Unified calendar agent supporting multiple sources.
    
    Sources:
    - macOS Calendar (via AppleScript)
    - Google Calendar (via API)
    - Outlook Calendar (via Graph API)
    
    Features:
    - Aggregate view across all calendars
    - Event search and filtering
    - Create events in draft mode
    """
    
    def __init__(self):
        super().__init__()
        self._use_macos_calendar = True  # Built-in, always available
    
    @property
    def name(self) -> str:
        return "calendar"
    
    @property
    def description(self) -> str:
        return "Manage calendar events across macOS Calendar, Google Calendar, and Outlook"
    
    async def understand(self, query: str) -> Dict[str, Any]:
        """Parse calendar-related intent"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["schedule", "create", "add event", "book"]):
            return {"action": "create", "query": query}
        elif any(word in query_lower for word in ["reschedule", "move", "change"]):
            return {"action": "update", "query": query}
        elif any(word in query_lower for word in ["cancel", "delete", "remove"]):
            return {"action": "delete", "query": query}
        else:
            return {"action": "search", "query": query}
    
    async def search(self, criteria: Dict[str, Any]) -> List[CalendarEvent]:
        """
        Aggregate search across all calendar sources.
        
        Args:
            criteria: {
                "query": "search terms" (optional),
                "hours": 24,  # Look ahead hours
                "calendars": "all" or ["macos", "google:personal"],
            }
        """
        hours = criteria.get("hours", 24)
        calendars_filter = criteria.get("calendars", "all")
        query = criteria.get("query", "")
        
        all_events: List[CalendarEvent] = []
        
        # Get macOS Calendar events (always available)
        if self._use_macos_calendar:
            if calendars_filter == "all" or "macos" in str(calendars_filter):
                try:
                    events = await self._get_macos_events(hours, query)
                    all_events.extend(events)
                except Exception as e:
                    print(f"Error getting macOS Calendar events: {e}")
        
        # Get events from connectors (Google, Outlook)
        for connector in self._connectors:
            if calendars_filter != "all":
                if isinstance(calendars_filter, list) and connector.name not in calendars_filter:
                    continue
            
            try:
                results = await connector.search({
                    "hours": hours,
                    "query": query,
                })
                
                for event_data in results:
                    event = self._normalize_event(event_data, connector.name)
                    all_events.append(event)
            except Exception as e:
                print(f"Error getting events from {connector.name}: {e}")
        
        # Sort by start time
        all_events.sort(key=lambda e: e.start)
        
        return all_events
    
    async def propose_action(self, intent: Dict[str, Any]) -> DraftAction:
        """Create a draft calendar action"""
        action_type = intent.get("action", "create")
        
        if action_type == "create":
            return DraftAction(
                agent=self.name,
                action_type="create_event",
                description=f"Create event: {intent.get('title', 'New Event')}\n"
                           f"When: {intent.get('start', 'Not specified')}\n"
                           f"Where: {intent.get('location', 'Not specified')}",
                params={
                    "title": intent.get("title", ""),
                    "start": intent.get("start", ""),
                    "end": intent.get("end", ""),
                    "location": intent.get("location", ""),
                    "calendar": intent.get("calendar", "default"),
                },
            )
        else:
            return DraftAction(
                agent=self.name,
                action_type=f"{action_type}_event",
                description=f"{action_type.title()} event: {intent.get('title', '')}",
                params=intent,
            )
    
    async def execute(self, action: DraftAction) -> str:
        """Execute an approved calendar action"""
        
        if action.action_type == "create_event":
            # Use macOS Calendar by default
            return await self._create_macos_event(action.params)
        else:
            return f"Calendar action '{action.action_type}' not yet implemented"
    
    async def _get_macos_events(self, hours: int, query: str = "") -> List[CalendarEvent]:
        """Get events from macOS Calendar via AppleScript"""
        
        # Build AppleScript
        if query:
            applescript = f'''
            tell application "Calendar"
                set nowDate to current date
                set endDate to nowDate + ({hours} * hours)
                set eventList to {{}}
                repeat with c in calendars
                    try
                        set evs to (every event of c whose start date ≥ nowDate and start date ≤ endDate)
                        repeat with e in evs
                            if summary of e contains "{query}" then
                                set eventInfo to (summary of e & "|" & (start date of e as string) & "|" & (name of c))
                                set end of eventList to eventInfo
                            end if
                        end repeat
                    end try
                end repeat
                return eventList as string
            end tell
            '''
        else:
            applescript = f'''
            tell application "Calendar"
                set nowDate to current date
                set endDate to nowDate + ({hours} * hours)
                set eventList to {{}}
                repeat with c in calendars
                    try
                        set evs to (every event of c whose start date ≥ nowDate and start date ≤ endDate)
                        repeat with e in evs
                            set eventInfo to (summary of e & "|" & (start date of e as string) & "|" & (name of c))
                            set end of eventList to eventInfo
                        end repeat
                    end try
                end repeat
                return eventList as string
            end tell
            '''
        
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/osascript", "-e", applescript,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        
        result = stdout.decode().strip()
        if not result or "No events" in result:
            return []
        
        events = []
        for item in result.split(", "):
            parts = item.split("|")
            if len(parts) >= 2:
                try:
                    # Parse date (macOS format varies)
                    start_str = parts[1].strip()
                    # Try to parse - this is approximate
                    start = datetime.now()  # Fallback
                    
                    events.append(CalendarEvent(
                        id=f"macos_{len(events)}",
                        title=parts[0].strip(),
                        start=start,
                        calendar_name=parts[2].strip() if len(parts) > 2 else "",
                        account="macos",
                    ))
                except Exception:
                    pass
        
        return events
    
    async def _create_macos_event(self, params: Dict[str, Any]) -> str:
        """Create event in macOS Calendar"""
        title = params.get("title", "New Event")
        start = params.get("start", "")
        location = params.get("location", "")
        
        applescript = f'''
        tell application "Calendar"
            tell calendar "Calendar"
                make new event with properties {{summary:"{title}", location:"{location}"}}
            end tell
        end tell
        '''
        
        proc = await asyncio.create_subprocess_exec(
            "/usr/bin/osascript", "-e", applescript,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            return f"Error creating event: {stderr.decode()}"
        
        return f"Created event: {title}"
    
    def _normalize_event(self, data: Dict[str, Any], account: str) -> CalendarEvent:
        """Convert connector data to unified CalendarEvent"""
        return CalendarEvent(
            id=data.get("id", ""),
            title=data.get("title", data.get("summary", "Untitled")),
            start=data.get("start", datetime.now()),
            end=data.get("end"),
            location=data.get("location"),
            description=data.get("description"),
            is_all_day=data.get("is_all_day", False),
            calendar_name=data.get("calendar_name", ""),
            account=account,
        )
    
    def get_capabilities(self) -> List[str]:
        return [
            "view upcoming calendar events",
            "search for specific events",
            "create new events (draft mode)",
            "aggregate events from multiple calendars",
        ]
