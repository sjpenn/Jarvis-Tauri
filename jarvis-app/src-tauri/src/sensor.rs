//! System sensor data collection and streaming
//!
//! Provides real-time system metrics (CPU, RAM) via Tauri events.
//! This data uses the event system, NOT the vector store, for low-latency updates.

use serde::{Deserialize, Serialize};
use sysinfo::System;
use tauri::{AppHandle, Emitter};
use std::sync::Mutex;
use std::time::Duration;

/// System stats snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorData {
    pub cpu_usage: f32,
    pub memory_used: u64,
    pub memory_total: u64,
    pub memory_percent: f32,
    pub timestamp: i64,
}

/// Managed sensor state
pub struct SensorState {
    system: Mutex<System>,
}

impl SensorState {
    pub fn new() -> Self {
        Self {
            system: Mutex::new(System::new_all()),
        }
    }

    /// Get current sensor readings
    pub fn get_readings(&self) -> SensorData {
        let mut sys = self.system.lock().unwrap();
        sys.refresh_all();

        let cpu_usage = sys.global_cpu_usage();
        let memory_used = sys.used_memory();
        let memory_total = sys.total_memory();
        let memory_percent = if memory_total > 0 {
            (memory_used as f32 / memory_total as f32) * 100.0
        } else {
            0.0
        };

        SensorData {
            cpu_usage,
            memory_used,
            memory_total,
            memory_percent,
            timestamp: chrono::Utc::now().timestamp(),
        }
    }
}

impl Default for SensorState {
    fn default() -> Self {
        Self::new()
    }
}

/// Start the sensor streaming loop
/// Emits "sensor:update" events every 500ms
pub fn start_sensor_stream(app: AppHandle) {
    std::thread::spawn(move || {
        let state = SensorState::new();
        
        loop {
            let data = state.get_readings();
            
            // Emit to all windows
            if let Err(e) = app.emit("sensor:update", &data) {
                log::error!("Failed to emit sensor data: {}", e);
            }
            
            std::thread::sleep(Duration::from_millis(500));
        }
    });
}

/// Command to get current sensor data on demand
#[tauri::command]
pub fn get_sensor_data(state: tauri::State<SensorState>) -> SensorData {
    state.get_readings()
}
