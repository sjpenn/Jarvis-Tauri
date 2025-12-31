"""
System Stats Module
Retrieves system information (CPU, Memory, Disk, Network) and Location.
"""

import psutil
import requests
import socket
import platform
import asyncio
from typing import Dict, Any

class SystemStats:
    def __init__(self):
        self.last_net_io = psutil.net_io_counters()

    def get_cpu_info(self) -> float:
        """Returns overall CPU usage percentage"""
        return psutil.cpu_percent(interval=None)

    def get_memory_info(self) -> Dict[str, Any]:
        """Returns memory usage statistics"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total": mem.total,
            "available": mem.available,
            "percent": mem.percent,
            "used": mem.used,
            "swap_percent": swap.percent
        }

    def get_disk_info(self) -> Dict[str, Any]:
        """Returns disk usage statistics for the root partition"""
        disk = psutil.disk_usage('/')
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        }

    def get_battery_info(self) -> Dict[str, Any]:
        """Returns battery status if available"""
        battery = psutil.sensors_battery()
        if battery:
            return {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "secsleft": battery.secsleft
            }
        return {"percent": 100, "power_plugged": True, "secsleft": 0}

    def get_network_stats(self) -> Dict[str, float]:
        """Returns network bytes sent/received since last check"""
        curr_net_io = psutil.net_io_counters()
        
        # Calculate difference
        bytes_sent = curr_net_io.bytes_sent - self.last_net_io.bytes_sent
        bytes_recv = curr_net_io.bytes_recv - self.last_net_io.bytes_recv
        
        # Update last state
        self.last_net_io = curr_net_io
        
        return {
            "sent_kb": bytes_sent / 1024,
            "recv_kb": bytes_recv / 1024
        }

    async def get_location(self) -> str:
        """Get approximate location based on IP"""
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, requests.get, "https://ipinfo.io/json")
            data = response.json()
            city = data.get("city", "Unknown")
            region = data.get("region", "")
            return f"{city}, {region}"
        except Exception:
            return "Location Unavailable"

    async def get_all_stats(self) -> Dict[str, Any]:
        """Aggregate all stats for UI Consumption"""
        return {
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "disk": self.get_disk_info(),
            "battery": self.get_battery_info(),
            "network": self.get_network_stats(),
        }
