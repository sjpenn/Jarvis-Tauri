//! LLM Chat module - Simplified version for initial launch

use serde::{Deserialize, Serialize};
use crate::memory::MemoryStore;
use std::sync::Mutex;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatResponse {
    pub message: String,
    pub memory_context_used: bool,
    pub memories_retrieved: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThoughtLog {
    pub step: String,
    pub detail: String,
    pub timestamp: i64,
}

pub struct LlmEngine {
    model_path: Option<PathBuf>,
    initialized: bool,
}

impl LlmEngine {
    pub fn new() -> Self {
        Self { model_path: None, initialized: false }
    }

    pub fn init(&mut self, path: PathBuf) -> Result<(), String> {
        if !path.exists() {
            return Err(format!("Model not found: {:?}", path));
        }
        self.model_path = Some(path);
        self.initialized = true;
        log::info!("Model path configured");
        Ok(())
    }

    pub fn generate(&self, prompt: &str, _system: &str) -> Result<String, String> {
        if !self.initialized {
            return Ok("JARVIS ready. Configure Phi-3 model path to enable AI responses.".into());
        }
        Ok(format!("JARVIS (model loaded): Processing '{}'", &prompt[..prompt.len().min(50)]))
    }
}

static LLM_ENGINE: Mutex<Option<LlmEngine>> = Mutex::new(None);

pub fn init_llm_engine(model_path: Option<PathBuf>) -> Result<(), String> {
    let mut engine = LlmEngine::new();
    if let Some(path) = model_path { engine.init(path)?; }
    *LLM_ENGINE.lock().unwrap() = Some(engine);
    Ok(())
}

#[tauri::command]
pub async fn chat(message: String, state: tauri::State<'_, MemoryStore>) -> Result<ChatResponse, String> {
    let memories = state.search_memories(&message, 5).map_err(|e| e.to_string())?;
    let context = state.get_context_summary().map_err(|e| e.to_string())?;
    
    let prompt = if context.is_empty() { message } else { format!("{}\n{}", context, message) };
    
    let response = LLM_ENGINE.lock().unwrap().as_ref()
        .map(|e| e.generate(&prompt, "JARVIS").unwrap_or_default())
        .unwrap_or_else(|| "Engine not initialized".into());

    Ok(ChatResponse { message: response, memory_context_used: !context.is_empty(), memories_retrieved: memories.len() })
}

#[tauri::command]
pub fn start_chat_stream(message: String, state: tauri::State<'_, MemoryStore>, app: tauri::AppHandle) -> Result<(), String> {
    use tauri::Emitter;
    let memories = state.search_memories(&message, 5).map_err(|e| e.to_string())?;
    let _ = app.emit("chat:thought", ThoughtLog { step: "Search".into(), detail: format!("{} memories", memories.len()), timestamp: chrono::Utc::now().timestamp() });
    
    std::thread::spawn(move || {
        let response = LLM_ENGINE.lock().unwrap().as_ref().map(|e| e.generate(&message, "").unwrap_or_default()).unwrap_or_default();
        for word in response.split_whitespace() {
            let _ = app.emit("chat:token", word);
            std::thread::sleep(std::time::Duration::from_millis(30));
        }
        let _ = app.emit("chat:complete", true);
    });
    Ok(())
}

#[tauri::command]
pub fn detect_intent(message: String) -> Result<Vec<String>, String> {
    let m = message.to_lowercase();
    let mut i = vec![];
    if m.contains("weather") { i.push("get_weather".into()); }
    if m.contains("train") { i.push("get_train_times".into()); }
    if m.contains("flight") { i.push("get_flights".into()); }
    Ok(i)
}

#[tauri::command]
pub fn set_model_path(path: String) -> Result<(), String> {
    init_llm_engine(Some(PathBuf::from(path)))
}
