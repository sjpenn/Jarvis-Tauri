//! LLM Chat module with Phi-3 Mini integration
//!
//! Provides chat functionality with Retrieval-Augmented Generation (RAG).
//! Uses llama-cpp-2 for local Phi-3 inference.

use serde::{Deserialize, Serialize};
use crate::memory::MemoryStore;
use std::sync::Mutex;
use std::path::PathBuf;

/// Chat message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String, // "user", "assistant", "system"
    pub content: String,
}

/// Chat response with metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatResponse {
    pub message: String,
    pub memory_context_used: bool,
    pub memories_retrieved: usize,
}

/// Log entry for AI thought process
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThoughtLog {
    pub step: String,
    pub detail: String,
    pub timestamp: i64,
}

/// LLM Engine state
pub struct LlmEngine {
    model_path: Option<PathBuf>,
    // We'll add llama-cpp-2 model here when initialized
    initialized: bool,
}

impl LlmEngine {
    pub fn new() -> Self {
        Self {
            model_path: None,
            initialized: false,
        }
    }

    /// Initialize with a GGUF model file
    pub fn init(&mut self, model_path: PathBuf) -> Result<(), String> {
        if !model_path.exists() {
            return Err(format!("Model file not found: {:?}", model_path));
        }
        
        self.model_path = Some(model_path);
        self.initialized = true;
        
        log::info!("LLM engine initialized with model: {:?}", self.model_path);
        Ok(())
    }

    /// Generate a response (placeholder - will integrate llama-cpp-2)
    pub fn generate(&self, prompt: &str, system: &str) -> Result<String, String> {
        if !self.initialized {
            return Ok(self.fallback_response(prompt));
        }

        // TODO: Integrate llama-cpp-2 inference here
        // For now, return a demo response
        Ok(format!(
            "I received your message: \"{}\"\n\n\
            I'm JARVIS, powered by Phi-3 Mini. Local inference will be integrated here.\n\n\
            System context: {}",
            prompt.chars().take(100).collect::<String>(),
            system.chars().take(50).collect::<String>()
        ))
    }

    fn fallback_response(&self, prompt: &str) -> String {
        format!(
            "JARVIS is ready. (Model not loaded - please configure Phi-3 Mini GGUF path)\n\
            Your message: {}",
            prompt.chars().take(100).collect::<String>()
        )
    }
}

impl Default for LlmEngine {
    fn default() -> Self {
        Self::new()
    }
}

/// Global LLM engine instance
static LLM_ENGINE: Mutex<Option<LlmEngine>> = Mutex::new(None);

/// Initialize the LLM engine
pub fn init_llm_engine(model_path: Option<PathBuf>) -> Result<(), String> {
    let mut engine = LlmEngine::new();
    
    if let Some(path) = model_path {
        engine.init(path)?;
    }
    
    *LLM_ENGINE.lock().unwrap() = Some(engine);
    Ok(())
}

/// Chat with RAG context retrieval
#[tauri::command]
pub async fn chat(
    message: String,
    state: tauri::State<'_, MemoryStore>,
) -> Result<ChatResponse, String> {
    // Step 1: Search for relevant memories
    let memories = state.search_memories(&message, 5).map_err(|e| e.to_string())?;
    
    // Step 2: Get user context
    let context = state.get_context_summary().map_err(|e| e.to_string())?;
    
    // Step 3: Build augmented prompt
    let augmented_prompt = if !context.is_empty() {
        format!(
            "Context about the user:\n{}\n\nUser message: {}",
            context, message
        )
    } else {
        message.clone()
    };

    // Step 4: Generate response
    let engine_lock = LLM_ENGINE.lock().unwrap();
    let response_text = if let Some(engine) = engine_lock.as_ref() {
        engine.generate(&augmented_prompt, "You are JARVIS, a helpful personal assistant.")?
    } else {
        "LLM engine not initialized. Please configure Phi-3 Mini model path.".to_string()
    };

    Ok(ChatResponse {
        message: response_text,
        memory_context_used: !context.is_empty(),
        memories_retrieved: memories.len(),
    })
}

/// Stream chat tokens (placeholder for streaming inference)
#[tauri::command]
pub fn start_chat_stream(
    message: String,
    state: tauri::State<'_, MemoryStore>,
    app: tauri::AppHandle,
) -> Result<(), String> {
    use tauri::Emitter;
    
    // Get context for RAG
    let context = state.get_context_summary().map_err(|e| e.to_string())?;
    let memories = state.search_memories(&message, 5).map_err(|e| e.to_string())?;
    
    // Emit thought process logs
    let _ = app.emit("chat:thought", ThoughtLog {
        step: "Memory Search".to_string(),
        detail: format!("Found {} relevant memories", memories.len()),
        timestamp: chrono::Utc::now().timestamp(),
    });

    // Spawn streaming task
    std::thread::spawn(move || {
        let engine_lock = LLM_ENGINE.lock().unwrap();
        
        let response = if let Some(engine) = engine_lock.as_ref() {
            let augmented = format!("{}\n{}", context, message);
            engine.generate(&augmented, "You are JARVIS, a helpful personal assistant.")
                .unwrap_or_else(|e| format!("Error: {}", e))
        } else {
            "LLM engine not initialized.".to_string()
        };
        
        // Simulate streaming by emitting word by word
        for word in response.split_whitespace() {
            let _ = app.emit("chat:token", word);
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
        
        // Signal completion
        let _ = app.emit("chat:complete", true);
    });
    
    Ok(())
}

/// Intent detection (simple keyword-based for now)
#[tauri::command]
pub fn detect_intent(message: String) -> Result<Vec<String>, String> {
    let message_lower = message.to_lowercase();
    let mut intents = Vec::new();
    
    if message_lower.contains("weather") || message_lower.contains("temperature") {
        intents.push("get_weather".to_string());
    }
    if message_lower.contains("train") || message_lower.contains("metro") {
        intents.push("get_train_times".to_string());
    }
    if message_lower.contains("flight") || message_lower.contains("plane") {
        intents.push("get_flights".to_string());
    }
    if message_lower.contains("remember") || message_lower.contains("note") {
        intents.push("save_memory".to_string());
    }
    
    Ok(intents)
}

/// Set the model path for Phi-3
#[tauri::command]
pub fn set_model_path(path: String) -> Result<(), String> {
    let model_path = PathBuf::from(path);
    init_llm_engine(Some(model_path))
}
