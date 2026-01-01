# JARVIS - Tauri + Svelte Edition

A personal AI assistant built with Tauri v2 (Rust) + SvelteKit, featuring local Phi-3 Mini inference and a stunning "Blueprint" UI.

## Features

- 🎨 **Blueprint Aesthetic**: Dark mode with cyan glow effects and animated HUD
- 🧠 **Local AI**: Phi-3 Mini inference via llama-cpp-2 (no cloud required)
- 💾 **Semantic Memory**: SQLite-based user profile, preferences, and RAG context
- 📊 **Real-time Monitoring**: CPU/RAM graphs updated every 500ms via Tauri events
- 🌤️ **External APIs**: Weather.gov, WMATA Metro, OpenSky flight tracking
- 🔒 **Privacy-First**: All data stays local on your machine

## Architecture

### Hybrid Data Strategy

1. **High-Frequency Sensor Data** → Tauri Events (NOT vector store)
   - CPU/RAM usage
   - System stats
   
2. **User Preferences & Memory** → SQLite with RAG
   - User profile
   - Conversation history
   - Learned preferences

3. **External APIs** → On-demand Tauri commands
   - Weather
   - Transit times
   - Flight tracking

## Setup

### Prerequisites

- **Rust**: Install from [rustup.rs](https://rustup.rs)
- **Node.js**: v18+ recommended
- **Phi-3 Mini GGUF**: Download from [Hugging Face](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)

### Installation

```bash
# Install dependencies
npm install

# Run in development mode
npm run tauri dev

# Build for production
npm run tauri build
```

### Configuring Phi-3

1. Download a Phi-3 Mini GGUF model (recommended: `Phi-3-mini-4k-instruct-q4.gguf`)
2. In the JARVIS UI, go to the right panel → "PHI-3 CONFIGURATION"
3. Click "Browse" and select your downloaded `.gguf` file
4. Click "Load Model"

## Project Structure

```
jarvis-app/
├── src-tauri/          # Rust backend
│   └── src/
│       ├── lib.rs      # Main entry point
│       ├── sensor.rs   # System stats (events)
│       ├── memory.rs   # SQLite store
│       ├── external.rs # HTTP API clients
│       └── llm.rs      # Phi-3 inference + RAG
├── src/                # Svelte frontend
│   ├── lib/
│   │   ├── components/ # UI components
│   │   └── stores/     # State management
│   └── routes/
│       └── +page.svelte # Main dashboard
└── package.json
```

## Components

- **HudCore**: Animated central status element with rotating rings
- **LiveGraph**: Real-time CPU/RAM canvas graphs
- **LogTerminal**: AI thought process display
- **MemoryIndicator**: Glows when vector store is accessed
- **ChatInterface**: Streaming chat with memory context badges
- **ModelSettings**: Configure Phi-3 model path

## Development

### Rust Backend

```bash
# Check compilation
cargo check --manifest-path src-tauri/Cargo.toml

# Run tests
cargo test --manifest-path src-tauri/Cargo.toml
```

### Frontend

```bash
# Type checking
npm run check

# Build
npm run build
```

## Next Steps

- [ ] Integrate full llama-cpp-2 inference in `llm.rs`
- [ ] Add SQLite-VSS for true vector similarity search
- [ ] Implement embedding generation for RAG
- [ ] Add more external API integrations (hotels, flights)
- [ ] Create mobile-optimized layout

## License

MIT

## Credits

Built with:
- [Tauri](https://tauri.app) - Rust-powered desktop framework
- [SvelteKit](https://kit.svelte.dev) - Web framework
- [llama-cpp-2](https://crates.io/crates/llama-cpp-2) - Local LLM inference
- [Phi-3 Mini](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf) - Microsoft's compact LLM
