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


# Training subcommands
train_app = typer.Typer(help="Training data and model customization commands")
app.add_typer(train_app, name="train")


@train_app.command("status")
def train_status():
    """Show training pipeline statistics"""
    from jarvis.core.interaction_store import InteractionStore
    from pathlib import Path
    
    interaction_store = InteractionStore()
    stats = interaction_store.get_stats()
    
    # Check for Q&A files
    training_dir = Path.home() / ".jarvis" / "training"
    qa_files = list(training_dir.glob("qa_*.jsonl")) if training_dir.exists() else []
    
    total_qa_pairs = 0
    for qa_file in qa_files:
        with open(qa_file, 'r') as f:
            total_qa_pairs += sum(1 for _ in f)
    
    lines = []
    lines.append("[bold cyan]Interaction Logs[/bold cyan]")
    lines.append(f"  Conversations: {stats['conversation_count']}")
    lines.append(f"  Messages: {stats['message_count']}")
    lines.append(f"  Tool Calls: {stats['tool_call_count']}")
    lines.append(f"  Feedback: {stats['feedback_count']}")
    if stats['average_rating']:
        lines.append(f"  Avg Rating: {stats['average_rating']:.1f}")
    
    lines.append("\n[bold cyan]Training Data[/bold cyan]")
    lines.append(f"  Document Q&A Files: {len(qa_files)}")
    lines.append(f"  Total Q&A Pairs: {total_qa_pairs}")
    
    lines.append(f"\n[dim]Interaction DB: {stats['db_path']}[/dim]")
    if training_dir.exists():
        lines.append(f"[dim]Training Data: {training_dir}[/dim]")
    
    console.print(Panel("\n".join(lines), title="📊 Training Status", border_style="cyan"))


@train_app.command("export")
def train_export(
    output: Path = typer.Option(None, "--output", "-o", help="Output JSONL file"),
    min_rating: int = typer.Option(None, "--min-rating", help="Minimum feedback rating"),
):
    """Export interaction logs to JSONL format"""
    from jarvis.core.interaction_store import InteractionStore
    
    interaction_store = InteractionStore()
    
    if output is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path.home() / ".jarvis" / "training" / f"interactions_{timestamp}.jsonl"
        output.parent.mkdir(parents=True, exist_ok=True)
    
    count = interaction_store.export_to_jsonl(
        output_path=output,
        min_rating=min_rating,
        include_tool_calls=False
    )
    
    console.print(f"[green]✓ Exported {count} conversations to {output}[/green]")


@train_app.command("ingest")
def train_ingest(
    path: Path = typer.Argument(..., help="Document file or directory to ingest"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Recursive directory search"),
    questions_per_chunk: int = typer.Option(3, "--questions", "-q", help="Q&A pairs per chunk"),
):
    """Ingest documents and generate training Q&A pairs"""
    
    async def _ingest():
        from jarvis.training.training_pipeline import TrainingPipeline
        jarvis = get_orchestrator()
        await jarvis.initialize()  # Initialize to set up LLM
        
        pipeline = TrainingPipeline(llm_engine=jarvis.llm)
        
        console.print(f"[cyan]Processing {path}...[/cyan]")
        
        if path.is_dir():
            docs = await pipeline.ingest_directory(
                directory_path=path,
                generate_qa=True,
                recursive=recursive
            )
            console.print(f"[green]✓ Processed {len(docs)} documents[/green]")
        else:
            doc = await pipeline.ingest_document(
                document_path=path,
                generate_qa=True,
                questions_per_chunk=questions_per_chunk
            )
            console.print(f"[green]✓ Processed {path.name}[/green]")
        
        # Show stats
        stats = pipeline.get_stats()
        console.print(f"[dim]Total Q&A pairs: {stats['total_qa_pairs']}[/dim]")
    
    asyncio.run(_ingest())


@train_app.command("prepare")
def train_prepare(
    output: str = typer.Option("training_dataset", "--output", "-o", help="Output dataset name"),
    min_rating: int = typer.Option(None, "--min-rating", help="Minimum interaction rating"),
    include_documents: bool = typer.Option(True, "--documents/--no-documents", help="Include document Q&A"),
):
    """Prepare complete training dataset from interactions and documents"""
    
    async def _prepare():
        from jarvis.training.training_pipeline import TrainingPipeline
        jarvis = get_orchestrator()
        await jarvis.initialize()  # Initialize to set up LLM
        
        pipeline = TrainingPipeline(llm_engine=jarvis.llm)
        
        console.print("[cyan]Preparing training dataset...[/cyan]")
        
        output_path = pipeline.prepare_training_dataset(
            min_rating=min_rating,
            include_documents=include_documents,
            output_name=output
        )
        
        # Count examples
        with open(output_path, 'r') as f:
            count = sum(1 for _ in f)
        
        console.print(f"[green]✓ Created dataset: {output_path}[/green]")
        console.print(f"[green]  Total examples: {count}[/green]")
    
    asyncio.run(_prepare())


@train_app.command("create-model")
def train_create_model(
    name: str = typer.Option("jarvis-enhanced", "--name", "-n", help="Name for custom model"),
    base: str = typer.Option("llama3.3", "--base", "-b", help="Base model to customize"),
    max_examples: int = typer.Option(5, "--examples", "-e", help="Max examples to include"),
    temperature: float = typer.Option(0.7, "--temperature", "-t", help="Model temperature"),
):
    """Create custom Ollama model from learned interactions"""
    from jarvis.training.modelfile_generator import ModelfileGenerator
    
    generator = ModelfileGenerator()
    
    console.print(f"[cyan]Generating Modelfile for '{name}'...[/cyan]")
    
    modelfile_path = generator.generate_modelfile(
        base_model=base,
        max_examples=max_examples,
        temperature=temperature
    )
    
    console.print(f"\n[green]✓ Modelfile created: {modelfile_path}[/green]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  1. Review the Modelfile: cat {modelfile_path}")
    console.print(f"  2. Create the model: ollama create {name} -f {modelfile_path}")
    console.print(f"  3. Update config to use '{name}' as your primary_model")
    console.print(f"  4. Test it: jarvis chat 'Hello JARVIS'")


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
