# JARVIS Training Test Document

## Overview
JARVIS is an advanced AI assistant that provides intelligent automation and personal assistance.

## Key Features

### Voice Activation
JARVIS responds to the wake word "JARVIS" and can process natural language voice commands using Whisper for speech-to-text conversion.

### Real-time Information
The system provides access to:
- Live weather data from NOAA Weather Service
- Metro and train schedules from WMATA, Amtrak, VRE, and MARC
- Flight tracking via OpenSky Network
- Calendar integration with Apple Calendar
- Email management through Gmail and Outlook connectors

### Machine Learning
JARVIS uses Ollama for local LLM inference, supporting models like Llama 3.3. The system includes:
- Automatic interaction logging
- Document-to-QA conversion for training
- Custom model generation from learned patterns
- Persistent memory for user preferences

### Integration Capabilities
JARVIS integrates with multiple services:
- Transportation: WMATA Metro, Capital Bikeshare, Amtrak, VRE, MARC
- Weather: NOAA Weather Service (free, no API key required)
- Communication: iMessage, Gmail, Outlook
- Calendar: Apple Calendar via EventKit
- Maps: Apple Maps for directions

## Technical Architecture

### Core Components
1. **Orchestrator**: Main coordination layer that manages all components
2. **LLM Engine**: Abstract interface supporting multiple LLM providers
3. **Memory Store**: SQLite database for persistent user context
4. **Agent Coordinator**: Domain-specific agents for specialized tasks
5. **Interaction Store**: Logs all conversations for training

### Training Pipeline
The training system includes:
- Document processor supporting PDF, HTML, and text files
- Q&A generator using LLM to create training pairs
- Modelfile generator for custom Ollama models
- Export functionality for fine-tuning datasets

## Usage Examples

### Voice Commands
- "JARVIS, what's the weather today?"
- "JARVIS, when's the next Metro to Wiehle?"
- "JARVIS, check my calendar for tomorrow"

### CLI Commands
- `jarvis chat "your message"` - Send a text message
- `jarvis ui` - Launch the native Flet interface
- `jarvis train status` - View training statistics
- `jarvis train ingest path/to/docs` - Process documents for training

## Configuration
JARVIS uses a YAML configuration file (`config/models.yaml`) to manage:
- LLM model selection
- API keys for various services
- Agent enablement and settings
- Voice and TTS preferences
