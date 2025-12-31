"""Main Native UI Application using Flet"""

from __future__ import annotations

import asyncio
import flet as ft
from pathlib import Path
from typing import Optional

from jarvis.core.orchestrator import JARVISOrchestrator


class JarvisUI:
    def __init__(self, page: ft.Page, orchestrator: JARVISOrchestrator):
        self.page = page
        self.orchestrator = orchestrator
        self.orchestrator.conversation_history = []  # Start fresh
        
        # UI Components
        self.chat_list = ft.ListView(
            expand=True,
            spacing=10,
            padding=20,
            auto_scroll=True,
        )
        self.input_field = ft.TextField(
            hint_text="Ask JARVIS...",
            expand=True,
            border_radius=20,
            on_submit=self._handle_submit,
        )
        self.mic_button = ft.IconButton(
            icon="mic",
            icon_color="cyan",
            icon_size=30,
            on_click=self._toggle_listen,
        )
        self.send_button = ft.IconButton(
            icon="send_rounded",
            icon_color="cyan",
            icon_size=30,
            on_click=self._handle_submit,
        )
        
        self.status_text = ft.Text("Online", size=12, color="green")
        self.wave_visualizer = ft.ProgressBar(width=100, value=0, color="cyan", bgcolor="transparent")
        
        self._setup_ui()
    
    def _setup_ui(self):
        self.page.title = "JARVIS"
        self.page.theme_mode = "dark"
        self.page.padding = 0
        self.page.window_width = 450
        self.page.window_height = 800
        self.page.bgcolor = "#000000"
        
        # Header
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Text("JARVIS", size=20, weight="bold", color="cyan"),
                    ft.Container(expand=True),
                    self.wave_visualizer,
                    self.status_text,
                ],
                alignment="spaceBetween",
            ),
            padding=ft.padding.only(left=20, right=20, top=40, bottom=10),
            bgcolor="#1A1A1A",
        )
        
        # Input Area
        input_area = ft.Container(
            content=ft.Row(
                [
                    self.mic_button,
                    self.input_field,
                    self.send_button,
                ],
                alignment="spaceBetween",
            ),
            padding=20,
            bgcolor="#0D0D0D",
            border=ft.border.only(top=ft.BorderSide(1, "#333333")),
        )
        
        # Browser View (Hidden by default)
        self.browser_view = ft.Container(visible=False, expand=True, content=ft.Text("Browser Placeholder"))
        
        # Main Layout
        self.page.add(
            ft.Column(
                [
                    header,
                    ft.Container(
                        content=self.chat_list,
                        expand=True,
                        bgcolor="#000000",
                    ),
                    input_area,
                ],
                expand=True,
                spacing=0,
            )
        )
    
    async def _handle_submit(self, e):
        text = self.input_field.value
        if not text:
            return
        
        self.input_field.value = ""
        self.input_field.focus()
        self.page.update()
        
        await self._add_message(text, is_user=True)
        self.status_text.value = "Thinking..."
        self.status_text.color = "yellow"
        self.page.update()
        
        # Stream response with true token streaming
        await self._stream_response_from_llm(text)
        
        self.status_text.value = "Online"
        self.status_text.color = "green"
        self.page.update()
    
    async def _add_message(self, text: str, is_user: bool):
        align = "end" if is_user else "start"
        bg = "#0A4D4D" if is_user else "#1A1A1A"
        
        bubble = ft.Container(
            content=ft.Markdown(text, selectable=True),
            padding=15,
            border_radius=20,
            bgcolor=bg,
            margin=ft.margin.only(
                left=50 if is_user else 0,
                right=0 if is_user else 50,
                bottom=10,
            )
        )
        
        row = ft.Row([bubble], alignment=align)
        self.chat_list.controls.append(row)
        self.page.update()
    
    async def _stream_response_from_llm(self, text: str):
        """Stream response tokens directly from LLM for immediate feedback"""
        align = "start"
        bg = "#1A1A1A"
        
        md_control = ft.Markdown("", selectable=True)
        bubble = ft.Container(
            content=md_control,
            padding=15,
            border_radius=20,
            bgcolor=bg,
            margin=ft.margin.only(right=50, bottom=10)
        )
        
        row = ft.Row([bubble], alignment=align)
        self.chat_list.controls.append(row)
        self.page.update()
        
        # True token streaming from LLM
        full_response = ""
        try:
            async for token in self.orchestrator.stream_chat(text, speak=True):
                full_response += token
                md_control.value = full_response + "▋"
                self.page.update()
        except Exception as e:
            full_response = f"Error: {e}"
            md_control.value = full_response
            self.page.update()
            return
        
        # Remove cursor and finalize
        md_control.value = full_response
        self.page.update()

    def _toggle_listen(self, e):
        # TODO: Implement mic toggle with Visualizer
        pass


async def main_async(page: ft.Page, config_path: Optional[Path] = None):
    """Async entry point for Flet UI"""
    orchestrator = JARVISOrchestrator(config_path)
    # Initialize orchestrator before UI so models are ready
    await orchestrator.initialize()
    JarvisUI(page, orchestrator)


def run_ui(config_path: Optional[Path] = None):
    """Entry point for Flet UI"""
    async def main(page: ft.Page):
        await main_async(page, config_path)
        
    ft.app(target=main)
