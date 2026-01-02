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
mod gtfs;
mod gtfs_rt;
mod feed_manager;

use sensor::{SensorState, start_sensor_stream};
use memory::MemoryStore;
use gtfs::GtfsState;
use feed_manager::FeedRegistryState;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Initialize logging with info level default
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    // Build the app
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        // Initialize managed state
        .setup(|app| {
            // Initialize memory store
            let memory_store = MemoryStore::new(None)
                .expect("Failed to initialize memory store");
            
            // Try to load saved model path
            let saved_model_path = memory_store.get_preference("llm", "model_path")
                .ok()
                .flatten()
                .map(std::path::PathBuf::from);

            // Store WMATA API Key directly
            let _ = memory_store.set_preference("transport", "wmata_api_key", "afa4f0928b2e4a078c2a5bada6fe2411");

            app.manage(memory_store);
            
            // Initialize sensor state
            let sensor_state = SensorState::new();
            app.manage(sensor_state);
            
            // Initialize GTFS manager (default to wmata)
            let gtfs_manager = gtfs::GtfsManager::new("wmata".to_string());
            // Try to load WMATA Rail by default
            let _ = gtfs_manager.load_feed("wmata-rail");
            app.manage(GtfsState(gtfs_manager));
            
            // Initialize Feed Registry
            let gtfs_data_path = std::env::current_dir()
                .unwrap_or_default()
                .join("src-tauri")
                .join("gtfs_data");
            let feed_registry = feed_manager::FeedRegistry::new(gtfs_data_path);
            app.manage(FeedRegistryState(feed_registry));
            
            // Initialize LLM engine with saved path if available
            llm::init_llm_engine(saved_model_path)
                .expect("Failed to initialize LLM engine");
            
            // Start sensor streaming
            start_sensor_stream(app.handle().clone());
            
            // Fetch system location in background
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                loop {
                    match external::get_system_location().await {
                        Ok(loc) => {
                            log::info!("System location detected: {}, {}", loc.city, loc.region);
                            let state = handle.state::<MemoryStore>();
                            let _ = state.set_preference("system", "city", &loc.city);
                            let _ = state.set_preference("system", "region", &loc.region);
                            let _ = state.set_preference("system", "country", &loc.country);
                            let _ = state.set_preference("system", "latitude", &loc.lat.to_string());
                            let _ = state.set_preference("system", "longitude", &loc.lon.to_string());
                            let _ = state.set_preference("system", "timezone", &loc.timezone);
                        }
                        Err(e) => {
                            log::error!("Failed to fetch system location: {}", e);
                        }
                    }
                    // Update every 60 minutes
                    tokio::time::sleep(std::time::Duration::from_secs(3600)).await;
                }
            });
            
            // Resize window to 80% of screen
            if let Some(window) = app.get_webview_window("main") {
                if let Ok(Some(monitor)) = window.current_monitor() {
                    let screen_size = monitor.size();
                    let width = (screen_size.width as f64 * 0.8) as u32;
                    let height = (screen_size.height as f64 * 0.8) as u32;
                    let _ = window.set_size(tauri::Size::Physical(tauri::PhysicalSize { width, height }));
                    let _ = window.center();
                }
            }
            
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
            // GTFS commands
            gtfs::download_gtfs_feed,
            gtfs::load_gtfs_feed,
            gtfs::get_gtfs_stops,
            gtfs::find_closest_stop,
            // Feed Manager commands
            feed_manager::list_available_cities,
            feed_manager::download_city_feed,
            feed_manager::get_city_by_location,
            // LLM commands
            llm::chat,
            llm::start_chat_stream,
            llm::detect_intent,
            llm::set_model_path,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
