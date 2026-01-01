/**
 * Sensor data stores - bound to Tauri events
 * This is for HIGH-FREQUENCY data that should NOT go through the vector store
 */

import { writable, derived } from 'svelte/store';

// Types
export interface SensorData {
    cpu_usage: number;
    memory_used: number;
    memory_total: number;
    memory_percent: number;
    timestamp: number;
}

export interface WeatherData {
    temperature: number;
    unit: string;
    conditions: string;
    humidity?: number;
    wind_speed?: string;
}

// Core sensor stores
export const sensorData = writable<SensorData>({
    cpu_usage: 0,
    memory_used: 0,
    memory_total: 0,
    memory_percent: 0,
    timestamp: Date.now()
});

// Derived stores for individual metrics
export const cpuUsage = derived(sensorData, $s => $s.cpu_usage);
export const memoryPercent = derived(sensorData, $s => $s.memory_percent);
export const memoryUsed = derived(sensorData, $s => $s.memory_used);
export const memoryTotal = derived(sensorData, $s => $s.memory_total);

// Weather store (updated less frequently)
export const weather = writable<WeatherData | null>(null);

// Connection status
export const isConnected = writable(false);

// History for graphs (last 60 samples = 30 seconds at 500ms interval)
const MAX_HISTORY = 60;

export const cpuHistory = writable<number[]>([]);
export const memoryHistory = writable<number[]>([]);

// Update history when sensor data changes
sensorData.subscribe(data => {
    cpuHistory.update(h => {
        const newHistory = [...h, data.cpu_usage];
        return newHistory.slice(-MAX_HISTORY);
    });
    memoryHistory.update(h => {
        const newHistory = [...h, data.memory_percent];
        return newHistory.slice(-MAX_HISTORY);
    });
});

/**
 * Initialize sensor event listeners
 * Call this once when the app mounts
 */
export async function initSensorListeners() {
    try {
        const { listen } = await import('@tauri-apps/api/event');
        
        // Listen for sensor updates from Rust backend
        await listen<SensorData>('sensor:update', (event) => {
            sensorData.set(event.payload);
            isConnected.set(true);
        });
        
        console.log('Sensor listeners initialized');
    } catch (error) {
        console.error('Failed to initialize sensor listeners:', error);
        isConnected.set(false);
    }
}
