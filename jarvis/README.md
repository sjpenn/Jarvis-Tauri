# JARVIS - Modular AI Personal Assistant

An advanced, modular AI assistant inspired by Tony Stark's JARVIS, built for macOS.

## Features

- **Modular Architecture**: Swap LLM, STT, TTS providers without code changes
- **Local-First**: Runs primarily on-device for privacy and speed
- **Voice Interface**: Wake word detection, speech recognition, and synthesis
- **Integrations**: Calendar, email, tasks, documents, web search
- **Tool Calling**: LLM can execute actions through registered tools

## Quick Start

```bash
cd ~/AgentSites/Jarvis/jarvis

# Install dependencies
pip install -e .

# (Optional) Pull Ollama models
ollama pull qwen2.5:14b-instruct-q5_K_M
ollama pull phi4:latest

# Run interactive chat
jarvis interactive

# Or send a single message
jarvis chat "What's my schedule today?"
```

## Commands

```bash
jarvis chat "message"      # Send a message
jarvis interactive         # Interactive chat mode
jarvis status              # System status (legacy)
jarvis events              # Upcoming calendar events
jarvis tasks               # List tasks
jarvis tasks --add "task"  # Add a task
jarvis say "text"          # Speak text
jarvis health              # Check component health
jarvis voices              # List available TTS voices
```

## Configuration

Edit `config/models.yaml` to customize:

```yaml
llm:
  provider: ollama
  primary_model: qwen2.5:14b-instruct-q5_K_M

tts:
  provider: macos  # or elevenlabs
  voice: Samantha

integrations:
  calendar_enabled: true
  tasks_enabled: true
```

## Environment Variables

Copy `.env.example` to `.env` and fill in API keys:

```bash
OLLAMA_HOST=http://localhost:11434
ELEVENLABS_API_KEY=      # Optional
PORCUPINE_ACCESS_KEY=    # Optional, for wake word
```

## Architecture

```
jarvis/
├── core/
│   ├── config.py          # Configuration management
│   ├── llm_engine.py      # Abstract LLM interface
│   ├── stt_engine.py      # Abstract STT interface
│   ├── tts_engine.py      # Abstract TTS interface
│   └── orchestrator.py    # Main coordinator
├── providers/
│   ├── llm/ollama_provider.py
│   ├── stt/whisper_provider.py
│   └── tts/macos_provider.py
├── integrations/
│   ├── calendar_module.py
│   └── tasks_module.py
└── cli.py                 # Command-line interface
```

## Adding New Providers

1. Implement the abstract base class (e.g., `LLMEngine`)
2. Add to `providers/<type>/__init__.py`
3. Update `orchestrator.py` to handle the new provider
4. Set in `config/models.yaml`

## License

MIT
