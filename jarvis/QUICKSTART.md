# JARVIS Quick Start Guide

## 🚀 Prerequisites

### 1. Ollama Service
Ollama must be running for JARVIS to work:

```bash
# Start Ollama (runs in background)
ollama serve

# Access: http://localhost:11434
```

### 2. Required Models

### 2. Required Models

**LLM - Two-Tier System:**
```bash
# Fast responses (~1s) for simple queries
ollama pull qwen2.5:3b  # ~1.9GB

# Deep thinking for complex reasoning
ollama pull qwen2.5:14b-instruct-q5_K_M  # ~10GB

# Fallback
ollama pull phi4:latest  # ~8GB
```

**JARVIS automatically routes:**
- Simple queries (greetings, calendar, tasks) → Fast model (3B)
- Complex queries (analysis, code, writing) → Deep model (14B)

**Vision:**
```bash
ollama pull llava:7b  # ~4.7GB
```

**Check installed models:**
```bash
ollama list
```

---

## 🎤 Commands

### Voice Mode (Wake Word)
```bash
cd ~/AgentSites/Jarvis/jarvis
python3 -m jarvis.cli start
```
Say "JARVIS" followed by your command.

### Native UI
```bash
cd ~/AgentSites/Jarvis/jarvis
python3 -m jarvis.cli ui
```

### Vision (Screen/Camera)
```bash
# Analyze screen
python3 -m jarvis.cli vision screen --prompt "What's on screen?"

# Analyze webcam
python3 -m jarvis.cli vision camera --prompt "Describe what you see"

# Analyze image
python3 -m jarvis.cli vision /path/to/image.jpg
```

### Text Chat
```bash
# Single command
python3 -m jarvis.cli chat "What's my schedule today?"

# Interactive mode
python3 -m jarvis.cli interactive
```

### Other Commands
```bash
python3 -m jarvis.cli status    # System info
python3 -m jarvis.cli tasks     # Task management
python3 -m jarvis.cli events    # Calendar
python3 -m jarvis.cli health    # Component health
```

---

## 🔧 Configuration

Edit `~/AgentSites/Jarvis/jarvis/config/models.yaml`:

```yaml
llm:
  primary_model: qwen2.5:14b-instruct-q5_K_M
  fallback_model: phi4:latest

vision:
  model: llava:7b
  
tts:
  provider: macos  # or elevenlabs
```

Environment variables in `~/AgentSites/Jarvis/jarvis/.env`:
```bash
PORCUPINE_ACCESS_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here  # optional
```

---

## 🩺 Troubleshooting

**Ollama not responding:**
```bash
# Check if running
curl http://localhost:11434/api/tags

# Restart
pkill ollama
ollama serve
```

**Models not found:**
```bash
ollama list
ollama pull qwen2.5:14b-instruct-q5_K_M
```

**UI errors:**
```bash
cd ~/AgentSites/Jarvis/jarvis
pip3 install -e .
```
