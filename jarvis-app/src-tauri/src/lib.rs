//! JARVIS Tauri Application - Main Entry Point
//!
//! This is the Rust backend for the JARVIS personal assistant.
//! Architecture:
//! - Sensor data: Streamed via Tauri events (high frequency)
//! - Memory/Preferences: SQLite database (semantic search ready)
//! - External APIs: On-demand Tauri commands
//! - LLM: Local inference with RAG augmentation

mod sensor;
mod memory;
mod external;
mod llm;

use sensor::{SensorState, start_sensor_stream};
use memory::MemoryStore;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Initialize logging
    env_logger::init();

    // Build the app
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        // Initialize managed state
        .setup(|app| {
            // Initialize memory store
            let memory_store = MemoryStore::new(None)
                .expect("Failed to initialize memory store");
            app.manage(memory_store);
            
            // Initialize sensor state
            let sensor_state = SensorState::new();
            app.manage(sensor_state);
            
            // Start sensor streaming
            start_sensor_stream(app.handle().clone());
            
            log::info!("JARVIS backend initialized successfully");
            Ok(())
        })
        // Register all commands
        .invoke_handler(tauri::generate_handler![
            // Sensor commands
            sensor::get_sensor_data,
            // Memory commands
            memory::get_user_profile,
            memory::set_user_name,
            memory::add_user_fact,
            memory::set_preference,
            memory::get_all_preferences,
            memory::add_memory,
            memory::search_memories,
            memory::get_memory_context,
            // External API commands
            external::get_weather,
            external::get_train_times,
            external::get_nearby_flights,
            // LLM commands
            llm::chat,
            llm::start_chat_stream,
            llm::detect_intent,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
