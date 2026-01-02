//! GTFS-Realtime feed parsing and client
//!
//! Handles real-time transit updates including delays, vehicle positions, and service alerts

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// GTFS-Realtime client for fetching and parsing live transit data
pub struct GtfsRealtimeClient {
    api_key: Option<String>,
}

impl GtfsRealtimeClient {
    pub fn new(api_key: Option<String>) -> Self {
        Self { api_key }
    }

    /// Fetch and parse trip updates (delays, cancellations)
    pub async fn fetch_trip_updates(&self, feed_url: &str) -> Result<TripUpdateFeed, String> {
        let client = reqwest::Client::new();
        let mut req = client.get(feed_url);
        
        if let Some(key) = &self.api_key {
            req = req.header("api_key", key);
        }

        let response = req
            .send()
            .await
            .map_err(|e| format!("Failed to fetch trip updates: {}", e))?;

        let bytes = response
            .bytes()
            .await
            .map_err(|e| format!("Failed to read response: {}", e))?;

        // Parse protobuf using gtfs-rt crate
        match gtfs_rt::FeedMessage::parse_from_bytes(&bytes) {
            Ok(feed_message) => {
                let mut updates = Vec::new();
                
                for entity in feed_message.entity {
                    if let Some(trip_update) = entity.trip_update {
                        if let Some(trip) = trip_update.trip {
                            let trip_id = trip.trip_id.unwrap_or_default();
                            
                            for stop_time_update in trip_update.stop_time_update {
                                if let Some(arrival) = stop_time_update.arrival {
                                    let delay = arrival.delay.unwrap_or(0);
                                    
                                    updates.push(TripUpdate {
                                        trip_id: trip_id.clone(),
                                        stop_id: stop_time_update.stop_id.unwrap_or_default(),
                                        delay_seconds: delay,
                                        schedule_relationship: ScheduleRelationship::Scheduled,
                                    });
                                }
                            }
                        }
                    }
                }
                
                Ok(TripUpdateFeed { updates })
            }
            Err(e) => Err(format!("Failed to parse GTFS-RT feed: {:?}", e)),
        }
    }

    /// Fetch and parse vehicle positions
    pub async fn fetch_vehicle_positions(&self, feed_url: &str) -> Result<VehiclePositionFeed, String> {
        let client = reqwest::Client::new();
        let mut req = client.get(feed_url);
        
        if let Some(key) = &self.api_key {
            req = req.header("api_key", key);
        }

        let response = req
            .send()
            .await
            .map_err(|e| format!("Failed to fetch vehicle positions: {}", e))?;

        let bytes = response
            .bytes()
            .await
            .map_err(|e| format!("Failed to read response: {}", e))?;

        match gtfs_rt::FeedMessage::parse_from_bytes(&bytes) {
            Ok(feed_message) => {
                let mut positions = Vec::new();
                
                for entity in feed_message.entity {
                    if let Some(vehicle) = entity.vehicle {
                        if let Some(position) = vehicle.position {
                            if let Some(trip) = vehicle.trip {
                                positions.push(VehiclePosition {
                                    vehicle_id: vehicle.vehicle.map(|v| v.id.unwrap_or_default()).unwrap_or_default(),
                                    trip_id: trip.trip_id.unwrap_or_default(),
                                    latitude: position.latitude,
                                    longitude: position.longitude,
                                    bearing: position.bearing,
                                    speed: position.speed,
                                });
                            }
                        }
                    }
                }
                
                Ok(VehiclePositionFeed { positions })
            }
            Err(e) => Err(format!("Failed to parse vehicle positions: {:?}", e)),
        }
    }

    /// Fetch and parse service alerts
    pub async fn fetch_service_alerts(&self, feed_url: &str) -> Result<ServiceAlertFeed, String> {
        let client = reqwest::Client::new();
        let mut req = client.get(feed_url);
        
        if let Some(key) = &self.api_key {
            req = req.header("api_key", key);
        }

        let response = req
            .send()
            .await
            .map_err(|e| format!("Failed to fetch service alerts: {}", e))?;

        let bytes = response
            .bytes()
            .await
            .map_err(|e| format!("Failed to read response: {}", e))?;

        match gtfs_rt::FeedMessage::parse_from_bytes(&bytes) {
            Ok(feed_message) => {
                let mut alerts = Vec::new();
                
                for entity in feed_message.entity {
                    if let Some(alert) = entity.alert {
                        let header = alert.header_text
                            .and_then(|t| t.translation.first().map(|tr| tr.text.clone().unwrap_or_default()))
                            .unwrap_or_default();
                        
                        let description = alert.description_text
                            .and_then(|t| t.translation.first().map(|tr| tr.text.clone().unwrap_or_default()))
                            .unwrap_or_default();

                        alerts.push(ServiceAlert {
                            id: entity.id,
                            header,
                            description,
                            severity: AlertSeverity::Warning,
                        });
                    }
                }
                
                Ok(ServiceAlertFeed { alerts })
            }
            Err(e) => Err(format!("Failed to parse service alerts: {:?}", e)),
        }
    }

    /// Enrich static GTFS stop times with real-time delay information
    pub fn enrich_with_delays(&self, stop_times: Vec<StaticStopTime>, updates: &TripUpdateFeed) -> Vec<EnrichedStopTime> {
        let delay_map: HashMap<(String, String), i32> = updates.updates.iter()
            .map(|u| ((u.trip_id.clone(), u.stop_id.clone()), u.delay_seconds))
            .collect();

        stop_times.into_iter().map(|st| {
            let delay = delay_map.get(&(st.trip_id.clone(), st.stop_id.clone())).copied().unwrap_or(0);
            
            EnrichedStopTime {
                trip_id: st.trip_id,
                stop_id: st.stop_id,
                scheduled_arrival: st.scheduled_arrival,
                estimated_arrival: st.scheduled_arrival + (delay as u64),
                delay_seconds: delay,
                status: if delay > 300 { "DELAYED" } else { "ON TIME" }.to_string(),
            }
        }).collect()
    }
}

// Data structures

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TripUpdate {
    pub trip_id: String,
    pub stop_id: String,
    pub delay_seconds: i32,
    pub schedule_relationship: ScheduleRelationship,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TripUpdateFeed {
    pub updates: Vec<TripUpdate>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VehiclePosition {
    pub vehicle_id: String,
    pub trip_id: String,
    pub latitude: f32,
    pub longitude: f32,
    pub bearing: Option<f32>,
    pub speed: Option<f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VehiclePositionFeed {
    pub positions: Vec<VehiclePosition>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceAlert {
    pub id: String,
    pub header: String,
    pub description: String,
    pub severity: AlertSeverity,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceAlertFeed {
    pub alerts: Vec<ServiceAlert>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ScheduleRelationship {
    Scheduled,
    Skipped,
    NoData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AlertSeverity {
    Info,
    Warning,
    Severe,
}

// Helper types for enrichment

#[derive(Debug, Clone)]
pub struct StaticStopTime {
    pub trip_id: String,
    pub stop_id: String,
    pub scheduled_arrival: u64, // Unix timestamp
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnrichedStopTime {
    pub trip_id: String,
    pub stop_id: String,
    pub scheduled_arrival: u64,
    pub estimated_arrival: u64,
    pub delay_seconds: i32,
    pub status: String,
}
