"""Main Native UI Application using Flet (HUD Edition)"""

from __future__ import annotations

import asyncio
import flet as ft
from pathlib import Path
from typing import Optional
import datetime

from jarvis.core.orchestrator import JARVISOrchestrator
from jarvis.core.system_stats import SystemStats
from jarvis.integrations.imessage import IMessageIntegration
from jarvis.ui.components import Orb, StatRing, HexButton

class JarvisUI:
    def __init__(self, page: ft.Page, orchestrator: JARVISOrchestrator):
        self.page = page
        self.orchestrator = orchestrator
        self.orchestrator.conversation_history = []
        
        self.system_stats = SystemStats()
        self.imessage = IMessageIntegration()
        
        # State
        self.is_monitoring = True
        
        # UI Refs
        self.orb = Orb()
        self.cpu_ring = StatRing("CPU", 0.0)
        self.mem_ring = StatRing("MEM", 0.0)
        self.batt_ring = StatRing("BATT", 0.0)
        
        self.chat_list = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
            auto_scroll=True,
        )
        self.input_field = ft.TextField(
            hint_text="Processing...",
            hint_style=ft.TextStyle(color="cyan900"),
            text_style=ft.TextStyle(color="cyan100"),
            expand=True,
            bgcolor="transparent",
            border_color="cyan700",
            border_radius=10,
            on_submit=self._handle_submit,
        )
        self.message_list = ft.ListView(expand=True, spacing=5)
        self.email_list = ft.ListView(expand=True, spacing=5)
        
        self._setup_ui()
        

        # Start background tasks
        self.page.run_task(self._update_stats_loop)
        self.page.run_task(self._update_stats_loop)
        self.page.run_task(self._update_messages_loop)
        self.page.run_task(self._update_emails_loop)
    
    def _get_time(self):
        return datetime.datetime.now().strftime("%H:%M")

    def _get_date(self):
        return datetime.datetime.now().strftime("%A, %b %d")

    def _setup_ui(self):
        self.page.title = "JARVIS HUD"
        self.page.theme_mode = "dark"
        self.page.padding = 10
        self.page.bgcolor = "#050A10" # Deep dark blue
        self.page.window_maximized = True
        

        # --- Left Panel: System Stats ---
        left_panel = ft.Container(
            content=ft.Column([
                # Clock Section
                ft.Container(
                    content=ft.Column([
                        ft.Text(self._get_time(), size=32, weight="bold", color="cyan"),
                        ft.Text(self._get_date(), size=14, color="cyan200"),
                    ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10,
                    border=ft.border.all(1, "cyan900"),
                    border_radius=10,
                    bgcolor=ft.colors.with_opacity(0.1, ft.colors.CYAN) if hasattr(ft, 'colors') else "#0D00FFFF", 
                    width=220
                ),
                ft.Divider(color="transparent", height=10),
                
                ft.Text("SYSTEM STATUS", color="cyan", weight="bold"),
                ft.Divider(color="cyan900"),
                ft.Row([self.cpu_ring, self.mem_ring, self.batt_ring], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                ft.Divider(color="transparent", height=20),
                ft.Text("ACTIVE AGENTS", color="cyan", weight="bold"),
                ft.Divider(color="cyan900"),
                self._build_agent_status("Transport", True),
                self._build_agent_status("Weather", True),
                self._build_agent_status("Calendar", True),
            ]),
            width=250,
            padding=15,
            border=ft.border.only(right=ft.BorderSide(1, "cyan900")),
        )
        
        # --- Center Panel: Orb & Chat ---
        center_panel = ft.Container(
            content=ft.Column([
                ft.Container(height=50), # Spacer
                ft.Container(content=self.orb, height=300), # Orb
                ft.Container(
                    content=self.chat_list,
                    expand=True,
                    border=ft.border.all(1, "cyan900"),
                    border_radius=10,
                    bgcolor=ft.colors.with_opacity(0.05, ft.colors.CYAN) if hasattr(ft, 'colors') else "#0D00FFFF",  # Use hex if needed but let's try hex with alpha
                    padding=10
                ),
                ft.Row([
                    self.input_field,
                    ft.IconButton(icon=ft.Icons.MIC, icon_color="cyan", on_click=self._toggle_mic),
                    ft.IconButton(icon=ft.Icons.SEND, icon_color="cyan", on_click=self._handle_submit),
                ])
            ]),
            expand=True,
            padding=20,
        )
        # Use simpler hex for bgcolor above to avoid issues
        center_panel.content.controls[2].bgcolor = "#0D00FFFF" # Very dark blue/cyan? Or just #0A1A1A

        # --- Right Panel: Comms & Info ---
        right_panel = ft.Container(
            content=ft.Column([
                ft.Text("COMMUNICATIONS", color="cyan", weight="bold"),
                ft.Divider(color="cyan900"),
                ft.Text("MESSAGES", size=10, color="cyan700"),
                ft.Container(
                    content=self.message_list,
                    expand=True,
                ),
                ft.Divider(color="cyan900"),
                ft.Text("EMAIL", size=10, color="cyan700"),
                ft.Container(
                    content=self.email_list,
                    expand=True,
                ),
                ft.Divider(color="cyan900"),
                ft.Text("LOCATION", color="cyan", weight="bold"),
                self._build_location_info(),
            ]),
            width=300,
            padding=15,
            border=ft.border.only(left=ft.BorderSide(1, "cyan900")),
        )
        
        # Main Layout
        self.page.add(
            ft.Row(
                [left_panel, center_panel, right_panel],
                expand=True,
                spacing=0
            )
        )
    
    def _build_agent_status(self, name: str, active: bool):
        return ft.Row([
            ft.Icon(ft.Icons.CIRCLE, size=10, color="green" if active else "red"),
            ft.Text(name, color="cyan100")
        ])
        
    def _build_location_info(self):
        # Placeholder, needs async init
        self.loc_text = ft.Text("Scanning...", color="cyan200", size=12)
        return ft.Container(content=self.loc_text, padding=5)

    async def _update_stats_loop(self):
        """Periodic System Stats Update"""
        while self.is_monitoring:
            try:
                cpu = self.system_stats.get_cpu_info()
                mem = self.system_stats.get_memory_info()
                batt = self.system_stats.get_battery_info()
                
                self.cpu_ring.update_value(cpu / 100.0)
                self.mem_ring.update_value(mem['percent'] / 100.0)
                self.batt_ring.update_value(batt['percent'] / 100.0)
                
                # Update location occasionally or just once
                if self.loc_text.value == "Scanning...":
                    loc = await self.system_stats.get_location()
                    self.loc_text.value = loc
                    self.loc_text.update()
                    
            except Exception as e:
                print(f"Stats error: {e}")
                
            await asyncio.sleep(2)

    async def _update_messages_loop(self):
        """Periodic iMessage Sync"""
        while self.is_monitoring:
            try:
                msgs = self.imessage.get_recent_messages(limit=8)
                self.message_list.controls.clear()
                
                for msg in msgs:
                    if "error" in msg:
                        self.message_list.controls.append(ft.Text(msg["error"], color="red", size=10))
                        break
                        
                    self.message_list.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(msg['sender'], weight="bold", size=11, color="cyan100"),
                                    ft.Text(msg['time'], size=10, color="cyan700")
                                ], alignment="spaceBetween"),
                                ft.Text(msg['text'], size=12, color="cyan50", no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)
                            ]),
                            padding=5,
                            border=ft.border.only(bottom=ft.BorderSide(1, "cyan900")) # used to be with opacity
                        )
                    )
                self.message_list.update()
            except Exception as e:
                print(f"Msg error: {e}")
            
            await asyncio.sleep(5) # Refresh every 5s

    async def _update_emails_loop(self):
        """Periodic Email Sync"""
        while self.is_monitoring:
            try:
                # Access Email Agent via coordinator
                agent = None
                if self.orchestrator.agent_coordinator:
                    agent = self.orchestrator.agent_coordinator.get_agent("email")
                
                if agent:
                    # Search recent emails
                    emails = await agent.search({"limit": 5, "accounts": "all"})
                    
                    self.email_list.controls.clear()
                    
                    if not emails:
                         self.email_list.controls.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([ft.Icon(ft.Icons.EMAIL, color="cyan", size=16), ft.Text("No new emails", color="cyan200", size=12)]),
                                    ft.Text("Inbox: Empty", color="cyan700", size=10)
                                ]),
                                padding=5
                            )
                         )
                    else:
                        for email in emails:
                            # Handle both object and dict (just in case)
                            subject = getattr(email, "subject", email.get("subject", "No Subject")) if hasattr(email, "subject") else email.get("subject", "No Subject")
                            sender = getattr(email, "sender", email.get("sender", "Unknown")) if hasattr(email, "sender") else email.get("sender", "Unknown")
                            body = getattr(email, "body", email.get("body", "")) if hasattr(email, "body") else email.get("body", "")
                            
                            self.email_list.controls.append(
                                ft.Container(
                                    content=ft.Column([
                                        ft.Row([
                                            ft.Text(sender[:15], weight="bold", size=11, color="cyan100", no_wrap=True),
                                            ft.Text(subject[:20], size=10, color="cyan200", no_wrap=True)
                                        ], alignment="spaceBetween"),
                                        ft.Text(body, size=10, color="cyan50", no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1)
                                    ]),
                                    padding=5,
                                    border=ft.border.only(bottom=ft.BorderSide(1, "cyan900"))
                                )
                            )
                    self.email_list.update()
                else:
                    # Agent not loaded
                    self.email_list.controls.clear()
                    self.email_list.controls.append(ft.Text("Email agent disabled", color="grey", size=10))
                    self.email_list.update()
                    
            except Exception as e:
                print(f"Email error: {e}")
            
            await asyncio.sleep(60) # Refresh every 60s


    async def _handle_submit(self, e):
        text = self.input_field.value
        if not text:
            return
        
        self.input_field.value = ""
        self.input_field.focus()
        self.input_field.update()
        
        await self._add_message(text, is_user=True)
        
        self.orb.set_state("THINKING")
        self.page.update()
        
        try:
            # Send to LLM
            # Note: We aren't doing the streaming token updates here for simplicity in this artifact, 
            # but we could add it back.
            response = await self.orchestrator.chat(text, speak=True)
            self.orb.set_state("SPEAKING") # Should ideally be triggered by TTS
            self.page.update()
            
            await self._add_message(response, is_user=False)
            
        finally:
            self.orb.set_state("IDLE")
            self.page.update()

    async def _add_message(self, text: str, is_user: bool):
        align = ft.CrossAxisAlignment.END if is_user else ft.CrossAxisAlignment.START
        bg = "#1A4D4D" if is_user else "#1A1A1A"
        
        bubble = ft.Container(
            content=ft.Markdown(text, selectable=True),
            padding=10,
            border_radius=10,
            bgcolor=bg,
            border=ft.border.all(1, "cyan800" if is_user else "grey800"),
            width=400
        )
        
        self.chat_list.controls.append(
            ft.Column([bubble], horizontal_alignment=align)
        )
        self.chat_list.update()

    async def _toggle_mic(self, e):
        """Toggle microphone recording"""
        if hasattr(self, 'is_recording') and self.is_recording:
            # Stop recording
            self.is_recording = False
            self.orb.set_state("THINKING")
            self.page.update()
            return

        # Start recording
        self.is_recording = True
        self.orb.set_state("LISTENING")
        self.page.update()
        
        # Run recording in background
        self.page.run_task(self._record_and_process)
        
    async def _record_and_process(self):
        """Record audio and send to orchestrator"""
        import pyaudio
        import wave
        import tempfile
        import os
        
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
        
        frames = []
        
        # Record while flag is true
        while getattr(self, 'is_recording', False):
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Recording error: {e}")
                break
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        if not frames:
            self.orb.set_state("IDLE")
            self.page.update()
            return

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
            wf = wave.open(tmp_wav.name, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            filename = tmp_wav.name
        
        # Process
        try:
            # Add user message placeholder
            await self._add_message("🎤 [Voice Command]", is_user=True)
            
            self.orb.set_state("THINKING")
            self.page.update()
            
            # Send to orchestrator
            response = await self.orchestrator.process_voice(Path(filename))
            
            self.orb.set_state("SPEAKING")
            self.page.update()
            
            await self._add_message(response, is_user=False)
            
        except Exception as e:
            await self._add_message(f"Error: {e}", is_user=False)
        finally:
            self.orb.set_state("IDLE")
            self.page.update()
            if os.path.exists(filename):
                os.unlink(filename)

async def main_async(page: ft.Page, config_path: Optional[Path] = None):
    orchestrator = JARVISOrchestrator(config_path)
    await orchestrator.initialize()
    JarvisUI(page, orchestrator)

def run_ui(config_path: Optional[Path] = None):
    async def main(page: ft.Page):
        await main_async(page, config_path)
    ft.app(target=main)
