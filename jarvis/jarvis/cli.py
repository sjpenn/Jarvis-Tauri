"""JARVIS CLI - Command-line interface"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from jarvis.core.orchestrator import JARVISOrchestrator
from jarvis.core.config import load_config

app = typer.Typer(
    name="jarvis",
    help="JARVIS - Your Personal AI Assistant",
    add_completion=False,
)
console = Console()


def get_orchestrator(config: Optional[Path] = None) -> JARVISOrchestrator:
    """Create orchestrator with optional config path"""
    return JARVISOrchestrator(config_path=config)


@app.command()
def chat(
    message: str = typer.Argument(..., help="Message to send to JARVIS"),
    speak: bool = typer.Option(True, "--speak/--no-speak", help="Speak the response"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Send a message to JARVIS and get a response"""
    
    async def _chat():
        jarvis = get_orchestrator(config)
        response = await jarvis.chat(message, speak=speak)
        console.print(Panel(Markdown(response), title="JARVIS", border_style="cyan"))
    
    asyncio.run(_chat())


@app.command()
def interactive(
    speak: bool = typer.Option(True, "--speak/--no-speak", help="Speak responses"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Start interactive chat mode"""
    
    async def _interactive():
        jarvis = get_orchestrator(config)
        
        console.print(Panel(
            "[cyan]JARVIS Interactive Mode[/cyan]\n"
            "Type your message and press Enter. Type 'exit' or 'quit' to leave.",
            title="JARVIS",
            border_style="cyan",
        ))
        
        while True:
            try:
                user_input = console.input("[green]You:[/green] ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ("exit", "quit", "bye", "goodbye"):
                    if speak:
                        await jarvis.tts.speak("Goodbye, sir.")
                    console.print("[cyan]JARVIS:[/cyan] Goodbye!")
                    break
                
                response = await jarvis.chat(user_input, speak=speak)
                console.print(f"[cyan]JARVIS:[/cyan] {response}\n")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
    
    asyncio.run(_interactive())


@app.command()
def status():
    """Show system status (legacy command)"""
    import subprocess
    
    # Mimic legacy jarvis.sh status command
    uptime = subprocess.run(["uptime"], capture_output=True, text=True).stdout.strip()
    
    battery = subprocess.run(
        ["pmset", "-g", "batt"],
        capture_output=True, text=True
    ).stdout.strip()
    
    disk = subprocess.run(
        ["df", "-h", "/"],
        capture_output=True, text=True
    ).stdout.strip()
    
    console.print(Panel(
        f"[bold]Uptime:[/bold]\n{uptime}\n\n"
        f"[bold]Battery:[/bold]\n{battery}\n\n"
        f"[bold]Disk:[/bold]\n{disk}",
        title="System Status",
        border_style="cyan",
    ))


@app.command()
def events(
    hours: int = typer.Option(24, "--hours", "-h", help="Hours to look ahead"),
):
    """List upcoming calendar events"""
    
    async def _events():
        from jarvis.integrations import CalendarIntegration
        cal = CalendarIntegration()
        result = await cal.get_events(hours)
        console.print(Panel(result, title=f"Events (next {hours}h)", border_style="cyan"))
    
    asyncio.run(_events())


@app.command()
def tasks(
    add: Optional[str] = typer.Option(None, "--add", "-a", help="Add a new task"),
    complete: Optional[int] = typer.Option(None, "--complete", "-c", help="Complete task by ID"),
    list_all: bool = typer.Option(False, "--all", help="Include completed tasks"),
):
    """Manage tasks"""
    
    async def _tasks():
        from jarvis.integrations import TasksIntegration
        task_mgr = TasksIntegration()
        await task_mgr.setup()
        
        if add:
            result = await task_mgr.add_task(add)
            console.print(f"[green]{result}[/green]")
        elif complete is not None:
            result = await task_mgr.complete_task(complete)
            console.print(f"[green]{result}[/green]")
        else:
            result = await task_mgr.list_tasks(include_completed=list_all)
            console.print(Panel(result, title="Tasks", border_style="cyan"))
    
    asyncio.run(_tasks())


@app.command()
def say(
    text: str = typer.Argument(..., help="Text to speak"),
    voice: str = typer.Option("Samantha", "--voice", "-v", help="Voice to use"),
):
    """Speak text using TTS (legacy command)"""
    
    async def _say():
        from jarvis.providers.tts import MacOSProvider
        tts = MacOSProvider(voice=voice)
        await tts.speak(text)
        await tts.show_notification(text)
    
    asyncio.run(_say())


@app.command()
def health():
    """Check health of all JARVIS components"""
    
    async def _health():
        jarvis = get_orchestrator()
        status = await jarvis.health_check()
        
        # Format status
        lines = []
        lines.append(f"LLM: {'✓' if status['llm'] else '✗'}")
        lines.append(f"TTS: {'✓' if status['tts'] else '✗'}")
        lines.append(f"STT: {'✓' if status['stt'] else '✗'}")
        
        for name, ok in status.get("integrations", {}).items():
            lines.append(f"{name.capitalize()}: {'✓' if ok else '✗'}")
        
        console.print(Panel("\n".join(lines), title="Health Check", border_style="cyan"))
    
    asyncio.run(_health())


@app.command()
def voices():
    """List available TTS voices"""
    
    async def _voices():
        from jarvis.providers.tts import MacOSProvider
        tts = MacOSProvider()
        voice_list = tts.get_available_voices()
        
        console.print(Panel(
            "\n".join(voice_list[:20]),  # Show first 20
            title="Available Voices",
            border_style="cyan",
        ))
    
    asyncio.run(_voices())


# Memory subcommands
memory_app = typer.Typer(help="Memory management commands")
app.add_typer(memory_app, name="memory")


@memory_app.command("show")
def memory_show():
    """Display stored user profile and preferences"""
    from jarvis.core.memory_store import MemoryStore
    
    memory = MemoryStore()
    stats = memory.get_stats()
    profile = memory.get_user_profile()
    preferences = memory.get_all_preferences()
    
    lines = []
    
    # User profile
    lines.append("[bold cyan]User Profile[/bold cyan]")
    lines.append(f"  Name: {profile.name or '[not set]'}")
    if profile.facts:
        lines.append("  Facts:")
        for fact in profile.facts:
            lines.append(f"    • {fact}")
    
    # Preferences
    if preferences:
        lines.append("\n[bold cyan]Preferences[/bold cyan]")
        for pref in preferences:
            lines.append(f"  {pref.category}/{pref.key}: {pref.value}")
    
    # Stats
    lines.append(f"\n[dim]Memories: {stats['memory_count']} | DB: {stats['db_path']}[/dim]")
    
    console.print(Panel("\n".join(lines), title="🧠 JARVIS Memory", border_style="cyan"))


@memory_app.command("clear")
def memory_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clear all stored memories (with confirmation)"""
    from jarvis.core.memory_store import MemoryStore
    
    if not force:
        confirm = typer.confirm("Are you sure you want to clear all JARVIS memories?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    memory = MemoryStore()
    memory.clear_all()
    console.print("[green]✓ All memories cleared[/green]")


@memory_app.command("set-name")
def memory_set_name(
    name: str = typer.Argument(..., help="Your name"),
):
    """Set your name directly"""
    from jarvis.core.memory_store import MemoryStore
    
    memory = MemoryStore()
    memory.set_user_name(name)
    console.print(f"[green]✓ Name set to: {name}[/green]")


@app.command()
def vision(
    mode: str = typer.Argument("screen", help="Mode: screen, camera, or path to image"),
    prompt: str = typer.Option("Describe what you see.", "--prompt", "-p", help="Question about the image"),
):
    """
    👀 Vision capabilities (Screen/Camera analysis)
    
    Examples:
        jarvis vision screen --prompt "Summarize this article"
        jarvis vision camera --prompt "What am I holding?"
        jarvis vision /path/to/image.jpg
    """
    
    async def _vision():
        jarvis = get_orchestrator()
        
        console.print(f"[cyan]Analyzing {mode}...[/cyan]")
        
        if mode == "screen":
            response = await jarvis.process_screen(prompt)
        elif mode == "camera":
            response = await jarvis.process_camera(prompt)
        else:
            # Assume path
            response = await jarvis.process_image(Path(mode), prompt)
            
        console.print(Panel(response, title="Vision Analysis", border_style="green"))
    
    try:
        asyncio.run(_vision())
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def ui(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """
    🖥️ Launch Native UI
    
    Starts the Flet-based responsive interface.
    """
    from jarvis.ui import run_ui
    run_ui(config)


@app.command()
def listen(
    porcupine_key: Optional[str] = typer.Option(
        None, "--key", "-k", 
        envvar="PORCUPINE_ACCESS_KEY",
        help="Porcupine access key (or set PORCUPINE_ACCESS_KEY env var)"
    ),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """
    Start voice-activated mode.
    
    Say 'JARVIS' followed by your command.
    
    Examples:
        'JARVIS, what's my schedule today?'
        'JARVIS, add a task to review the proposal'
        'JARVIS, what time is it?'
    
    Get a free Porcupine key at: https://console.picovoice.ai/
    Without a key, falls back to Whisper-based detection (slower).
    """
    
    console.print(Panel(
        "[cyan]JARVIS Voice Mode[/cyan]\n\n"
        "Say [bold]'JARVIS'[/bold] followed by your command.\n"
        "Press Ctrl+C to exit.",
        title="🎤 Voice Activation",
        border_style="cyan",
    ))
    
    async def _listen():
        from jarvis.voice.voice_loop import VoiceLoop
        
        jarvis = get_orchestrator(config)
        loop = VoiceLoop(jarvis, porcupine_key=porcupine_key)
        
        try:
            await loop.start()
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
            await loop.stop()
    
    try:
        asyncio.run(_listen())
    except KeyboardInterrupt:
        console.print("\n[cyan]JARVIS:[/cyan] Goodbye!")


@app.command()
def start(
    porcupine_key: Optional[str] = typer.Option(
        None, "--key", "-k", 
        envvar="PORCUPINE_ACCESS_KEY",
        help="Porcupine access key (or set PORCUPINE_ACCESS_KEY env var)"
    ),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """
    🚀 Start JARVIS - Your AI Assistant
    
    Launches JARVIS in voice-activated mode.
    Say 'JARVIS' followed by your command.
    
    Examples:
        jarvis start
        jarvis start --key YOUR_PORCUPINE_KEY
    """
    
    console.print(Panel(
        "[bold cyan]J.A.R.V.I.S.[/bold cyan]\n"
        "[dim]Just A Rather Very Intelligent System[/dim]\n\n"
        "🎤 Say [bold]'JARVIS'[/bold] to activate\n"
        "📝 Then speak your command\n\n"
        "[dim]Press Ctrl+C to shutdown[/dim]",
        title="✨ JARVIS Online",
        border_style="cyan",
        padding=(1, 2),
    ))
    
    async def _start():
        from jarvis.voice.voice_loop import VoiceLoop
        
        jarvis = get_orchestrator(config)
        loop = VoiceLoop(jarvis, porcupine_key=porcupine_key)
        
        try:
            await loop.start()
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
            await loop.stop()
    
    try:
        asyncio.run(_start())
    except KeyboardInterrupt:
        console.print("\n[cyan]JARVIS:[/cyan] Goodbye, sir.")


def main():
    """Entry point"""
    app()


if __name__ == "__main__":
    main()
